#!/usr/bin/env python3
from bloom_verifier import BloomFilter
import os

bf = BloomFilter('/workspace/bloom_search/btc_addresses.bloom')

# Test with known addresses
test_addrs = [
    '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',  # Satoshi genesis
    '3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy',  # Random P2SH
    '1BitcoinEaterAddressDontSendf59kuE',   # Burn address
    'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',  # Bech32
]

print('Testing known addresses:')
for addr in test_addrs:
    result = bf.check_address(addr)
    status = 'MATCH' if result else 'no match'
    print(f'  {addr}: {status}')

# Test false positive rate
print()
print('Testing random hash160 values:')
matches = 0
total = 1000
for i in range(total):
    random_hash = os.urandom(20)
    if bf.check(random_hash):
        matches += 1

print(f'  Random matches: {matches}/{total}')
