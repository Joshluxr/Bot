#!/usr/bin/env python3
"""
K3 Debug Test Script
=====================
This script runs on the GPU server to debug why specific target keys
are not being found by K3.

Target: Private key 74120947517767895891355266452452269842804955139343486161984562552406380210176
Hash160 (uncompressed): abeddf6b115157b704de34c50d22beefbeb59c98
Address: 1Gg5WVQsrfk8L9uMpmtsFqW7NoS2ZpoKPs
"""

import hashlib
import struct
import os
import sys

# ============================================================================
# secp256k1 Parameters (same as K3)
# ============================================================================
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

# Target values
TARGET_DECIMAL = "74120947517767895891355266452452269842804955139343486161984562552406380210176"
TARGET_START = "74120947517767895891355266452452269842804955139343486161984562552406380000000"
EXPECTED_H160_UNCOMP = "abeddf6b115157b704de34c50d22beefbeb59c98"

# ============================================================================
# Elliptic Curve Math
# ============================================================================
def mod_inverse(a, p=P):
    if a < 0:
        a = a % p
    g, x, _ = extended_gcd(a, p)
    if g != 1:
        raise ValueError("Modular inverse does not exist")
    return x % p

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def point_add(x1, y1, x2, y2):
    if x1 is None:
        return x2, y2
    if x2 is None:
        return x1, y1
    if x1 == x2 and y1 == y2:
        s = (3 * x1 * x1 * mod_inverse(2 * y1)) % P
    elif x1 == x2:
        return None, None
    else:
        s = ((y2 - y1) * mod_inverse(x2 - x1)) % P
    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P
    return x3, y3

def scalar_mult(k, x=GX, y=GY):
    rx, ry = None, None
    qx, qy = x, y
    while k > 0:
        if k & 1:
            rx, ry = point_add(rx, ry, qx, qy)
        qx, qy = point_add(qx, qy, qx, qy)
        k >>= 1
    return rx, ry

# ============================================================================
# Hash Functions
# ============================================================================
def compute_hash160(pubkey_bytes):
    sha256_hash = hashlib.sha256(pubkey_bytes).digest()
    ripemd160 = hashlib.new('ripemd160', sha256_hash).digest()
    return ripemd160

def murmur3_32(key, seed):
    """MurmurHash3 32-bit - matches K3's implementation"""
    c1 = 0xcc9e2d51
    c2 = 0x1b873593
    h1 = seed & 0xFFFFFFFF

    nblocks = len(key) // 4
    for i in range(nblocks):
        k1 = struct.unpack('<I', key[i*4:(i+1)*4])[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF
        h1 = ((h1 * 5) + 0xe6546b64) & 0xFFFFFFFF

    tail = key[nblocks * 4:]
    k1 = 0
    if len(tail) >= 3:
        k1 ^= tail[2] << 16
    if len(tail) >= 2:
        k1 ^= tail[1] << 8
    if len(tail) >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1

    h1 ^= len(key)
    h1 ^= (h1 >> 16)
    h1 = (h1 * 0x85ebca6b) & 0xFFFFFFFF
    h1 ^= (h1 >> 13)
    h1 = (h1 * 0xc2b2ae35) & 0xFFFFFFFF
    h1 ^= (h1 >> 16)

    return h1

# ============================================================================
# Bloom Filter Check
# ============================================================================
def check_bloom_and_mask(h160_bytes, bloom_data, bloom_mask, seeds):
    """Check if h160 passes bloom filter using K3's AND mask method"""
    all_pass = True
    results = []
    for seed in seeds:
        h = murmur3_32(h160_bytes, seed)
        bit_pos = h & bloom_mask
        word_pos = bit_pos >> 5
        bit_mask = 1 << (bit_pos & 31)

        if word_pos * 4 + 4 <= len(bloom_data):
            word = struct.unpack('<I', bloom_data[word_pos*4:(word_pos+1)*4])[0]
            is_set = bool(word & bit_mask)
        else:
            is_set = False

        results.append({
            'seed': seed,
            'hash': h,
            'bit_pos': bit_pos,
            'word_pos': word_pos,
            'bit_mask': bit_mask,
            'is_set': is_set
        })
        if not is_set:
            all_pass = False

    return all_pass, results

def check_prefix_table(h160_as_u32, prefix_table):
    """Check 32-bit prefix bitmap (first tier)"""
    # K3 uses __byte_perm(h[0], 0, 0x0123) which reverses bytes
    prefix32 = ((h160_as_u32[0] >> 24) & 0xFF) | \
               ((h160_as_u32[0] >> 8) & 0xFF00) | \
               ((h160_as_u32[0] << 8) & 0xFF0000) | \
               ((h160_as_u32[0] << 24) & 0xFF000000)

    byte_idx = prefix32 >> 3
    bit_idx = prefix32 & 7

    if byte_idx < len(prefix_table):
        is_set = bool(prefix_table[byte_idx] & (1 << bit_idx))
    else:
        is_set = False

    return {
        'h0': h160_as_u32[0],
        'prefix32': prefix32,
        'byte_idx': byte_idx,
        'bit_idx': bit_idx,
        'is_set': is_set
    }

# ============================================================================
# Main Test
# ============================================================================
def main():
    print("="*70)
    print("K3 DEBUG TEST")
    print("="*70)

    # Compute target hash160
    target_k = int(TARGET_DECIMAL)
    x, y = scalar_mult(target_k)

    uncompressed = b'\x04' + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')
    h160_uncomp = compute_hash160(uncompressed)

    print(f"\nTarget private key: {TARGET_DECIMAL[:40]}...")
    print(f"Target hash160 (uncompressed): {h160_uncomp.hex()}")
    print(f"Expected: {EXPECTED_H160_UNCOMP}")
    print(f"Match: {h160_uncomp.hex() == EXPECTED_H160_UNCOMP}")

    # Convert to uint32 array (K3 format)
    h160_as_u32 = []
    for i in range(5):
        val = struct.unpack('<I', h160_uncomp[i*4:(i+1)*4])[0]
        h160_as_u32.append(val)

    print(f"\nHash160 as uint32[5]: [{', '.join(f'0x{v:08x}' for v in h160_as_u32)}]")

    # Check data files
    print("\n" + "="*70)
    print("DATA FILE CHECKS")
    print("="*70)

    data_files = {
        'prefix': '/data/prefix32.bin',
        'bloom': '/data/bloom_filter.bin',
        'seeds': '/data/bloom_seeds.bin',
        'h160db': '/data/bloom_opt.h160db'
    }

    for name, path in data_files.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  {name}: {path} ({size:,} bytes = {size/1024/1024:.2f} MB)")
        else:
            print(f"  {name}: {path} NOT FOUND")

    # Load and check prefix table
    prefix_path = data_files['prefix']
    if os.path.exists(prefix_path):
        print(f"\n--- Prefix Table Check ---")
        with open(prefix_path, 'rb') as f:
            prefix_table = f.read()

        result = check_prefix_table(h160_as_u32, prefix_table)
        print(f"  h[0] = 0x{result['h0']:08x}")
        print(f"  prefix32 (byte-reversed) = 0x{result['prefix32']:08x}")
        print(f"  Byte index = {result['byte_idx']}")
        print(f"  Bit index = {result['bit_idx']}")
        print(f"  Prefix table size = {len(prefix_table)} bytes")
        print(f"  IS SET: {result['is_set']}")

        if not result['is_set']:
            print("  WARNING: Prefix check would FAIL - address not in prefix table!")

    # Load and check bloom filter
    bloom_path = data_files['bloom']
    seeds_path = data_files['seeds']

    if os.path.exists(bloom_path) and os.path.exists(seeds_path):
        print(f"\n--- Bloom Filter Check ---")
        with open(bloom_path, 'rb') as f:
            bloom_data = f.read()
        with open(seeds_path, 'rb') as f:
            seeds_data = f.read()

        num_seeds = len(seeds_data) // 4
        seeds = [struct.unpack('<I', seeds_data[i*4:(i+1)*4])[0] for i in range(num_seeds)]

        bloom_bits = len(bloom_data) * 8
        # K3 uses power-of-2 mask
        bloom_mask = 1
        while bloom_mask * 2 <= bloom_bits:
            bloom_mask *= 2
        bloom_mask -= 1

        print(f"  Bloom filter: {len(bloom_data):,} bytes = {bloom_bits:,} bits")
        print(f"  K3 mask (power of 2): 0x{bloom_mask:x} ({bloom_mask+1:,} bits)")
        print(f"  Seeds ({num_seeds}): {seeds}")

        all_pass, results = check_bloom_and_mask(h160_uncomp, bloom_data, bloom_mask, seeds)

        print(f"\n  Bloom filter results:")
        for r in results:
            status = "PASS" if r['is_set'] else "FAIL"
            print(f"    Seed {r['seed']:08x}: h=0x{r['hash']:08x} bitPos={r['bit_pos']:,} -> {status}")

        print(f"\n  OVERALL: {'ALL PASS' if all_pass else 'FAILED'}")

        if not all_pass:
            print("  WARNING: Bloom filter check would FAIL!")

    # Check if target is in h160db
    h160db_path = data_files['h160db']
    if os.path.exists(h160db_path):
        print(f"\n--- Hash160 Database Check ---")
        with open(h160db_path, 'rb') as f:
            h160db_data = f.read()

        num_entries = len(h160db_data) // 20
        print(f"  Database: {num_entries:,} entries")

        # Linear search (slow but definitive)
        found = False
        for i in range(num_entries):
            entry = h160db_data[i*20:(i+1)*20]
            if entry == h160_uncomp:
                found = True
                print(f"  Target FOUND at index {i}")
                break

        if not found:
            print(f"  Target NOT FOUND in database!")
            print("  This means the address doesn't have a balance to find.")

    print("\n" + "="*70)
    print("K3 THREAD/ITERATION CALCULATION")
    print("="*70)

    start_k = int(TARGET_START)
    offset = target_k - start_k

    nbThread = 65536  # K3_TOTAL_THREADS
    step_size = 1024   # K3_STEP_SIZE

    thread_id = offset % step_size
    iteration = offset // step_size

    print(f"\n  Start key: {TARGET_START[:40]}...")
    print(f"  Target offset: {offset}")
    print(f"  K3 threads: {nbThread}")
    print(f"  K3 step size: {step_size}")
    print(f"\n  Thread ID: {thread_id}")
    print(f"  Kernel iteration: {iteration}")
    print(f"\n  Verification: {thread_id} + {iteration} * {step_size} = {thread_id + iteration * step_size}")
    print(f"  Correct: {thread_id + iteration * step_size == offset}")

if __name__ == "__main__":
    main()
