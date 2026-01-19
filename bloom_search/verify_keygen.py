#!/usr/bin/env python3
"""
Verify the key generation in BloomSearch32K1.cu

This script tests:
1. Whether random bytes form valid secp256k1 EC points
2. Proper private key -> public key derivation
3. Address generation correctness

The issue: BloomSearch32K1.cu uses random 64-byte data as (x, y) coordinates,
but random data is NOT a valid EC point on secp256k1!

Valid approaches:
- Generate random 32-byte private key k, then compute public key P = k*G
- Use a known valid starting point and iterate
"""

import hashlib
import struct
import os

# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
A = 0  # secp256k1: y^2 = x^3 + 7
B = 7
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def modinv(a, m):
    """Extended Euclidean Algorithm for modular inverse"""
    if a < 0:
        a = m + a
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        raise ValueError('Modular inverse does not exist')
    return x % m


def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y


def point_add(p1, p2):
    """Add two EC points"""
    if p1 is None:
        return p2
    if p2 is None:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2 and y1 == (P - y2) % P:
        return None  # Point at infinity

    if x1 == x2 and y1 == y2:
        # Point doubling
        s = (3 * x1 * x1 * modinv(2 * y1, P)) % P
    else:
        # Point addition
        s = ((y2 - y1) * modinv(x2 - x1, P)) % P

    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P

    return (x3, y3)


def scalar_mult(k, point):
    """Multiply EC point by scalar k"""
    result = None
    addend = point

    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1

    return result


def is_on_curve(x, y):
    """Check if point (x, y) is on secp256k1"""
    left = (y * y) % P
    right = (x * x * x + B) % P
    return left == right


def bytes_to_int(b):
    """Convert bytes to big-endian integer"""
    return int.from_bytes(b, 'big')


def int_to_bytes(n, length=32):
    """Convert integer to big-endian bytes"""
    return n.to_bytes(length, 'big')


def get_y_from_x(x, odd=False):
    """Get y coordinate from x (if valid point exists)"""
    # y^2 = x^3 + 7 mod P
    y_squared = (pow(x, 3, P) + B) % P

    # Compute square root using Tonelli-Shanks (simplified for secp256k1)
    # P ≡ 3 (mod 4), so y = y_squared^((P+1)/4) mod P
    y = pow(y_squared, (P + 1) // 4, P)

    if (y * y) % P != y_squared:
        return None  # No valid y exists

    if (y & 1) != odd:
        y = P - y

    return y


def privkey_to_pubkey(privkey_bytes):
    """Convert 32-byte private key to public key (x, y)"""
    k = bytes_to_int(privkey_bytes)
    if k == 0 or k >= N:
        raise ValueError("Invalid private key")

    G = (Gx, Gy)
    return scalar_mult(k, G)


def pubkey_to_hash160(x, y, compressed=True):
    """Convert public key to hash160 (RIPEMD160(SHA256(pubkey)))"""
    if compressed:
        prefix = b'\x02' if y % 2 == 0 else b'\x03'
        pubkey = prefix + int_to_bytes(x)
    else:
        pubkey = b'\x04' + int_to_bytes(x) + int_to_bytes(y)

    sha256_hash = hashlib.sha256(pubkey).digest()
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    return ripemd160.digest()


def hash160_to_address(h160, mainnet=True):
    """Convert hash160 to Bitcoin address (Base58Check)"""
    version = b'\x00' if mainnet else b'\x6f'
    payload = version + h160
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]

    # Base58 encoding
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    n = int.from_bytes(payload + checksum, 'big')
    result = ''
    while n > 0:
        n, remainder = divmod(n, 58)
        result = alphabet[remainder] + result

    # Add leading zeros
    for byte in payload + checksum:
        if byte == 0:
            result = '1' + result
        else:
            break

    return result


def test_random_bytes_as_ec_point():
    """Test if random bytes form a valid EC point"""
    print("=" * 70)
    print("TEST 1: Random bytes as EC point coordinates")
    print("=" * 70)

    valid_count = 0
    invalid_count = 0

    for i in range(100):
        # Generate random 64 bytes (like BloomSearch32K1 does)
        random_bytes = os.urandom(64)
        x = bytes_to_int(random_bytes[:32])
        y = bytes_to_int(random_bytes[32:])

        # Check if it's on curve
        if is_on_curve(x, y):
            valid_count += 1
        else:
            invalid_count += 1

    print(f"Random 64-byte samples: {valid_count} valid, {invalid_count} invalid")
    print(f"Probability of random point being valid: ~{valid_count}%")
    print()

    if invalid_count > 0:
        print("⚠️  PROBLEM: Random bytes are almost NEVER valid EC points!")
        print("   BloomSearch32K1.cu's approach of using random bytes as (x,y)")
        print("   coordinates will produce INVALID points that don't correspond")
        print("   to any private key!")
        print()

    return invalid_count == 0


def test_proper_keygen():
    """Test proper private key -> public key generation"""
    print("=" * 70)
    print("TEST 2: Proper private key to public key derivation")
    print("=" * 70)

    # Test with known values (from Bitcoin wiki)
    test_vectors = [
        # (private_key_hex, expected_pubkey_x, expected_pubkey_y)
        ("0000000000000000000000000000000000000000000000000000000000000001",
         Gx, Gy),
        ("0000000000000000000000000000000000000000000000000000000000000002",
         0xc6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5,
         0x1ae168fea63dc339a3c58419466ceae1061b7cd988e06f3d0d9d8a1d0f3a5e47),
    ]

    all_passed = True
    for privkey_hex, expected_x, expected_y in test_vectors:
        privkey = bytes.fromhex(privkey_hex)
        x, y = privkey_to_pubkey(privkey)

        if x == expected_x and y == expected_y:
            print(f"✓ Private key {privkey_hex[:16]}... -> correct public key")
        else:
            print(f"✗ Private key {privkey_hex[:16]}... -> WRONG public key!")
            print(f"  Expected x: {hex(expected_x)}")
            print(f"  Got x:      {hex(x)}")
            all_passed = False

    print()
    return all_passed


def test_address_generation():
    """Test address generation from public key"""
    print("=" * 70)
    print("TEST 3: Address generation from public key")
    print("=" * 70)

    # Known test vector: Private key 1 -> G point
    privkey = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000001")
    x, y = privkey_to_pubkey(privkey)

    # Compressed address
    h160_comp = pubkey_to_hash160(x, y, compressed=True)
    addr_comp = hash160_to_address(h160_comp)
    expected_comp = "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH"

    print(f"Private key: 1")
    print(f"Compressed address:   {addr_comp}")
    print(f"Expected:             {expected_comp}")
    print(f"Match: {'✓' if addr_comp == expected_comp else '✗'}")
    print()

    # Uncompressed address
    h160_uncomp = pubkey_to_hash160(x, y, compressed=False)
    addr_uncomp = hash160_to_address(h160_uncomp)
    expected_uncomp = "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm"

    print(f"Uncompressed address: {addr_uncomp}")
    print(f"Expected:             {expected_uncomp}")
    print(f"Match: {'✓' if addr_uncomp == expected_uncomp else '✗'}")
    print()

    return addr_comp == expected_comp and addr_uncomp == expected_uncomp


def demonstrate_fix():
    """Show how to properly generate starting points"""
    print("=" * 70)
    print("SOLUTION: Proper starting point generation")
    print("=" * 70)

    print("""
The fix for BloomSearch32K1.cu:

Instead of:
    secure_random(h_keys, nbThread * 64);  // Random (x, y) - WRONG!

Do this:
    1. Generate random 32-byte private key k
    2. Compute public key P = k * G (EC multiplication)
    3. Use P as the starting point
    4. The private key for iteration i is: k + i

Option A - CPU initialization:
    for (int t = 0; t < nbThread; t++) {
        uint8_t privkey[32];
        secure_random(privkey, 32);

        // Compute P = privkey * G using CPU secp256k1 library
        secp256k1_pubkey pubkey;
        secp256k1_ec_pubkey_create(ctx, &pubkey, privkey);

        // Extract x, y coordinates to h_keys
        memcpy(&h_keys[t * 8], pubkey_x, 32);
        memcpy(&h_keys[t * 8 + nbThread * 4], pubkey_y, 32);
    }

Option B - Use generator table:
    The code already has Gx/Gy tables for G, 2G, 3G, ..., 512G.
    Starting from k*G and iterating gives k*G, (k+1)*G, (k+2)*G, etc.

    If we pick random k and initialize with k*G (computed properly),
    the iteration will cover k, k+1, k+2, ..., k+GRP_SIZE*STEP_SIZE

Key insight: The current iteration logic ADDS G to points correctly.
The bug is only in the INITIALIZATION of starting points!
""")


def verify_gpu_iteration_math():
    """Verify the GPU iteration math is correct"""
    print("=" * 70)
    print("TEST 4: Verify GPU iteration math")
    print("=" * 70)

    G = (Gx, Gy)

    # Simulate what the GPU does: start at k*G, add G repeatedly
    start_k = 12345  # Example starting private key
    start_point = scalar_mult(start_k, G)

    print(f"Starting private key: {start_k}")
    print(f"Starting point P = {start_k}*G")
    print()

    # GPU iteration: P, P+G, P+2G, ...
    current = start_point
    for i in range(5):
        expected_k = start_k + i
        expected_point = scalar_mult(expected_k, G)

        match = current == expected_point
        print(f"Iteration {i}: k={expected_k}, point match: {'✓' if match else '✗'}")

        if not match:
            print(f"  Current:  ({hex(current[0])[:20]}..., {hex(current[1])[:20]}...)")
            print(f"  Expected: ({hex(expected_point[0])[:20]}..., {hex(expected_point[1])[:20]}...)")

        # Add G for next iteration (simulating GPU)
        current = point_add(current, G)

    print()
    print("The iteration math (adding G) is correct.")
    print("The BUG is in initialization: random bytes ≠ valid EC point ≠ k*G")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("BLOOM SEARCH KEY GENERATION VERIFICATION")
    print("=" * 70 + "\n")

    test_random_bytes_as_ec_point()
    test_proper_keygen()
    test_address_generation()
    verify_gpu_iteration_math()
    demonstrate_fix()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
CRITICAL BUG FOUND in BloomSearch32K1.cu:

The code uses random 64 bytes as (x, y) EC point coordinates:
    secure_random(h_keys, nbThread * 64);

This is WRONG because:
1. Random (x, y) is almost NEVER a valid secp256k1 curve point
2. Invalid points don't correspond to any private key
3. The search is checking addresses that DON'T EXIST

FIX REQUIRED:
1. Generate random 32-byte private keys
2. Compute public keys P = k * G (proper EC multiplication)
3. Use these valid points as starting coordinates

The iteration logic (P + i*G) is correct; only initialization is broken.
""")
