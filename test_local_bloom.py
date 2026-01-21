#!/usr/bin/env python3
"""Test target against local bloom filter files"""

import hashlib
import struct
import os

# Target hash160 (uncompressed)
TARGET_H160 = bytes.fromhex("abeddf6b115157b704de34c50d22beefbeb59c98")

def murmur3_32(key, seed):
    """MurmurHash3 32-bit"""
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

def test_bloom_modulo(h160, bloom_data, bits, seeds):
    """Test bloom with MODULO (original method)"""
    print(f"\nTesting with MODULO (h % {bits}):")
    all_pass = True
    for seed in seeds:
        h = murmur3_32(h160, seed)
        bit_pos = h % bits
        byte_pos = bit_pos // 8
        bit_in_byte = bit_pos % 8

        if byte_pos < len(bloom_data):
            is_set = bool(bloom_data[byte_pos] & (1 << bit_in_byte))
        else:
            is_set = False

        status = "PASS" if is_set else "FAIL"
        print(f"  Seed {seed:08x}: h={h:08x} bitPos={bit_pos:,} -> {status}")
        if not is_set:
            all_pass = False

    return all_pass

def test_bloom_and_mask(h160, bloom_data, bits, seeds):
    """Test bloom with AND mask (K3 method)"""
    # Find nearest power of 2
    mask = 1
    while mask < bits:
        mask *= 2
    mask -= 1  # Now mask+1 is >= bits and is power of 2

    print(f"\nTesting with AND mask (h & 0x{mask:x}):")
    all_pass = True
    for seed in seeds:
        h = murmur3_32(h160, seed)
        bit_pos = h & mask
        byte_pos = bit_pos // 8
        bit_in_byte = bit_pos % 8

        if byte_pos < len(bloom_data):
            is_set = bool(bloom_data[byte_pos] & (1 << bit_in_byte))
        else:
            is_set = False

        status = "PASS" if is_set else "FAIL"
        print(f"  Seed {seed:08x}: h={h:08x} bitPos={bit_pos:,} -> {status}")
        if not is_set:
            all_pass = False

    return all_pass

def main():
    print("="*60)
    print("Local Bloom Filter Test")
    print("="*60)

    bloom_path = "/tmp/bloom_v2/bloom_v2.bloom"
    seeds_path = "/tmp/bloom_v2/bloom_v2.seeds"
    info_path = "/tmp/bloom_v2/bloom_v2.info"

    if not os.path.exists(bloom_path):
        print("Bloom filter not found. Run: unzip -o VanitySearch-bitcrack/bloom/bloom_v2.zip -d /tmp/bloom_v2/")
        return

    # Read info
    bits = 335098344
    with open(info_path) as f:
        for line in f:
            if line.startswith("bits="):
                bits = int(line.split("=")[1].strip())

    print(f"\nTarget hash160: {TARGET_H160.hex()}")
    print(f"Bloom filter bits: {bits:,}")

    # Read bloom data
    with open(bloom_path, 'rb') as f:
        bloom_data = f.read()
    print(f"Bloom file size: {len(bloom_data):,} bytes = {len(bloom_data)*8:,} bits")

    # Read seeds
    with open(seeds_path, 'rb') as f:
        seeds_data = f.read()
    seeds = [struct.unpack('<I', seeds_data[i*4:(i+1)*4])[0] for i in range(len(seeds_data)//4)]
    print(f"Seeds ({len(seeds)}): {[hex(s) for s in seeds]}")

    # Test with modulo
    modulo_pass = test_bloom_modulo(TARGET_H160, bloom_data, bits, seeds)

    # Test with AND mask
    mask_pass = test_bloom_and_mask(TARGET_H160, bloom_data, bits, seeds)

    print("\n" + "="*60)
    print("RESULTS:")
    print(f"  MODULO method: {'PASS' if modulo_pass else 'FAIL'}")
    print(f"  AND mask method: {'PASS' if mask_pass else 'FAIL'}")

    if modulo_pass and not mask_pass:
        print("\n  WARNING: Bloom was built with MODULO but K3 uses AND mask!")
        print("  This is likely the root cause of the detection failure.")
        print("  Solution: Rebuild bloom filter using AND mask method.")
    elif not modulo_pass and not mask_pass:
        print("\n  WARNING: Target hash160 is NOT in the bloom filter at all!")
        print("  This could mean:")
        print("    1. The address has no balance in the database")
        print("    2. The bloom filter was built from a different database")

if __name__ == "__main__":
    main()
