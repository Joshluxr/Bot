#!/usr/bin/env python3
"""
Build 32-bit prefix bitmap and bloom filter from Bitcoin address list.
Only processes addresses starting with 1 or 3 (P2PKH and P2SH).
"""

import sys
import hashlib
import struct
import array
import math
from typing import BinaryIO

# Base58 decode table
B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B58_DECODE = {c: i for i, c in enumerate(B58_ALPHABET)}

def base58_decode(addr: str) -> bytes:
    """Decode Base58Check address to get HASH160."""
    n = 0
    for c in addr:
        n = n * 58 + B58_DECODE.get(c, 0)
    
    # Convert to bytes (25 bytes: 1 version + 20 hash + 4 checksum)
    h = '%050x' % n
    data = bytes.fromhex(h)
    
    # Return just the 20-byte HASH160 (skip version byte, skip 4-byte checksum)
    return data[1:21]

def murmurhash3(data: bytes, seed: int) -> int:
    """Simple MurmurHash3-like hash for bloom filter."""
    h = seed
    for i in range(0, len(data), 4):
        k = int.from_bytes(data[i:i+4], 'little') if i+4 <= len(data) else int.from_bytes(data[i:].ljust(4, b'\x00'), 'little')
        k = (k * 0xcc9e2d51) & 0xffffffff
        k = ((k << 15) | (k >> 17)) & 0xffffffff
        k = (k * 0x1b873593) & 0xffffffff
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xffffffff
        h = (h * 5 + 0xe6546b64) & 0xffffffff
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85ebca6b) & 0xffffffff
    h ^= h >> 13
    h = (h * 0xc2b2ae35) & 0xffffffff
    h ^= h >> 16
    return h

class BloomFilter:
    """Simple bloom filter implementation."""
    
    def __init__(self, num_items: int, fp_rate: float = 0.003):
        # Calculate optimal size and number of hash functions
        self.size = int(-num_items * math.log(fp_rate) / (math.log(2) ** 2))
        self.size = ((self.size + 63) // 64) * 64  # Align to 64 bits
        self.num_hashes = max(1, int((self.size / num_items) * math.log(2)))
        self.num_hashes = min(self.num_hashes, 16)  # Cap at 16
        
        # Use bytearray for the bit array
        self.bits = bytearray((self.size + 7) // 8)
        self.count = 0
        
        print(f"Bloom filter: {self.size} bits ({self.size // 8 // 1024 // 1024} MB), {self.num_hashes} hashes")
    
    def add(self, data: bytes):
        for i in range(self.num_hashes):
            h = murmurhash3(data, i * 0x9e3779b9) % self.size
            self.bits[h // 8] |= (1 << (h % 8))
        self.count += 1
    
    def contains(self, data: bytes) -> bool:
        for i in range(self.num_hashes):
            h = murmurhash3(data, i * 0x9e3779b9) % self.size
            if not (self.bits[h // 8] & (1 << (h % 8))):
                return False
        return True
    
    def save(self, f: BinaryIO):
        # Header: magic, size, num_hashes, count
        f.write(struct.pack('<4sQII', b'BLM1', self.size, self.num_hashes, self.count))
        f.write(self.bits)

def build_filters(address_file: str, prefix_bitmap_file: str, bloom_file: str, info_file: str):
    """Build 32-bit prefix bitmap and bloom filter from address list."""
    
    # First pass: count valid addresses
    print("Counting addresses...")
    count = 0
    with open(address_file, 'r') as f:
        for line in f:
            addr = line.strip()
            if addr and (addr.startswith('1') or addr.startswith('3')):
                count += 1
    print(f"Found {count:,} valid addresses (1xxx or 3xxx)")
    
    # Initialize structures
    # 32-bit prefix bitmap: 2^32 bits = 512 MB
    print("Allocating 32-bit prefix bitmap (512 MB)...")
    prefix_bitmap = bytearray(512 * 1024 * 1024)  # 512 MB
    
    print(f"Creating bloom filter for {count:,} addresses...")
    bloom = BloomFilter(count, 0.003)  # 0.3% false positive rate
    
    # Second pass: populate structures
    print("Processing addresses...")
    processed = 0
    hash160_list = []
    
    with open(address_file, 'r') as f:
        for line in f:
            addr = line.strip()
            if not addr:
                continue
            if not (addr.startswith('1') or addr.startswith('3')):
                continue
            
            try:
                hash160 = base58_decode(addr)
                if len(hash160) != 20:
                    continue
                
                # Set bit in prefix bitmap (first 4 bytes = 32 bits)
                prefix32 = int.from_bytes(hash160[0:4], 'big')
                prefix_bitmap[prefix32 // 8] |= (1 << (prefix32 % 8))
                
                # Add to bloom filter
                bloom.add(hash160)
                
                processed += 1
                if processed % 1000000 == 0:
                    print(f"  Processed {processed:,} addresses...")
            
            except Exception as e:
                continue
    
    print(f"Processed {processed:,} addresses total")
    
    # Calculate prefix bitmap stats
    bits_set = sum(bin(b).count('1') for b in prefix_bitmap)
    coverage = bits_set / (512 * 1024 * 1024 * 8) * 100
    rejection_rate = 100 - coverage
    print(f"Prefix bitmap: {bits_set:,} bits set ({coverage:.4f}% coverage, {rejection_rate:.4f}% rejection)")
    
    # Save prefix bitmap
    print(f"Saving prefix bitmap to {prefix_bitmap_file}...")
    with open(prefix_bitmap_file, 'wb') as f:
        # Header: magic, count
        f.write(struct.pack('<4sI', b'PFX1', processed))
        f.write(prefix_bitmap)
    
    # Save bloom filter
    print(f"Saving bloom filter to {bloom_file}...")
    with open(bloom_file, 'wb') as f:
        bloom.save(f)
    
    # Save info file
    print(f"Saving info to {info_file}...")
    with open(info_file, 'w') as f:
        f.write(f"addresses={processed}\n")
        f.write(f"prefix_bits_set={bits_set}\n")
        f.write(f"prefix_rejection_rate={rejection_rate:.6f}\n")
        f.write(f"bloom_size={bloom.size}\n")
        f.write(f"bloom_hashes={bloom.num_hashes}\n")
        f.write(f"bloom_fp_rate=0.003\n")
    
    print("Done!")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <address_file> [prefix_bitmap] [bloom_filter] [info_file]")
        sys.exit(1)
    
    addr_file = sys.argv[1]
    prefix_file = sys.argv[2] if len(sys.argv) > 2 else 'prefix_bitmap.bin'
    bloom_file = sys.argv[3] if len(sys.argv) > 3 else 'bloom_filter.bin'
    info_file = sys.argv[4] if len(sys.argv) > 4 else 'filter_info.txt'
    
    build_filters(addr_file, prefix_file, bloom_file, info_file)
