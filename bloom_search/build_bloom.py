#!/usr/bin/env python3
"""
Build a bloom filter from Bitcoin addresses for GPU-accelerated matching.
Converts addresses to hash160 and builds a compact bloom filter.
"""
import hashlib
import gzip
import struct
import sys
import os
from typing import Generator

# Bloom filter parameters for ~55M addresses with 0.0001% false positive rate
# Using ~200MB bloom filter (reasonable for GPU memory)
BLOOM_SIZE_BITS = 1_600_000_000  # 1.6 billion bits = 200MB
BLOOM_SIZE_BYTES = BLOOM_SIZE_BITS // 8
NUM_HASH_FUNCTIONS = 20  # Optimal for this size/count ratio

# Base58 alphabet for Bitcoin addresses
B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B58_MAP = {c: i for i, c in enumerate(B58_ALPHABET)}

# Bech32 charset
BECH32_CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'

def b58decode(s: str) -> bytes:
    """Decode Base58 string to bytes."""
    num = 0
    for c in s:
        num = num * 58 + B58_MAP.get(c, 0)
    
    # Convert to bytes
    result = []
    while num > 0:
        result.append(num & 0xff)
        num >>= 8
    
    # Add leading zeros for each leading '1'
    for c in s:
        if c == '1':
            result.append(0)
        else:
            break
    
    return bytes(reversed(result))

def bech32_decode(addr: str) -> bytes:
    """Decode bech32/bech32m address to witness program."""
    try:
        # Find the separator
        pos = addr.rfind('1')
        if pos < 1 or pos + 7 > len(addr):
            return None
        
        hrp = addr[:pos].lower()
        data_part = addr[pos+1:].lower()
        
        # Decode data part
        data = []
        for c in data_part:
            if c not in BECH32_CHARSET:
                return None
            data.append(BECH32_CHARSET.index(c))
        
        if len(data) < 6:
            return None
        
        # Remove checksum and convert from 5-bit to 8-bit
        values = data[:-6]
        if len(values) < 1:
            return None
        
        witver = values[0]
        witprog = []
        
        acc = 0
        bits = 0
        for v in values[1:]:
            acc = (acc << 5) | v
            bits += 5
            if bits >= 8:
                bits -= 8
                witprog.append((acc >> bits) & 0xff)
        
        return bytes(witprog) if witprog else None
    except:
        return None

def address_to_hash160(addr: str) -> bytes:
    """Convert Bitcoin address to 20-byte hash160."""
    try:
        if addr.startswith('1') or addr.startswith('3'):
            # P2PKH or P2SH - Base58Check encoded
            decoded = b58decode(addr)
            if len(decoded) >= 21:
                # Skip version byte, take 20 bytes of hash160
                return decoded[1:21]
        elif addr.lower().startswith('bc1'):
            # Bech32/Bech32m - witness program
            witprog = bech32_decode(addr)
            if witprog:
                if len(witprog) == 20:
                    # P2WPKH - direct hash160
                    return witprog
                elif len(witprog) == 32:
                    # P2WSH or P2TR - hash the witness program to get 20 bytes
                    return hashlib.new('ripemd160', hashlib.sha256(witprog).digest()).digest()
        return None
    except:
        return None

def murmur3_32(data: bytes, seed: int) -> int:
    """MurmurHash3 32-bit implementation matching GPU version."""
    c1 = 0xcc9e2d51
    c2 = 0x1b873593
    
    h = seed & 0xffffffff
    length = len(data)
    
    # Process 4-byte chunks
    nblocks = length // 4
    for i in range(nblocks):
        k = struct.unpack('<I', data[i*4:(i+1)*4])[0]
        k = (k * c1) & 0xffffffff
        k = ((k << 15) | (k >> 17)) & 0xffffffff
        k = (k * c2) & 0xffffffff
        
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xffffffff
        h = ((h * 5) + 0xe6546b64) & 0xffffffff
    
    # Process remaining bytes
    tail = data[nblocks * 4:]
    k = 0
    if len(tail) >= 3:
        k ^= tail[2] << 16
    if len(tail) >= 2:
        k ^= tail[1] << 8
    if len(tail) >= 1:
        k ^= tail[0]
        k = (k * c1) & 0xffffffff
        k = ((k << 15) | (k >> 17)) & 0xffffffff
        k = (k * c2) & 0xffffffff
        h ^= k
    
    # Finalization
    h ^= length
    h ^= (h >> 16)
    h = (h * 0x85ebca6b) & 0xffffffff
    h ^= (h >> 13)
    h = (h * 0xc2b2ae35) & 0xffffffff
    h ^= (h >> 16)
    
    return h

def bloom_add(bloom: bytearray, hash160: bytes, num_bits: int, num_hashes: int):
    """Add a hash160 to the bloom filter."""
    for i in range(num_hashes):
        h = murmur3_32(hash160, i) % num_bits
        bloom[h // 8] |= (1 << (h % 8))

def process_addresses(input_file: str) -> Generator[bytes, None, None]:
    """Stream addresses from gzipped file and yield hash160 values."""
    opener = gzip.open if input_file.endswith('.gz') else open
    mode = 'rt' if input_file.endswith('.gz') else 'r'
    
    with opener(input_file, mode, encoding='utf-8', errors='ignore') as f:
        for line in f:
            addr = line.strip()
            if addr:
                hash160 = address_to_hash160(addr)
                if hash160 and len(hash160) == 20:
                    yield hash160

def main():
    input_file = '/workspace/bloom_search/btc_addresses.txt.gz'
    bloom_file = '/workspace/bloom_search/btc_addresses.bloom'
    hash160_file = '/workspace/bloom_search/btc_hash160.bin'
    
    print(f'Building bloom filter from {input_file}')
    print(f'Bloom filter size: {BLOOM_SIZE_BYTES / 1024 / 1024:.1f} MB')
    print(f'Hash functions: {NUM_HASH_FUNCTIONS}')
    
    # Initialize bloom filter
    bloom = bytearray(BLOOM_SIZE_BYTES)
    
    # Also save hash160 values for CPU verification
    hash160_list = []
    
    count = 0
    errors = 0
    
    for hash160 in process_addresses(input_file):
        bloom_add(bloom, hash160, BLOOM_SIZE_BITS, NUM_HASH_FUNCTIONS)
        hash160_list.append(hash160)
        count += 1
        
        if count % 1_000_000 == 0:
            print(f'Processed {count:,} addresses...')
    
    print(f'\nTotal addresses processed: {count:,}')
    
    # Write bloom filter with header
    print(f'Writing bloom filter to {bloom_file}...')
    with open(bloom_file, 'wb') as f:
        # Header: magic, version, size_bits, num_hashes, num_addresses
        f.write(b'BLOOM001')  # Magic + version
        f.write(struct.pack('<Q', BLOOM_SIZE_BITS))
        f.write(struct.pack('<I', NUM_HASH_FUNCTIONS))
        f.write(struct.pack('<Q', count))
        f.write(bytes(bloom))
    
    bloom_size = os.path.getsize(bloom_file)
    print(f'Bloom filter written: {bloom_size / 1024 / 1024:.1f} MB')
    
    # Write sorted hash160 for CPU verification
    print(f'Writing hash160 file to {hash160_file}...')
    hash160_list.sort()
    with open(hash160_file, 'wb') as f:
        f.write(struct.pack('<Q', len(hash160_list)))
        for h in hash160_list:
            f.write(h)
    
    hash160_size = os.path.getsize(hash160_file)
    print(f'Hash160 file written: {hash160_size / 1024 / 1024:.1f} MB')
    
    print('\nDone!')

if __name__ == '__main__':
    main()
