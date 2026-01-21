#!/usr/bin/env python3
"""
Debug script to verify K3's hash computation matches Python.
Target: private key 74120947517767895891355266452452269842804955139343486161984562552406380210176
        hash160 (uncompressed): abeddf6b115157b704de34c50d22beefbeb59c98
"""

import hashlib
import struct

# Target values from previous debugging session
TARGET_DECIMAL = "74120947517767895891355266452452269842804955139343486161984562552406380210176"
TARGET_START = "74120947517767895891355266452452269842804955139343486161984562552406380000000"
TARGET_OFFSET = 210176  # Should be found at thread=256, iteration=205

# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

def mod_inverse(a, p):
    """Compute modular inverse using extended Euclidean algorithm"""
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
    """Add two points on secp256k1"""
    if x1 is None:
        return x2, y2
    if x2 is None:
        return x1, y1
    if x1 == x2 and y1 == y2:
        # Point doubling
        s = (3 * x1 * x1 * mod_inverse(2 * y1, P)) % P
    elif x1 == x2:
        return None, None  # Point at infinity
    else:
        s = ((y2 - y1) * mod_inverse(x2 - x1, P)) % P

    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P
    return x3, y3

def scalar_mult(k, x=GX, y=GY):
    """Multiply point by scalar k"""
    rx, ry = None, None
    qx, qy = x, y

    while k > 0:
        if k & 1:
            rx, ry = point_add(rx, ry, qx, qy)
        qx, qy = point_add(qx, qy, qx, qy)
        k >>= 1

    return rx, ry

def compute_hash160(pubkey_bytes):
    """Compute RIPEMD160(SHA256(pubkey))"""
    sha256_hash = hashlib.sha256(pubkey_bytes).digest()
    ripemd160 = hashlib.new('ripemd160', sha256_hash).digest()
    return ripemd160

def privkey_to_pubkey_uncompressed(k):
    """Convert private key to uncompressed public key (65 bytes)"""
    x, y = scalar_mult(k)
    return b'\x04' + x.to_bytes(32, 'big') + y.to_bytes(32, 'big')

def privkey_to_pubkey_compressed(k):
    """Convert private key to compressed public key (33 bytes)"""
    x, y = scalar_mult(k)
    prefix = b'\x02' if y % 2 == 0 else b'\x03'
    return prefix + x.to_bytes(32, 'big')

def decimal_to_256bit(decimal_str):
    """Convert decimal string to 256-bit integer (matching K3's implementation)"""
    # Remove commas
    clean = ''.join(c for c in decimal_str if c.isdigit())
    return int(clean)

def to_256bit_array(val):
    """Convert int to 4 x uint64 array (little-endian, like K3)"""
    result = []
    for i in range(4):
        result.append(val & 0xFFFFFFFFFFFFFFFF)
        val >>= 64
    return result

def murmur3_32(key, seed):
    """MurmurHash3 32-bit implementation matching K3"""
    c1 = 0xcc9e2d51
    c2 = 0x1b873593
    h1 = seed & 0xFFFFFFFF

    # Process 4-byte blocks
    nblocks = len(key) // 4
    for i in range(nblocks):
        k1 = struct.unpack('<I', key[i*4:(i+1)*4])[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF
        h1 = ((h1 * 5) + 0xe6546b64) & 0xFFFFFFFF

    # Process remaining bytes
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

    # Finalization
    h1 ^= len(key)
    h1 ^= (h1 >> 16)
    h1 = (h1 * 0x85ebca6b) & 0xFFFFFFFF
    h1 ^= (h1 >> 13)
    h1 = (h1 * 0xc2b2ae35) & 0xFFFFFFFF
    h1 ^= (h1 >> 16)

    return h1

def check_bloom_with_mask(hash160_bytes, bits_mask, seeds):
    """Check if hash160 passes bloom filter using AND mask"""
    for seed in seeds:
        h = murmur3_32(hash160_bytes, seed)
        bit_pos = h & bits_mask
        print(f"  Seed {seed}: h={h:08x}, bitPos={bit_pos}")
    return True

def main():
    print("="*70)
    print("K3 Hash Computation Debug")
    print("="*70)

    # Parse target values
    target_k = decimal_to_256bit(TARGET_DECIMAL)
    start_k = decimal_to_256bit(TARGET_START)

    print(f"\nTarget private key (decimal): {TARGET_DECIMAL}")
    print(f"Target private key (hex): {target_k:064x}")
    print(f"\nStart point (decimal): {TARGET_START}")
    print(f"Start point (hex): {start_k:064x}")
    print(f"\nOffset from start: {target_k - start_k}")
    print(f"Expected: thread=256, iteration=205")
    print(f"Verify: 256 + 205 * 1024 = {256 + 205 * 1024}")

    # Compute public keys
    print("\n" + "="*70)
    print("Computing public key for target...")
    print("="*70)

    x, y = scalar_mult(target_k)
    print(f"\nPublic key X: {x:064x}")
    print(f"Public key Y: {y:064x}")
    print(f"Y is {'even' if y % 2 == 0 else 'odd'}")

    # Uncompressed pubkey
    uncompressed = privkey_to_pubkey_uncompressed(target_k)
    print(f"\nUncompressed pubkey (65 bytes):")
    print(f"  {uncompressed.hex()}")

    # Compressed pubkey
    compressed = privkey_to_pubkey_compressed(target_k)
    print(f"\nCompressed pubkey (33 bytes):")
    print(f"  {compressed.hex()}")

    # Compute hash160s
    print("\n" + "="*70)
    print("Computing hash160...")
    print("="*70)

    h160_uncomp = compute_hash160(uncompressed)
    h160_comp = compute_hash160(compressed)

    print(f"\nHash160 (uncompressed): {h160_uncomp.hex()}")
    print(f"Hash160 (compressed):   {h160_comp.hex()}")

    # Show as uint32 array (how K3 stores it)
    print("\nHash160 (uncompressed) as uint32 array (little-endian, like K3):")
    h160_as_u32 = []
    for i in range(5):
        val = struct.unpack('<I', h160_uncomp[i*4:(i+1)*4])[0]
        h160_as_u32.append(val)
        print(f"  h[{i}] = 0x{val:08x}")

    # K3 prefix check: __byte_perm(h[0], 0, 0x0123) reverses bytes of h[0]
    prefix32_k3 = ((h160_as_u32[0] >> 24) & 0xFF) | \
                  ((h160_as_u32[0] >> 8) & 0xFF00) | \
                  ((h160_as_u32[0] << 8) & 0xFF0000) | \
                  ((h160_as_u32[0] << 24) & 0xFF000000)
    print(f"\nK3 prefix32 (__byte_perm reverses bytes): 0x{prefix32_k3:08x}")
    print(f"  Byte index for prefix table: {prefix32_k3 >> 3}")
    print(f"  Bit index: {prefix32_k3 & 7}")

    # The bloom filter uses (const uint8_t*)h directly
    # Since h is stored as little-endian uint32s, the byte representation is:
    h160_from_u32 = b''.join(struct.pack('<I', v) for v in h160_as_u32)
    print(f"\nHash160 bytes when cast from uint32[] to uint8_t*:")
    print(f"  Hex: {h160_from_u32.hex()}")
    print(f"  Matches original: {h160_from_u32 == h160_uncomp}")

    # Expected hash160 from previous session
    expected_h160 = "abeddf6b115157b704de34c50d22beefbeb59c98"
    print(f"\nExpected hash160 (uncompressed): {expected_h160}")
    print(f"Match: {h160_uncomp.hex() == expected_h160}")

    # Test MurmurHash3
    print("\n" + "="*70)
    print("Testing MurmurHash3...")
    print("="*70)

    # Use some test seeds
    test_seeds = [0x12345678, 0x87654321, 0xDEADBEEF]
    print(f"\nMurmurHash3 of hash160 (uncompressed) with test seeds:")
    for seed in test_seeds:
        h = murmur3_32(h160_uncomp, seed)
        print(f"  Seed 0x{seed:08x}: 0x{h:08x}")

    # Verify byte order - K3 reads hash160 as uint32 array
    print("\n" + "="*70)
    print("Byte order analysis...")
    print("="*70)

    print("\nHash160 bytes:")
    print(f"  Hex: {h160_uncomp.hex()}")
    print(f"  Bytes: {list(h160_uncomp)}")

    # K3 uses (const uint8_t*)h where h is uint32* array
    # The _GetHash160 function should output the hash in the right format

    # Check K3's expected thread/iteration
    print("\n" + "="*70)
    print("K3 Thread/Iteration Analysis")
    print("="*70)

    nbThread = 65536  # K3_TOTAL_THREADS = 256 * 256
    step_size = 1024   # K3_STEP_SIZE (= GRP_SIZE in GPUGroup.h)
    grp_size = 1024    # GRP_SIZE from GPUGroup.h

    offset = target_k - start_k
    print(f"\nOffset from start: {offset}")

    # Key insight: init_keys_from_decimal_start gives thread t key = start + t
    # So thread 0 starts at key 'start', thread 1 at 'start+1', etc.
    # After each kernel call, each thread advances by STEP_SIZE keys

    # Thread t at iteration i has private key: start + t + i * STEP_SIZE
    # We want: start + offset
    # So: t + i * STEP_SIZE = offset
    # Or: offset = t + i * 1024

    # This means we need to find t and i such that:
    #   t + i * step_size = offset
    #   where 0 <= t < nbThread

    # Since threads are independent, we can have ANY thread find it
    # Thread t will find it at iteration i = (offset - t) / step_size
    # IF (offset - t) % step_size == 0

    # Let's find which thread hits it first (lowest iteration)
    remainder = offset % step_size
    thread_id = remainder  # This thread hits the target
    iteration = offset // step_size

    # But wait, thread_id must be < nbThread = 65536
    # And step_size = 1024, so thread_id = offset % 1024 is always < 1024 < 65536 ✓

    print(f"\nK3 Configuration:")
    print(f"  Total threads: {nbThread} (256 blocks x 256 threads/block)")
    print(f"  Step size: {step_size}")
    print(f"  Group size: {grp_size}")

    print(f"\nTarget key analysis:")
    print(f"  offset mod step_size = {remainder}")
    print(f"  Thread that hits target: {thread_id}")
    print(f"  Iteration when found: {iteration}")

    print(f"\n  Verification: {thread_id} + {iteration} * {step_size} = {thread_id + iteration * step_size}")
    print(f"  Expected: {offset}")
    print(f"  Match: {thread_id + iteration * step_size == offset}")

    # But K3's kernel processes GROUP points per iteration per thread
    # Looking at ComputeKeysK3, it loops: for j in range(STEP_SIZE / GRP_SIZE)
    # Inside the loop it checks GRP_SIZE points via the group operation

    # So actually the iteration counting works like this:
    # Each kernel call processes STEP_SIZE keys per thread
    # STEP_SIZE = 1024, GRP_SIZE = 1024
    # So j loops once (1024/1024 = 1)

    # The CheckHashBothFormats_K3 is called for:
    #   j*GRP_SIZE + GRP_SIZE/2 (center point)
    #   j*GRP_SIZE + GRP_SIZE/2 + (i+1) for i in 0..HSIZE-1
    #   j*GRP_SIZE + GRP_SIZE/2 - (i+1) for i in 0..HSIZE-1
    #   j*GRP_SIZE (first point)

    # Where HSIZE = GRP_SIZE/2 = 512

    # Actually looking more carefully at the loop structure:
    # Thread starts at point P = G * (start + threadIdx)
    # Each iteration it advances by GRP_SIZE
    # The inner loop processes offsets from -HSIZE to +HSIZE around center

    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print(f"\nTarget will be found by:")
    print(f"  Thread: {thread_id}")
    print(f"  Kernel iteration: {iteration}")
    print(f"\nComputed hash160 (uncompressed): {h160_uncomp.hex()}")
    print(f"Expected hash160: {expected_h160}")

if __name__ == "__main__":
    main()
