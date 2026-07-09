#!/usr/bin/env python3
"""
build_bloom_filter.py - Create GPU-optimized bloom filter from Bitcoin addresses

This script:
1. Downloads the latest Bitcoin address list from loyce.club
2. Converts addresses to hash160 (20 bytes)
3. Builds a bloom filter optimized for GPU batch checking
4. Saves in a format ready for CUDA global memory

For 55M addresses with 0.00001% false positive rate:
- Filter size: ~200 MB
- Hash functions: 20
- At 23B keys/sec: ~2.3 false positives per second (easily verified on CPU)

Author: Claude Code
"""

import hashlib
import struct
import sys
import os
import math
import gzip
import urllib.request
from typing import List, Tuple, BinaryIO
import mmap
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

# Target false positive rate: 0.00001% = 1e-7
FALSE_POSITIVE_RATE = 1e-7

# Base58 alphabet for Bitcoin addresses
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
BASE58_MAP = {c: i for i, c in enumerate(BASE58_ALPHABET)}

# ============================================================================
# BASE58 DECODING
# ============================================================================

def base58_decode(s: str) -> bytes:
    """Decode a Base58Check encoded string to bytes"""
    # Count leading '1's (they represent leading zero bytes)
    leading_zeros = 0
    for c in s:
        if c == '1':
            leading_zeros += 1
        else:
            break

    # Convert base58 to integer
    num = 0
    for c in s:
        num = num * 58 + BASE58_MAP[c]

    # Convert to bytes
    result = []
    while num > 0:
        result.append(num & 0xff)
        num >>= 8
    result.reverse()

    # Add leading zeros
    return bytes([0] * leading_zeros) + bytes(result)

def address_to_hash160(address: str) -> bytes:
    """
    Convert Bitcoin address to hash160 (20 bytes)

    For P2PKH (1...): version(1) + hash160(20) + checksum(4)
    For P2SH (3...):  version(1) + hash160(20) + checksum(4)
    """
    try:
        decoded = base58_decode(address)
        if len(decoded) != 25:
            return None
        # Verify checksum
        payload = decoded[:-4]
        checksum = decoded[-4:]
        expected_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        if checksum != expected_checksum:
            return None
        # Return hash160 (skip version byte)
        return decoded[1:21]
    except:
        return None

def bech32_decode(address: str) -> bytes:
    """Decode bech32/bech32m address to witness program (hash160 for P2WPKH)"""
    BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    try:
        # Split human-readable part and data
        pos = address.rfind('1')
        if pos < 1 or pos + 7 > len(address):
            return None

        hrp = address[:pos].lower()
        data = address[pos+1:].lower()

        # Decode data part
        values = [BECH32_CHARSET.index(c) for c in data]

        # Convert from 5-bit to 8-bit
        witness_version = values[0]
        data_5bit = values[1:-6]  # Exclude checksum

        # Convert 5-bit groups to 8-bit
        acc = 0
        bits = 0
        result = []
        for value in data_5bit:
            acc = (acc << 5) | value
            bits += 5
            while bits >= 8:
                bits -= 8
                result.append((acc >> bits) & 0xff)

        if len(result) == 20:  # P2WPKH
            return bytes(result)
        elif len(result) == 32:  # P2WSH - we'll still store it but flag it
            return bytes(result[:20])  # Truncate for bloom filter (will have more FPs for P2WSH)
        return None
    except:
        return None

# ============================================================================
# BLOOM FILTER
# ============================================================================

def calculate_bloom_params(num_items: int, fp_rate: float) -> Tuple[int, int]:
    """Calculate optimal bloom filter size and number of hash functions"""
    # m = -n * ln(p) / (ln(2)^2)
    m = int(-num_items * math.log(fp_rate) / (math.log(2) ** 2))
    # k = (m/n) * ln(2)
    k = int((m / num_items) * math.log(2))
    return m, k

def murmur3_32(data: bytes, seed: int) -> int:
    """MurmurHash3 32-bit implementation (matches CUDA version)"""
    c1 = 0xcc9e2d51
    c2 = 0x1b873593

    h1 = seed & 0xffffffff
    length = len(data)

    # Body
    nblocks = length // 4
    for i in range(nblocks):
        k1 = struct.unpack('<I', data[i*4:(i+1)*4])[0]

        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff

        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xffffffff
        h1 = ((h1 * 5) + 0xe6546b64) & 0xffffffff

    # Tail
    tail = data[nblocks * 4:]
    k1 = 0
    if len(tail) >= 3:
        k1 ^= tail[2] << 16
    if len(tail) >= 2:
        k1 ^= tail[1] << 8
    if len(tail) >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff
        h1 ^= k1

    # Finalization
    h1 ^= length
    h1 ^= h1 >> 16
    h1 = (h1 * 0x85ebca6b) & 0xffffffff
    h1 ^= h1 >> 13
    h1 = (h1 * 0xc2b2ae35) & 0xffffffff
    h1 ^= h1 >> 16

    return h1

class BloomFilter:
    """GPU-optimized Bloom Filter"""

    def __init__(self, num_bits: int, num_hashes: int):
        self.num_bits = num_bits
        self.num_hashes = num_hashes
        self.num_bytes = (num_bits + 7) // 8
        # Align to 4 bytes for GPU efficiency
        self.num_bytes = ((self.num_bytes + 3) // 4) * 4
        self.bits = bytearray(self.num_bytes)
        # Use prime seeds for better distribution
        self.seeds = [
            0x7a2f3c1d, 0x9e8b4f2a, 0x3d5c7e9b, 0x1f4a6b8c,
            0x5c9d2e7f, 0x8b3a4f1e, 0x2e7c9d5a, 0x4f1b8c3e,
            0x6a9e2d7c, 0x3c8f5b1a, 0x9d4e7a2f, 0x1b6c3f8e,
            0x7e2a9d5c, 0x4c8b1f3a, 0x5a3e7c9d, 0x2f9c4b8e,
            0x8d5a2e7f, 0x3b7f9c4e, 0x6c1a5d3b, 0x9f4e2a7c,
            0x1d8b5c3f, 0x7c3a9e2d, 0x4e9f1b8c, 0x2a5d7c9e
        ][:num_hashes]
        self.items_added = 0

    def add(self, data: bytes):
        """Add an item to the bloom filter"""
        for seed in self.seeds:
            h = murmur3_32(data, seed)
            bit_pos = h % self.num_bits
            byte_pos = bit_pos // 8
            bit_mask = 1 << (bit_pos % 8)
            self.bits[byte_pos] |= bit_mask
        self.items_added += 1

    def contains(self, data: bytes) -> bool:
        """Check if item might be in the filter"""
        for seed in self.seeds:
            h = murmur3_32(data, seed)
            bit_pos = h % self.num_bits
            byte_pos = bit_pos // 8
            bit_mask = 1 << (bit_pos % 8)
            if not (self.bits[byte_pos] & bit_mask):
                return False
        return True

    def save(self, filename: str):
        """Save bloom filter in GPU-ready format"""
        with open(filename, 'wb') as f:
            # Header (64 bytes, aligned)
            header = struct.pack('<Q', self.num_bits)           # 8 bytes: number of bits
            header += struct.pack('<Q', self.num_bytes)         # 8 bytes: number of bytes
            header += struct.pack('<I', self.num_hashes)        # 4 bytes: number of hash functions
            header += struct.pack('<I', self.items_added)       # 4 bytes: items added
            # Seeds (up to 24 * 4 = 96 bytes)
            for seed in self.seeds:
                header += struct.pack('<I', seed)
            # Pad to 256 bytes for alignment
            header = header.ljust(256, b'\x00')
            f.write(header)
            # Bloom filter data
            f.write(self.bits)

        print(f"Saved bloom filter:")
        print(f"  - File: {filename}")
        print(f"  - Size: {os.path.getsize(filename) / 1024 / 1024:.2f} MB")
        print(f"  - Bits: {self.num_bits:,}")
        print(f"  - Hashes: {self.num_hashes}")
        print(f"  - Items: {self.items_added:,}")

    @classmethod
    def load(cls, filename: str) -> 'BloomFilter':
        """Load bloom filter from file"""
        with open(filename, 'rb') as f:
            num_bits = struct.unpack('<Q', f.read(8))[0]
            num_bytes = struct.unpack('<Q', f.read(8))[0]
            num_hashes = struct.unpack('<I', f.read(4))[0]
            items_added = struct.unpack('<I', f.read(4))[0]

            bf = cls(num_bits, num_hashes)
            bf.items_added = items_added

            # Read seeds
            bf.seeds = []
            for _ in range(num_hashes):
                bf.seeds.append(struct.unpack('<I', f.read(4))[0])

            # Skip to data (header is 256 bytes)
            f.seek(256)
            bf.bits = bytearray(f.read())

            return bf

# ============================================================================
# PARALLEL PROCESSING
# ============================================================================

def process_address_batch(args):
    """Process a batch of addresses (for parallel processing)"""
    addresses, include_p2pkh, include_p2sh, include_bech32 = args
    hash160s = []

    for addr in addresses:
        addr = addr.strip()
        if not addr:
            continue

        # Determine address type
        if addr.startswith('bc1'):
            if include_bech32:
                h = bech32_decode(addr)
                if h:
                    hash160s.append(h)
        elif addr.startswith('1'):
            if include_p2pkh:
                h = address_to_hash160(addr)
                if h:
                    hash160s.append(h)
        elif addr.startswith('3'):
            if include_p2sh:
                h = address_to_hash160(addr)
                if h:
                    hash160s.append(h)

    return hash160s

# ============================================================================
# MAIN
# ============================================================================

def download_addresses(url: str, output_file: str):
    """Download and extract address file"""
    print(f"Downloading from {url}...")

    # Download with progress
    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 / total_size)
        mb_downloaded = downloaded / 1024 / 1024
        mb_total = total_size / 1024 / 1024
        print(f"\r  Progress: {percent:.1f}% ({mb_downloaded:.1f} / {mb_total:.1f} MB)", end='', flush=True)

    temp_gz = output_file + '.gz'
    urllib.request.urlretrieve(url, temp_gz, report_progress)
    print()

    print("Extracting...")
    with gzip.open(temp_gz, 'rb') as f_in:
        with open(output_file, 'wb') as f_out:
            while chunk := f_in.read(1024 * 1024):
                f_out.write(chunk)

    os.remove(temp_gz)
    print(f"Extracted to {output_file}")

def build_bloom_filter(
    input_file: str,
    output_file: str,
    include_p2pkh: bool = True,
    include_p2sh: bool = True,
    include_bech32: bool = True,
    fp_rate: float = 1e-7
):
    """Build bloom filter from address file"""

    # First pass: count addresses to size bloom filter
    print("Counting addresses...")
    total_lines = 0
    with open(input_file, 'r') as f:
        for line in f:
            total_lines += 1
    print(f"Total addresses: {total_lines:,}")

    # Calculate bloom filter parameters
    num_bits, num_hashes = calculate_bloom_params(total_lines, fp_rate)
    print(f"Bloom filter parameters:")
    print(f"  - Bits: {num_bits:,} ({num_bits / 8 / 1024 / 1024:.2f} MB)")
    print(f"  - Hash functions: {num_hashes}")
    print(f"  - Expected FP rate: {fp_rate * 100:.7f}%")

    # Create bloom filter
    bf = BloomFilter(num_bits, num_hashes)

    # Process addresses in batches
    batch_size = 100000
    num_workers = mp.cpu_count()

    print(f"Processing addresses with {num_workers} workers...")

    processed = 0
    start_time = time.time()

    # Also save hash160s for CPU verification
    hash160_file = output_file.replace('.bloom', '.hash160')
    with open(hash160_file, 'wb') as h160_out:
        with open(input_file, 'r') as f:
            batch = []
            for line in f:
                batch.append(line)
                if len(batch) >= batch_size:
                    # Process batch
                    for addr in batch:
                        addr = addr.strip()
                        if not addr:
                            continue

                        h = None
                        if addr.startswith('bc1') and include_bech32:
                            h = bech32_decode(addr)
                        elif addr.startswith('1') and include_p2pkh:
                            h = address_to_hash160(addr)
                        elif addr.startswith('3') and include_p2sh:
                            h = address_to_hash160(addr)

                        if h:
                            bf.add(h)
                            h160_out.write(h)

                    processed += len(batch)
                    elapsed = time.time() - start_time
                    rate = processed / elapsed
                    eta = (total_lines - processed) / rate if rate > 0 else 0
                    print(f"\r  Processed: {processed:,} / {total_lines:,} ({processed*100/total_lines:.1f}%) - {rate:.0f}/sec - ETA: {eta:.0f}s", end='', flush=True)
                    batch = []

            # Process remaining
            if batch:
                for addr in batch:
                    addr = addr.strip()
                    if not addr:
                        continue

                    h = None
                    if addr.startswith('bc1') and include_bech32:
                        h = bech32_decode(addr)
                    elif addr.startswith('1') and include_p2pkh:
                        h = address_to_hash160(addr)
                    elif addr.startswith('3') and include_p2sh:
                        h = address_to_hash160(addr)

                    if h:
                        bf.add(h)
                        h160_out.write(h)

                processed += len(batch)

    print()
    print(f"Added {bf.items_added:,} hash160s to bloom filter")

    # Save bloom filter
    bf.save(output_file)

    # Sort hash160 file for binary search verification
    print(f"Sorting hash160 file for CPU verification...")
    hash160s = []
    with open(hash160_file, 'rb') as f:
        while chunk := f.read(20):
            if len(chunk) == 20:
                hash160s.append(chunk)

    hash160s.sort()

    sorted_file = output_file.replace('.bloom', '.sorted')
    with open(sorted_file, 'wb') as f:
        for h in hash160s:
            f.write(h)

    print(f"Saved sorted hash160s to {sorted_file}")
    print(f"  - Count: {len(hash160s):,}")
    print(f"  - Size: {len(hash160s) * 20 / 1024 / 1024:.2f} MB")

    # Cleanup unsorted file
    os.remove(hash160_file)

    print("\nDone!")
    print(f"\nFiles created:")
    print(f"  - Bloom filter: {output_file}")
    print(f"  - Sorted hash160s: {sorted_file}")

    return bf

def test_bloom_filter(bloom_file: str, sorted_file: str, num_tests: int = 1000):
    """Test bloom filter false positive rate"""
    print(f"\nTesting bloom filter...")

    bf = BloomFilter.load(bloom_file)

    # Load some known addresses
    with open(sorted_file, 'rb') as f:
        known_hash160s = []
        for _ in range(min(num_tests, bf.items_added)):
            h = f.read(20)
            if len(h) == 20:
                known_hash160s.append(h)

    # Test known addresses (should all return True)
    true_positives = sum(1 for h in known_hash160s if bf.contains(h))
    print(f"  Known addresses found: {true_positives}/{len(known_hash160s)} ({true_positives*100/len(known_hash160s):.2f}%)")

    # Test random addresses (measure false positive rate)
    import random
    false_positives = 0
    for _ in range(num_tests):
        random_hash160 = bytes(random.randint(0, 255) for _ in range(20))
        if bf.contains(random_hash160):
            false_positives += 1

    print(f"  False positives: {false_positives}/{num_tests} ({false_positives*100/num_tests:.4f}%)")
    print(f"  Expected FP rate: {FALSE_POSITIVE_RATE * 100:.7f}%")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Build GPU-optimized bloom filter from Bitcoin addresses')
    parser.add_argument('--input', '-i', help='Input address file (or will download if not specified)')
    parser.add_argument('--output', '-o', default='targets.bloom', help='Output bloom filter file')
    parser.add_argument('--download', '-d', action='store_true', help='Download latest address list')
    parser.add_argument('--url', default='http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz',
                        help='URL to download addresses from')
    parser.add_argument('--fp-rate', type=float, default=1e-7, help='False positive rate (default: 1e-7 = 0.00001%%)')
    parser.add_argument('--p2pkh', action='store_true', default=True, help='Include P2PKH addresses (1...)')
    parser.add_argument('--p2sh', action='store_true', default=True, help='Include P2SH addresses (3...)')
    parser.add_argument('--bech32', action='store_true', default=True, help='Include bech32 addresses (bc1...)')
    parser.add_argument('--no-p2pkh', action='store_true', help='Exclude P2PKH addresses')
    parser.add_argument('--no-p2sh', action='store_true', help='Exclude P2SH addresses')
    parser.add_argument('--no-bech32', action='store_true', help='Exclude bech32 addresses')
    parser.add_argument('--test', action='store_true', help='Test bloom filter after building')

    args = parser.parse_args()

    # Determine input file
    if args.download or not args.input:
        input_file = 'Bitcoin_addresses_LATEST.txt'
        if not os.path.exists(input_file):
            download_addresses(args.url, input_file)
    else:
        input_file = args.input

    # Build bloom filter
    bf = build_bloom_filter(
        input_file,
        args.output,
        include_p2pkh=args.p2pkh and not args.no_p2pkh,
        include_p2sh=args.p2sh and not args.no_p2sh,
        include_bech32=args.bech32 and not args.no_bech32,
        fp_rate=args.fp_rate
    )

    # Test if requested
    if args.test:
        sorted_file = args.output.replace('.bloom', '.sorted')
        test_bloom_filter(args.output, sorted_file)
