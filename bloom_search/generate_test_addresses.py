#!/usr/bin/env python3
"""Generate test Bitcoin addresses for filter testing."""

import hashlib
import os

B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def sha256(data):
    return hashlib.sha256(data).digest()

def ripemd160(data):
    h = hashlib.new('ripemd160')
    h.update(data)
    return h.digest()

def base58_encode(data):
    n = int.from_bytes(data, 'big')
    result = ''
    while n > 0:
        n, r = divmod(n, 58)
        result = B58_ALPHABET[r] + result
    # Add leading '1's for leading zero bytes
    for b in data:
        if b == 0:
            result = '1' + result
        else:
            break
    return result

def hash160_to_address(h160, version=0x00):
    """Convert hash160 to Bitcoin address."""
    vh160 = bytes([version]) + h160
    checksum = sha256(sha256(vh160))[:4]
    return base58_encode(vh160 + checksum)

def generate_random_addresses(count, filename):
    """Generate random Bitcoin addresses."""
    print(f"Generating {count:,} random test addresses...")
    
    with open(filename, 'w') as f:
        for i in range(count):
            # Random hash160
            h160 = os.urandom(20)
            
            # 70% type 1, 30% type 3
            if i % 10 < 7:
                addr = hash160_to_address(h160, 0x00)  # P2PKH (1xxx)
            else:
                addr = hash160_to_address(h160, 0x05)  # P2SH (3xxx)
            
            f.write(addr + '\n')
            
            if (i + 1) % 100000 == 0:
                print(f"  Generated {i + 1:,} addresses...")
    
    print(f"Saved to {filename}")

if __name__ == '__main__':
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    filename = sys.argv[2] if len(sys.argv) > 2 else 'test_addresses.txt'
    generate_random_addresses(count, filename)
