#!/usr/bin/env python3
"""Fast bloom filter build"""
import sys, struct, random, math, hashlib

def b58decode_check(addr):
    """Decode base58check address and return hash160"""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    try:
        n = 0
        for c in addr:
            n = n * 58 + alphabet.index(c)
        # Convert to bytes (variable length)
        h = hex(n)[2:]
        if len(h) % 2: h = "0" + h
        data = bytes.fromhex(h)
        # Pad to 25 bytes if needed (leading zeros)
        while len(data) < 25:
            data = b"\x00" + data
        if len(data) != 25:
            return None
        # Return hash160 (bytes 1-20, skip version byte)
        return data[1:21]
    except:
        return None

def murmur3(key, seed):
    c1, c2 = 0xcc9e2d51, 0x1b873593
    h1 = seed
    for i in range(0, 20, 4):
        k1 = int.from_bytes(key[i:i+4], "little")
        k1 = (k1 * c1) & 0xffffffff
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xffffffff
        k1 = (k1 * c2) & 0xffffffff
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xffffffff
        h1 = (h1 * 5 + 0xe6546b64) & 0xffffffff
    h1 ^= 20
    h1 ^= h1 >> 16
    h1 = (h1 * 0x85ebca6b) & 0xffffffff
    h1 ^= h1 >> 13
    h1 = (h1 * 0xc2b2ae35) & 0xffffffff
    h1 ^= h1 >> 16
    return h1

NUM_HASHES = 8
BITS_PER_ELEM = 12

addr_file = sys.argv[1]
out_prefix = sys.argv[2]

# First pass
print("Pass 1: Count and prefix table...", flush=True)
prefix_table = bytearray(8192)
n = 0
with open(addr_file) as f:
    for line in f:
        a = line.strip()
        if a and (a[0] == "1" or a[0] == "3"):
            h160 = b58decode_check(a)
            if h160:
                n += 1
                prefix16 = (h160[0] << 8) | h160[1]
                prefix_table[prefix16 >> 3] |= 1 << (prefix16 & 7)
        if n > 0 and n % 1000000 == 0:
            print(f"  {n:,}...", flush=True)

print(f"Found {n:,} addresses", flush=True)
prefix_count = sum(bin(b).count("1") for b in prefix_table)
print(f"  {prefix_count:,} prefixes", flush=True)

# Bloom filter
num_bits = n * BITS_PER_ELEM
num_bytes = (num_bits + 7) // 8
print(f"\nBloom: {num_bits:,} bits ({num_bytes/1e6:.1f} MB)", flush=True)

random.seed(42)
seeds = [random.randint(0, 2**32-1) for _ in range(NUM_HASHES)]
bloom = bytearray(num_bytes)

# Second pass
print("\nPass 2: Build bloom...", flush=True)
i = 0
with open(addr_file) as f:
    for line in f:
        a = line.strip()
        if a and (a[0] == "1" or a[0] == "3"):
            h160 = b58decode_check(a)
            if h160:
                for seed in seeds:
                    h = murmur3(h160, seed)
                    pos = h % num_bits
                    bloom[pos >> 3] |= 1 << (pos & 7)
                i += 1
                if i % 1000000 == 0:
                    print(f"  {i:,} / {n:,}", flush=True)

# Save
with open(f"{out_prefix}.prefix", "wb") as f:
    f.write(prefix_table)
with open(f"{out_prefix}.bloom", "wb") as f:
    f.write(bloom)
with open(f"{out_prefix}.seeds", "wb") as f:
    f.write(struct.pack(f"{NUM_HASHES}I", *seeds))
with open(f"{out_prefix}.info", "w") as f:
    f.write(f"bits={num_bits}\nhashes={NUM_HASHES}\naddresses={n}\nprefixes={prefix_count}\n")

fp = (1 - math.exp(-NUM_HASHES * n / num_bits)) ** NUM_HASHES
print(f"\nDone! FP: {fp:.2e}", flush=True)
