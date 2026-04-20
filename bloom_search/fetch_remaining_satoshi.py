#!/usr/bin/env python3
"""
Fetch remaining Satoshi addresses from Patoshi blocks using Blockstream API.
Converts P2PK outputs to Bitcoin addresses.
"""
import urllib.request
import json
import hashlib
import time
import os

ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def b58encode(data):
    n = int.from_bytes(data, 'big')
    result = ''
    while n > 0:
        n, r = divmod(n, 58)
        result = ALPHABET[r] + result
    for byte in data:
        if byte == 0:
            result = '1' + result
        else:
            break
    return result or '1'

def pubkey_to_address(pubkey_hex):
    pubkey_bytes = bytes.fromhex(pubkey_hex)
    sha256_hash = hashlib.sha256(pubkey_bytes).digest()
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    hash160 = ripemd160.digest()
    versioned = b'\x00' + hash160
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    return b58encode(versioned + checksum)

def fetch_address(block_num):
    try:
        url1 = f"https://blockstream.info/api/block-height/{block_num}"
        req1 = urllib.request.Request(url1, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req1, timeout=15) as response:
            block_hash = response.read().decode().strip()
        
        url2 = f"https://blockstream.info/api/block/{block_hash}/txids"
        req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req2, timeout=15) as response:
            txids = json.loads(response.read().decode())
            coinbase_txid = txids[0]
        
        url3 = f"https://blockstream.info/api/tx/{coinbase_txid}"
        req3 = urllib.request.Request(url3, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req3, timeout=15) as response:
            tx = json.loads(response.read().decode())
        
        vout = tx['vout'][0]
        
        if 'scriptpubkey_address' in vout:
            return vout['scriptpubkey_address']
        elif vout.get('scriptpubkey_type') == 'p2pk':
            scriptpubkey = vout['scriptpubkey']
            pubkey_hex = scriptpubkey[2:-2]
            return pubkey_to_address(pubkey_hex)
        return None
    except Exception as e:
        print(f"Error block {block_num}: {e}")
        return None

# Load existing addresses
existing = set()
if os.path.exists('satoshi_addresses.txt'):
    with open('satoshi_addresses.txt', 'r') as f:
        existing = set(line.strip() for line in f if line.strip())
print(f"Already have {len(existing)} addresses")

# Load block list
with open('patoshi_blocks.txt', 'r') as f:
    blocks = [int(line.strip()) for line in f if line.strip()]
print(f"Total blocks to process: {len(blocks)}")

# Continue fetching
addresses = list(existing)
outfile = open('satoshi_addresses.txt', 'a')

for i, block_num in enumerate(blocks):
    addr = fetch_address(block_num)
    if addr and addr not in existing:
        addresses.append(addr)
        existing.add(addr)
        outfile.write(f"{addr}\n")
        outfile.flush()
    
    if (i + 1) % 500 == 0:
        print(f"Progress: {i+1}/{len(blocks)} blocks, {len(addresses)} unique addresses")
    
    time.sleep(0.15)

outfile.close()
print(f"Done! Total: {len(addresses)} addresses")
