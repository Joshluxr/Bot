#!/usr/bin/env python3
"""
Build K3-Compatible Bloom Filter
================================

This script rebuilds a bloom filter using K3's AND mask method instead of MODULO.

K3 requires:
1. Power-of-2 bloom filter size (for fast h & mask operation)
2. AND masking: bit_pos = murmur3_hash & (size - 1)

The original bloom filter was built with MODULO which is incompatible.
"""

import struct
import os
import sys
import hashlib
from array import array

def murmur3_32(key, seed):
    """MurmurHash3 32-bit - matches K3's implementation exactly"""
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

def next_power_of_2(n):
    """Round up to next power of 2"""
    n -= 1
    n |= n >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16
    n |= n >> 32
    return n + 1

def build_k3_bloom(h160db_path, output_bloom, output_seeds, bloom_bits=None, num_hashes=12):
    """
    Build K3-compatible bloom filter from hash160 database.

    Args:
        h160db_path: Path to sorted hash160 database (20 bytes per entry)
        output_bloom: Output bloom filter path
        output_seeds: Output seeds file path
        bloom_bits: Bloom filter size in bits (must be power of 2). If None, auto-calculate.
        num_hashes: Number of hash functions (default: 12)
    """
    # Check input file
    if not os.path.exists(h160db_path):
        print(f"ERROR: h160db file not found: {h160db_path}")
        return False

    file_size = os.path.getsize(h160db_path)
    num_entries = file_size // 20

    print(f"Input: {h160db_path}")
    print(f"  Size: {file_size:,} bytes")
    print(f"  Entries: {num_entries:,}")

    # Auto-calculate bloom size if not specified
    # Target: ~10 bits per element for ~1% false positive rate
    if bloom_bits is None:
        bloom_bits = next_power_of_2(num_entries * 10)
        print(f"  Auto-calculated bloom bits: {bloom_bits:,}")

    # Ensure power of 2
    if bloom_bits != next_power_of_2(bloom_bits):
        bloom_bits = next_power_of_2(bloom_bits)
        print(f"  Adjusted to power of 2: {bloom_bits:,}")

    bloom_bytes = bloom_bits // 8
    bloom_mask = bloom_bits - 1

    print(f"\nBloom filter configuration:")
    print(f"  Bits: {bloom_bits:,} (0x{bloom_bits:x})")
    print(f"  Bytes: {bloom_bytes:,} ({bloom_bytes / (1024*1024):.2f} MB)")
    print(f"  Mask: 0x{bloom_mask:x}")
    print(f"  Hashes: {num_hashes}")

    # Generate random seeds
    import random
    random.seed(42)  # Fixed seed for reproducibility
    seeds = [random.randint(1, 0xFFFFFFFF) for _ in range(num_hashes)]
    print(f"  Seeds: {[hex(s) for s in seeds]}")

    # Allocate bloom filter
    print(f"\nAllocating bloom filter ({bloom_bytes / (1024*1024):.2f} MB)...")
    bloom = bytearray(bloom_bytes)

    # Process hash160 database
    print(f"Processing {num_entries:,} entries...")

    with open(h160db_path, 'rb') as f:
        for i in range(num_entries):
            h160 = f.read(20)
            if len(h160) != 20:
                print(f"  Warning: incomplete entry at position {i}")
                break

            # Add to bloom filter using AND mask (K3 method)
            for seed in seeds:
                h = murmur3_32(h160, seed)
                bit_pos = h & bloom_mask  # K3 method: AND mask
                byte_pos = bit_pos >> 3
                bit_in_byte = bit_pos & 7
                bloom[byte_pos] |= (1 << bit_in_byte)

            if (i + 1) % 1000000 == 0:
                print(f"  Processed {i+1:,} / {num_entries:,} entries ({100*(i+1)/num_entries:.1f}%)")

    print(f"  Done! Processed {num_entries:,} entries.")

    # Save bloom filter
    print(f"\nSaving bloom filter to {output_bloom}...")
    with open(output_bloom, 'wb') as f:
        f.write(bloom)

    # Save seeds
    print(f"Saving seeds to {output_seeds}...")
    with open(output_seeds, 'wb') as f:
        for seed in seeds:
            f.write(struct.pack('<I', seed))

    # Save info file
    info_path = output_bloom.replace('.bloom', '.info')
    print(f"Saving info to {info_path}...")
    with open(info_path, 'w') as f:
        f.write(f"bits={bloom_bits}\n")
        f.write(f"hashes={num_hashes}\n")
        f.write(f"addresses={num_entries}\n")
        f.write(f"method=AND_MASK\n")
        f.write(f"mask=0x{bloom_mask:x}\n")

    # Verify a few entries
    print("\nVerification (first 5 entries):")
    with open(h160db_path, 'rb') as f:
        for i in range(min(5, num_entries)):
            h160 = f.read(20)
            all_pass = True
            for seed in seeds:
                h = murmur3_32(h160, seed)
                bit_pos = h & bloom_mask
                byte_pos = bit_pos >> 3
                bit_in_byte = bit_pos & 7
                if not (bloom[byte_pos] & (1 << bit_in_byte)):
                    all_pass = False
                    break
            status = "PASS" if all_pass else "FAIL"
            print(f"  Entry {i}: {h160.hex()} -> {status}")

    print("\n" + "="*60)
    print("K3-COMPATIBLE BLOOM FILTER CREATED")
    print("="*60)
    print(f"  Bloom: {output_bloom} ({os.path.getsize(output_bloom):,} bytes)")
    print(f"  Seeds: {output_seeds} ({os.path.getsize(output_seeds):,} bytes)")
    print(f"  Info:  {info_path}")
    print(f"\nK3 command line parameters:")
    print(f"  -bloom {output_bloom} -seeds {output_seeds} -bits {bloom_bits} -hashes {num_hashes}")

    return True

def test_target_in_bloom(bloom_path, seeds_path, target_h160_hex):
    """Test if a specific hash160 is in the bloom filter"""
    target = bytes.fromhex(target_h160_hex)

    with open(bloom_path, 'rb') as f:
        bloom = f.read()

    with open(seeds_path, 'rb') as f:
        seeds_data = f.read()

    num_seeds = len(seeds_data) // 4
    seeds = [struct.unpack('<I', seeds_data[i*4:(i+1)*4])[0] for i in range(num_seeds)]

    bloom_bits = len(bloom) * 8
    bloom_mask = bloom_bits - 1

    print(f"\nTesting target hash160: {target_h160_hex}")
    print(f"  Bloom bits: {bloom_bits:,}")
    print(f"  Mask: 0x{bloom_mask:x}")
    print(f"  Seeds: {num_seeds}")

    all_pass = True
    for seed in seeds:
        h = murmur3_32(target, seed)
        bit_pos = h & bloom_mask
        byte_pos = bit_pos >> 3
        bit_in_byte = bit_pos & 7
        is_set = bool(bloom[byte_pos] & (1 << bit_in_byte))
        status = "PASS" if is_set else "FAIL"
        print(f"    Seed {seed:08x}: h={h:08x} bitPos={bit_pos:,} -> {status}")
        if not is_set:
            all_pass = False

    print(f"\n  RESULT: {'ALL PASS' if all_pass else 'FAILED'}")
    return all_pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Build bloom:  python3 build_k3_bloom.py build <h160db> <output_bloom> <output_seeds> [bits] [hashes]")
        print("  Test target:  python3 build_k3_bloom.py test <bloom> <seeds> <hash160_hex>")
        print("")
        print("Example:")
        print("  python3 build_k3_bloom.py build /data/bloom_opt.h160db /data/k3_bloom.bloom /data/k3_bloom.seeds")
        print("  python3 build_k3_bloom.py test /data/k3_bloom.bloom /data/k3_bloom.seeds abeddf6b115157b704de34c50d22beefbeb59c98")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "build":
        if len(sys.argv) < 5:
            print("Usage: python3 build_k3_bloom.py build <h160db> <output_bloom> <output_seeds> [bits] [hashes]")
            sys.exit(1)
        h160db = sys.argv[2]
        out_bloom = sys.argv[3]
        out_seeds = sys.argv[4]
        bits = int(sys.argv[5]) if len(sys.argv) > 5 else None
        hashes = int(sys.argv[6]) if len(sys.argv) > 6 else 12
        build_k3_bloom(h160db, out_bloom, out_seeds, bits, hashes)

    elif cmd == "test":
        if len(sys.argv) < 5:
            print("Usage: python3 build_k3_bloom.py test <bloom> <seeds> <hash160_hex>")
            sys.exit(1)
        bloom = sys.argv[2]
        seeds = sys.argv[3]
        target = sys.argv[4]
        test_target_in_bloom(bloom, seeds, target)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
