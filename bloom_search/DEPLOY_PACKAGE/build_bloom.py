#!/usr/bin/env python3
"""
build_bloom.py - Build bloom filter from Bitcoin addresses

Run on the GPU server:
  python3 build_bloom.py

This will:
1. Download 55M+ Bitcoin addresses from loyce.club
2. Build a ~200 MB bloom filter (0.00001% false positive rate)
3. Create sorted hash160 file for CPU verification
"""

import hashlib
import struct
import os
import math
import gzip
import urllib.request
import time
import sys

# Configuration
FALSE_POSITIVE_RATE = 1e-7  # 0.00001%
ADDRESS_URL = "http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz"
ADDRESS_FILE = "Bitcoin_addresses_LATEST.txt"
BLOOM_FILE = "targets.bloom"
SORTED_FILE = "targets.sorted"

# Base58 decoding
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
BASE58_MAP = {c: i for i, c in enumerate(BASE58_ALPHABET)}

def base58_decode(s):
    """Decode Base58Check string to bytes"""
    leading_zeros = sum(1 for c in s if c == '1')
    num = 0
    for c in s:
        if c not in BASE58_MAP:
            return None
        num = num * 58 + BASE58_MAP[c]
    result = []
    while num > 0:
        result.append(num & 0xff)
        num >>= 8
    result.reverse()
    return bytes([0] * leading_zeros) + bytes(result)

def address_to_hash160(address):
    """Convert Bitcoin address to hash160 (20 bytes)"""
    try:
        decoded = base58_decode(address)
        if decoded is None or len(decoded) != 25:
            return None
        payload = decoded[:-4]
        checksum = decoded[-4:]
        expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        if checksum != expected:
            return None
        return decoded[1:21]
    except:
        return None

def bech32_decode(address):
    """Decode bech32 address to witness program"""
    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    try:
        pos = address.rfind('1')
        if pos < 1 or pos + 7 > len(address):
            return None
        data = address[pos+1:].lower()
        values = [CHARSET.index(c) for c in data]
        data_5bit = values[1:-6]
        acc, bits = 0, 0
        result = []
        for value in data_5bit:
            acc = (acc << 5) | value
            bits += 5
            while bits >= 8:
                bits -= 8
                result.append((acc >> bits) & 0xff)
        if len(result) == 20:
            return bytes(result)
        elif len(result) == 32:
            return bytes(result[:20])  # P2WSH - truncate for bloom
        return None
    except:
        return None

def murmur3_32(data, seed):
    """MurmurHash3 32-bit (matches GPU implementation)"""
    c1, c2 = 0xcc9e2d51, 0x1b873593
    h1 = seed & 0xffffffff
    length = len(data)
    nblocks = length // 4

    for i in range(nblocks):
        k1 = struct.unpack('<I', data[i*4:(i+1)*4])[0]
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xffffffff
        h1 = ((h1 * 5) + 0xe6546b64) & 0xffffffff

    tail = data[nblocks * 4:]
    k1 = 0
    if len(tail) >= 3: k1 ^= tail[2] << 16
    if len(tail) >= 2: k1 ^= tail[1] << 8
    if len(tail) >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff
        h1 ^= k1

    h1 ^= length
    h1 ^= h1 >> 16
    h1 = (h1 * 0x85ebca6b) & 0xffffffff
    h1 ^= h1 >> 13
    h1 = (h1 * 0xc2b2ae35) & 0xffffffff
    h1 ^= h1 >> 16
    return h1

class BloomFilter:
    def __init__(self, num_bits, num_hashes):
        self.num_bits = num_bits
        self.num_hashes = num_hashes
        self.num_bytes = ((num_bits + 7) // 8 + 3) // 4 * 4  # Align to 4 bytes
        self.bits = bytearray(self.num_bytes)
        self.seeds = [
            0x7a2f3c1d, 0x9e8b4f2a, 0x3d5c7e9b, 0x1f4a6b8c,
            0x5c9d2e7f, 0x8b3a4f1e, 0x2e7c9d5a, 0x4f1b8c3e,
            0x6a9e2d7c, 0x3c8f5b1a, 0x9d4e7a2f, 0x1b6c3f8e,
            0x7e2a9d5c, 0x4c8b1f3a, 0x5a3e7c9d, 0x2f9c4b8e,
            0x8d5a2e7f, 0x3b7f9c4e, 0x6c1a5d3b, 0x9f4e2a7c
        ][:num_hashes]
        self.items_added = 0

    def add(self, data):
        for seed in self.seeds:
            h = murmur3_32(data, seed)
            bit_pos = h % self.num_bits
            self.bits[bit_pos // 8] |= (1 << (bit_pos % 8))
        self.items_added += 1

    def contains(self, data):
        for seed in self.seeds:
            h = murmur3_32(data, seed)
            bit_pos = h % self.num_bits
            if not (self.bits[bit_pos // 8] & (1 << (bit_pos % 8))):
                return False
        return True

    def save(self, filename):
        with open(filename, 'wb') as f:
            # Header (256 bytes)
            header = struct.pack('<Q', self.num_bits)
            header += struct.pack('<Q', self.num_bytes)
            header += struct.pack('<I', self.num_hashes)
            header += struct.pack('<I', self.items_added)
            for seed in self.seeds:
                header += struct.pack('<I', seed)
            header = header.ljust(256, b'\x00')
            f.write(header)
            f.write(self.bits)
        return os.path.getsize(filename)

def calculate_bloom_params(num_items, fp_rate):
    """Calculate optimal bloom filter parameters"""
    m = int(-num_items * math.log(fp_rate) / (math.log(2) ** 2))
    k = int((m / num_items) * math.log(2))
    return m, min(k, 20)  # Cap at 20 hash functions

def download_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = min(100, downloaded * 100 / total_size)
    mb = downloaded / 1024 / 1024
    total_mb = total_size / 1024 / 1024
    print(f"\rDownloading: {percent:.1f}% ({mb:.1f}/{total_mb:.1f} MB)", end='', flush=True)

def main():
    print("=" * 60)
    print("BloomSearch - Bloom Filter Builder")
    print("=" * 60)

    os.chdir(os.path.dirname(os.path.abspath(__file__)) or '.')

    # Check if already built
    if os.path.exists(BLOOM_FILE) and os.path.getsize(BLOOM_FILE) > 100000000:
        print(f"\nBloom filter already exists: {BLOOM_FILE}")
        print(f"  Size: {os.path.getsize(BLOOM_FILE)/1024/1024:.1f} MB")
        if os.path.exists(SORTED_FILE):
            print(f"  Sorted file: {os.path.getsize(SORTED_FILE)/1024/1024:.1f} MB")
        print("\nTo rebuild, delete these files first.")
        return

    # Download addresses if needed
    if not os.path.exists(ADDRESS_FILE):
        print(f"\nDownloading Bitcoin addresses from {ADDRESS_URL}...")
        gz_file = ADDRESS_FILE + '.gz'
        urllib.request.urlretrieve(ADDRESS_URL, gz_file, download_progress)
        print("\n\nExtracting...")

        with gzip.open(gz_file, 'rb') as f_in:
            with open(ADDRESS_FILE, 'wb') as f_out:
                while chunk := f_in.read(1024 * 1024):
                    f_out.write(chunk)
        os.remove(gz_file)
        print(f"Extracted to {ADDRESS_FILE}")

    # Count addresses
    print("\nCounting addresses...")
    total = sum(1 for _ in open(ADDRESS_FILE))
    print(f"Total addresses: {total:,}")

    # Calculate bloom filter parameters
    num_bits, num_hashes = calculate_bloom_params(total, FALSE_POSITIVE_RATE)
    print(f"\nBloom filter parameters:")
    print(f"  Bits: {num_bits:,} ({num_bits/8/1024/1024:.1f} MB)")
    print(f"  Hash functions: {num_hashes}")
    print(f"  Expected FP rate: {FALSE_POSITIVE_RATE*100:.7f}%")

    # Build bloom filter
    print("\nBuilding bloom filter...")
    bf = BloomFilter(num_bits, num_hashes)
    hash160s = []

    processed = 0
    skipped = 0
    start_time = time.time()

    with open(ADDRESS_FILE, 'r') as f:
        for line in f:
            addr = line.strip()
            if not addr:
                continue

            h = None
            if addr.startswith('bc1'):
                h = bech32_decode(addr)
            elif addr.startswith('1') or addr.startswith('3'):
                h = address_to_hash160(addr)

            if h:
                bf.add(h)
                hash160s.append(h)
            else:
                skipped += 1

            processed += 1
            if processed % 1000000 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                eta = (total - processed) / rate if rate > 0 else 0
                print(f"\rProcessed: {processed:,}/{total:,} ({processed*100/total:.1f}%) "
                      f"- {rate:.0f}/sec - ETA: {eta:.0f}s", end='', flush=True)

    print(f"\n\nAdded {bf.items_added:,} addresses to bloom filter")
    if skipped > 0:
        print(f"Skipped {skipped:,} invalid addresses")

    # Save bloom filter
    print(f"\nSaving bloom filter to {BLOOM_FILE}...")
    size = bf.save(BLOOM_FILE)
    print(f"Saved: {size/1024/1024:.1f} MB")

    # Sort and save hash160s
    print(f"\nSorting {len(hash160s):,} hash160s...")
    hash160s.sort()

    print(f"Saving to {SORTED_FILE}...")
    with open(SORTED_FILE, 'wb') as f:
        for h in hash160s:
            f.write(h)
    print(f"Saved: {len(hash160s)*20/1024/1024:.1f} MB")

    # Test
    print("\n" + "=" * 60)
    print("Testing bloom filter...")
    print("=" * 60)

    # Test known addresses
    test_count = min(1000, len(hash160s))
    found = sum(1 for h in hash160s[:test_count] if bf.contains(h))
    print(f"Known addresses found: {found}/{test_count} ({found*100/test_count:.2f}%)")

    # Test random data (measure FP rate)
    import random
    fps = 0
    random_tests = 10000
    for _ in range(random_tests):
        random_hash = bytes(random.randint(0, 255) for _ in range(20))
        if bf.contains(random_hash):
            fps += 1
    print(f"False positives: {fps}/{random_tests} ({fps*100/random_tests:.4f}%)")
    print(f"Expected: {FALSE_POSITIVE_RATE*100:.7f}%")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  {BLOOM_FILE}: {os.path.getsize(BLOOM_FILE)/1024/1024:.1f} MB")
    print(f"  {SORTED_FILE}: {os.path.getsize(SORTED_FILE)/1024/1024:.1f} MB")

if __name__ == '__main__':
    main()
