#!/usr/bin/env python3
"""
Fast bloom filter builder using mmh3 and bitarray.
"""
import mmh3
import gzip
import struct
import sys
import os
from bitarray import bitarray

# Bloom filter parameters
BLOOM_SIZE_BITS = 1_600_000_000  # 1.6 billion bits = 200MB
NUM_HASH_FUNCTIONS = 20

# Base58 alphabet
B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B58_MAP = {c: i for i, c in enumerate(B58_ALPHABET)}

BECH32_CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'

def b58decode(s):
    num = 0
    for c in s:
        if c not in B58_MAP:
            return None
        num = num * 58 + B58_MAP[c]
    
    result = []
    while num > 0:
        result.append(num & 0xff)
        num >>= 8
    
    for c in s:
        if c == '1':
            result.append(0)
        else:
            break
    
    return bytes(reversed(result))

def bech32_decode(addr):
    try:
        pos = addr.rfind('1')
        if pos < 1 or pos + 7 > len(addr):
            return None
        
        data_part = addr[pos+1:].lower()
        data = []
        for c in data_part:
            if c not in BECH32_CHARSET:
                return None
            data.append(BECH32_CHARSET.index(c))
        
        if len(data) < 6:
            return None
        
        values = data[:-6]
        if len(values) < 1:
            return None
        
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

def address_to_hash160(addr):
    try:
        if addr.startswith('1') or addr.startswith('3'):
            decoded = b58decode(addr)
            if decoded and len(decoded) >= 21:
                return decoded[1:21]
        elif addr.lower().startswith('bc1'):
            import hashlib
            witprog = bech32_decode(addr)
            if witprog:
                if len(witprog) == 20:
                    return witprog
                elif len(witprog) == 32:
                    return hashlib.new('ripemd160', hashlib.sha256(witprog).digest()).digest()
        return None
    except:
        return None

def main():
    input_file = '/workspace/bloom_search/btc_addresses.txt.gz'
    bloom_file = '/workspace/bloom_search/btc_addresses.bloom'
    
    print(f'Building bloom filter from {input_file}')
    print(f'Bloom filter size: {BLOOM_SIZE_BITS / 8 / 1024 / 1024:.1f} MB')
    print(f'Hash functions: {NUM_HASH_FUNCTIONS}')
    sys.stdout.flush()
    
    # Initialize bitarray
    bloom = bitarray(BLOOM_SIZE_BITS)
    bloom.setall(0)
    
    count = 0
    errors = 0
    
    with gzip.open(input_file, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            addr = line.strip()
            if not addr:
                continue
            
            hash160 = address_to_hash160(addr)
            if hash160 and len(hash160) == 20:
                # Add to bloom filter
                for i in range(NUM_HASH_FUNCTIONS):
                    h = mmh3.hash(hash160, i, signed=False) % BLOOM_SIZE_BITS
                    bloom[h] = 1
                count += 1
            else:
                errors += 1
            
            if count % 1_000_000 == 0:
                print(f'Processed {count:,} addresses... (errors: {errors:,})')
                sys.stdout.flush()
    
    print(f'\nTotal addresses processed: {count:,}')
    print(f'Total errors: {errors:,}')
    
    # Write bloom filter with header
    print(f'Writing bloom filter to {bloom_file}...')
    with open(bloom_file, 'wb') as f:
        f.write(b'BLOOM001')
        f.write(struct.pack('<Q', BLOOM_SIZE_BITS))
        f.write(struct.pack('<I', NUM_HASH_FUNCTIONS))
        f.write(struct.pack('<Q', count))
        bloom.tofile(f)
    
    bloom_size = os.path.getsize(bloom_file)
    print(f'Bloom filter written: {bloom_size / 1024 / 1024:.1f} MB')
    print('Done!')

if __name__ == '__main__':
    main()
