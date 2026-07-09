#!/usr/bin/env python3
"""
Build a bloom filter from Bitcoin addresses for VanitySearch-bitcrack
Outputs binary bloom filter data and metadata for GPU loading
"""

import os
import sys
import struct
import hashlib
import base58
import mmh3
from bitarray import bitarray
import json

# Bloom filter parameters for ~55M addresses with <0.0001% FP rate
NUM_HASHES = 20
BITS_PER_ELEMENT = 28  # Results in ~0.00001% FP rate

def address_to_hash160(address):
    """Convert Bitcoin address to hash160 (20 bytes)"""
    try:
        if address.startswith('1') or address.startswith('3'):
            # P2PKH or P2SH
            decoded = base58.b58decode_check(address)
            return decoded[1:]  # Remove version byte
        elif address.startswith('bc1'):
            # Bech32 - skip for now, focus on legacy addresses
            return None
        else:
            return None
    except:
        return None

def build_bloom_filter(addresses_file, output_prefix):
    """Build bloom filter from address file"""
    
    print(f"Reading addresses from {addresses_file}...")
    
    # First pass: count valid addresses
    count = 0
    with open(addresses_file, 'r') as f:
        for line in f:
            addr = line.strip()
            if addr and (addr.startswith('1') or addr.startswith('3')):
                count += 1
    
    print(f"Found {count:,} valid addresses")
    
    # Calculate bloom filter size
    num_bits = count * BITS_PER_ELEMENT
    num_bytes = (num_bits + 7) // 8
    
    print(f"Bloom filter: {num_bits:,} bits ({num_bytes / (1024*1024):.2f} MB)")
    print(f"Using {NUM_HASHES} hash functions")
    
    # Generate random seeds for hash functions
    import random
    random.seed(42)  # Reproducible for testing
    seeds = [random.randint(0, 2**32-1) for _ in range(NUM_HASHES)]
    
    # Create bloom filter
    bloom = bitarray(num_bits)
    bloom.setall(0)
    
    # Second pass: add addresses to bloom filter
    print("Building bloom filter...")
    processed = 0
    with open(addresses_file, 'r') as f:
        for line in f:
            addr = line.strip()
            if not addr or not (addr.startswith('1') or addr.startswith('3')):
                continue
            
            hash160 = address_to_hash160(addr)
            if hash160 is None:
                continue
            
            # Add to bloom filter using multiple hashes
            for seed in seeds:
                h = mmh3.hash(hash160, seed, signed=False)
                bit_pos = h % num_bits
                bloom[bit_pos] = 1
            
            processed += 1
            if processed % 1000000 == 0:
                print(f"  Processed {processed:,} / {count:,}")
    
    print(f"Processed {processed:,} addresses")
    
    # Save bloom filter binary
    bloom_file = f"{output_prefix}.bloom"
    print(f"Saving bloom filter to {bloom_file}...")
    with open(bloom_file, 'wb') as f:
        bloom.tofile(f)
    
    # Save metadata
    meta = {
        'num_bits': num_bits,
        'num_bytes': num_bytes,
        'num_hashes': NUM_HASHES,
        'seeds': seeds,
        'num_addresses': processed
    }
    
    meta_file = f"{output_prefix}.json"
    with open(meta_file, 'w') as f:
        json.dump(meta, f, indent=2)
    
    # Save seeds in binary format for C++
    seeds_file = f"{output_prefix}.seeds"
    with open(seeds_file, 'wb') as f:
        f.write(struct.pack(f'{NUM_HASHES}I', *seeds))
    
    print(f"Saved metadata to {meta_file}")
    print(f"Saved seeds to {seeds_file}")
    
    # Calculate false positive rate
    k = NUM_HASHES
    n = processed
    m = num_bits
    fp_rate = (1 - (1 - 1/m)**(k*n))**k
    print(f"Expected false positive rate: {fp_rate:.10f} ({fp_rate*100:.8f}%)")
    
    return bloom_file, meta_file

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <addresses_file> <output_prefix>")
        sys.exit(1)
    
    build_bloom_filter(sys.argv[1], sys.argv[2])
