#!/usr/bin/env python3
"""
Fetch Satoshi addresses using multiple APIs in rotation to avoid rate limits
"""
import urllib.request
import json
import hashlib
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import random

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

# Multiple API endpoints to rotate
APIS = [
    "https://mempool.space/api",
    "https://blockstream.info/api",
    "https://blockchain.info",
]

addresses = {}
lock = threading.Lock()
completed = 0
errors = 0

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

def fetch_with_mempool(block_num):
    api = "https://mempool.space/api"
    url1 = f"{api}/block-height/{block_num}"
    req1 = urllib.request.Request(url1, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req1, timeout=15) as response:
        block_hash = response.read().decode().strip()
    
    url2 = f"{api}/block/{block_hash}/txids"
    req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req2, timeout=15) as response:
        txids = json.loads(response.read().decode())
    
    url3 = f"{api}/tx/{txids[0]}"
    req3 = urllib.request.Request(url3, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req3, timeout=15) as response:
        tx = json.loads(response.read().decode())
    
    vout = tx["vout"][0]
    if "scriptpubkey_address" in vout:
        return vout["scriptpubkey_address"]
    elif vout.get("scriptpubkey_type") == "p2pk":
        pubkey_hex = vout["scriptpubkey"][2:-2]
        return pubkey_to_address(pubkey_hex)
    return None

def fetch_block_address(block_num):
    global completed, errors
    for attempt in range(5):
        try:
            addr = fetch_with_mempool(block_num)
            with lock:
                if addr:
                    addresses[block_num] = addr
                completed += 1
                if completed % 200 == 0:
                    print(f"Progress: {completed}/{total_blocks} - {len(addresses)} addresses, {errors} errors")
                    sys.stdout.flush()
            return addr
        except Exception as e:
            if attempt == 4:
                with lock:
                    errors += 1
                    completed += 1
            time.sleep(0.5 + random.random())
    return None

# Load blocks
with open("patoshi_blocks.txt", "r") as f:
    blocks = [int(line.strip()) for line in f if line.strip()]

# Load existing to skip
existing = set()
try:
    with open("satoshi_addresses_full.txt", "r") as f:
        for i, line in enumerate(f):
            if line.strip():
                existing.add(blocks[i] if i < len(blocks) else 0)
except:
    pass

# Filter blocks we still need
remaining = [b for b in blocks if b not in existing]
total_blocks = len(remaining)

print(f"Already have {len(existing)} addresses")
print(f"Fetching {total_blocks} remaining blocks with 20 threads...")
sys.stdout.flush()

start_time = time.time()

# Slower but more reliable - 20 threads
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(fetch_block_address, b): b for b in remaining}
    for future in as_completed(futures):
        pass

elapsed = time.time() - start_time
print(f"\nDone in {elapsed:.1f} seconds!")
print(f"New addresses: {len(addresses)}")
print(f"Errors: {errors}")

# Append new addresses
with open("satoshi_addresses_full.txt", "a") as f:
    for block_num in sorted(addresses.keys()):
        f.write(f"{addresses[block_num]}\n")

print(f"Total addresses in file now")
