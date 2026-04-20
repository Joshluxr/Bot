#!/usr/bin/env python3
"""Fetch all Satoshi addresses from Patoshi blocks using mempool.space API"""
import urllib.request
import json
import hashlib
import time
import sys
import os

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
API_BASE = "https://mempool.space/api"

def b58encode(data):
    n = int.from_bytes(data, "big")
    result = ""
    while n > 0:
        n, r = divmod(n, 58)
        result = ALPHABET[r] + result
    for byte in data:
        if byte == 0:
            result = "1" + result
        else:
            break
    return result or "1"

def pubkey_to_address(pubkey_hex):
    pubkey_bytes = bytes.fromhex(pubkey_hex)
    sha256_hash = hashlib.sha256(pubkey_bytes).digest()
    ripemd160 = hashlib.new("ripemd160")
    ripemd160.update(sha256_hash)
    hash160 = ripemd160.digest()
    versioned = b"\x00" + hash160
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    return b58encode(versioned + checksum)

def fetch_address(block_num, retries=3):
    for attempt in range(retries):
        try:
            # Get block hash
            url1 = f"{API_BASE}/block-height/{block_num}"
            req1 = urllib.request.Request(url1, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req1, timeout=15) as response:
                block_hash = response.read().decode().strip()
            
            # Get block info with txids
            url2 = f"{API_BASE}/block/{block_hash}/txids"
            req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=15) as response:
                txids = json.loads(response.read().decode())
            
            # Get coinbase tx
            url3 = f"{API_BASE}/tx/{txids[0]}"
            req3 = urllib.request.Request(url3, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req3, timeout=15) as response:
                tx = json.loads(response.read().decode())
            
            vout = tx["vout"][0]
            if "scriptpubkey_address" in vout:
                return vout["scriptpubkey_address"]
            elif vout.get("scriptpubkey_type") == "p2pk":
                scriptpubkey = vout["scriptpubkey"]
                pubkey_hex = scriptpubkey[2:-2]
                return pubkey_to_address(pubkey_hex)
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            continue
    return None

# Load blocks
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, "patoshi_blocks.txt"), "r") as f:
    blocks = [int(line.strip()) for line in f if line.strip()]

# Load existing addresses to resume
existing = set()
outpath = os.path.join(script_dir, "satoshi_addresses_full.txt")
if os.path.exists(outpath):
    with open(outpath, "r") as f:
        for line in f:
            if line.strip():
                existing.add(line.strip())

print(f"Starting with {len(existing)} existing addresses")
print(f"Fetching {len(blocks)} Patoshi block addresses...")
sys.stdout.flush()

addresses = list(existing)
errors = 0
outfile = open(outpath, "a")

for i, block_num in enumerate(blocks):
    # Skip if we already have this block's address (rough check by count)
    if i < len(existing):
        continue
    
    addr = fetch_address(block_num)
    if addr:
        addresses.append(addr)
        outfile.write(f"{addr}\n")
    else:
        errors += 1
    
    if (i + 1) % 100 == 0:
        outfile.flush()
        print(f"Progress: {i+1}/{len(blocks)} - {len(addresses)} addresses, {errors} errors")
        sys.stdout.flush()
    
    time.sleep(0.15)

outfile.close()
print(f"Done! {len(addresses)} total addresses in {outpath}")
