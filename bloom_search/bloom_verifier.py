#!/usr/bin/env python3
"""
Bloom filter verifier - check if found addresses are real matches.
Also provides CPU bloom checking for testing.
"""
import mmh3
import struct
import sys

class BloomFilter:
    def __init__(self, bloom_file):
        with open(bloom_file, 'rb') as f:
            magic = f.read(8)
            if magic != b'BLOOM001':
                raise ValueError('Invalid bloom filter format')
            
            self.size_bits = struct.unpack('<Q', f.read(8))[0]
            self.num_hashes = struct.unpack('<I', f.read(4))[0]
            self.num_addresses = struct.unpack('<Q', f.read(8))[0]
            
            from bitarray import bitarray
            self.bloom = bitarray()
            self.bloom.fromfile(f)
        
        print(f'Loaded bloom filter:')
        print(f'  Size: {self.size_bits / 8 / 1024 / 1024:.1f} MB')
        print(f'  Hash functions: {self.num_hashes}')
        print(f'  Addresses: {self.num_addresses:,}')
    
    def check(self, hash160):
        """Check if hash160 (20 bytes) is in bloom filter."""
        if len(hash160) != 20:
            return False
        
        for i in range(self.num_hashes):
            h = mmh3.hash(hash160, i, signed=False) % self.size_bits
            if not self.bloom[h]:
                return False
        return True
    
    def check_address(self, address):
        """Check if Bitcoin address is in bloom filter."""
        from build_bloom_fast import address_to_hash160
        hash160 = address_to_hash160(address)
        if hash160:
            return self.check(hash160)
        return False

def main():
    if len(sys.argv) < 2:
        print('Usage: bloom_verifier.py <bloom_file> [address...]')
        print('       bloom_verifier.py <bloom_file> -f <address_file>')
        return
    
    bloom_file = sys.argv[1]
    bf = BloomFilter(bloom_file)
    
    if len(sys.argv) == 2:
        # Interactive mode
        print('\nEnter addresses to check (Ctrl+D to exit):')
        try:
            for line in sys.stdin:
                addr = line.strip()
                if addr:
                    result = bf.check_address(addr)
                    print(f'{addr}: {"MATCH" if result else "no match"}')
        except EOFError:
            pass
    elif sys.argv[2] == '-f' and len(sys.argv) > 3:
        # File mode
        matches = 0
        total = 0
        with open(sys.argv[3], 'r') as f:
            for line in f:
                addr = line.strip()
                if addr:
                    total += 1
                    if bf.check_address(addr):
                        matches += 1
                        print(f'MATCH: {addr}')
        print(f'\nTotal: {total}, Matches: {matches}')
    else:
        # Command line addresses
        for addr in sys.argv[2:]:
            result = bf.check_address(addr)
            print(f'{addr}: {"MATCH" if result else "no match"}')

if __name__ == '__main__':
    main()
