#!/usr/bin/env python3
"""
Fetch Satoshi addresses from Patoshi blocks using mempool.space API
Multi-threaded for speed
"""
import urllib.request
import json
import hashlib
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
API_BASE = "https://mempool.space/api"

addresses = {}  # block_num -> address
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

def fetch_block_address(block_num):
    global completed, errors
    for attempt in range(3):
        try:
            # Get block hash
            url1 = f"{API_BASE}/block-height/{block_num}"
            req1 = urllib.request.Request(url1, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req1, timeout=20) as response:
                block_hash = response.read().decode().strip()
            
            # Get txids
            url2 = f"{API_BASE}/block/{block_hash}/txids"
            req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=20) as response:
                txids = json.loads(response.read().decode())
            
            # Get coinbase tx
            url3 = f"{API_BASE}/tx/{txids[0]}"
            req3 = urllib.request.Request(url3, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req3, timeout=20) as response:
                tx = json.loads(response.read().decode())
            
            vout = tx["vout"][0]
            addr = None
            if "scriptpubkey_address" in vout:
                addr = vout["scriptpubkey_address"]
            elif vout.get("scriptpubkey_type") == "p2pk":
                scriptpubkey = vout["scriptpubkey"]
                pubkey_hex = scriptpubkey[2:-2]
                addr = pubkey_to_address(pubkey_hex)
            
            with lock:
                if addr:
                    addresses[block_num] = addr
                completed += 1
                if completed % 500 == 0:
                    print(f"Progress: {completed}/{len(blocks)} - {len(addresses)} addresses, {errors} errors")
                    sys.stdout.flush()
            return addr
        except Exception as e:
            if attempt == 2:
                with lock:
                    errors += 1
                    completed += 1
            time.sleep(0.5)
    return None

# Load blocks
with open("patoshi_blocks.txt", "r") as f:
    blocks = [int(line.strip()) for line in f if line.strip()]

THREADS = 50  # 50 concurrent threads

print(f"Fetching {len(blocks)} Patoshi blocks with {THREADS} threads...")
print(f"Using mempool.space API")
sys.stdout.flush()

start_time = time.time()

# Fetch in parallel
with ThreadPoolExecutor(max_workers=THREADS) as executor:
    futures = {executor.submit(fetch_block_address, b): b for b in blocks}
    for future in as_completed(futures):
        pass

elapsed = time.time() - start_time
print(f"\nDone in {elapsed:.1f} seconds!")
print(f"Total addresses: {len(addresses)}")
print(f"Errors: {errors}")

# Save sorted by block number
outpath = "satoshi_addresses_full.txt"
with open(outpath, "w") as f:
    for block_num in sorted(addresses.keys()):
        f.write(f"{addresses[block_num]}\n")

print(f"Saved to {outpath}")
