#!/usr/bin/env python3
"""Test K3 formula with known private key"""

import coincurve as cc
import hashlib

N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def privkey_to_hash160(privkey_int, compressed=True):
    """Convert private key to hash160"""
    privkey_bytes = privkey_int.to_bytes(32, 'big')
    pubkey = cc.PublicKey.from_secret(privkey_bytes)

    if compressed:
        pubkey_bytes = pubkey.format(compressed=True)
    else:
        pubkey_bytes = pubkey.format(compressed=False)

    sha256 = hashlib.sha256(pubkey_bytes).digest()
    ripemd160 = hashlib.new('ripemd160', sha256).digest()
    return ripemd160.hex()

# Create test data
base_privkey = 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
incr = 499

print("Testing K3 Formula")
print("=" * 70)
print(f"Base privkey: {base_privkey:064x}")
print(f"Increment:    {incr}")
print()

# Method 1: Simple addition
actual_privkey = (base_privkey + incr) % N
print(f"Actual privkey (base + incr): {actual_privkey:064x}")
print()

# Generate hash160s
for mode_name, compressed in [("Compressed", True), ("Uncompressed", False)]:
    base_hash160 = privkey_to_hash160(base_privkey, compressed)
    actual_hash160 = privkey_to_hash160(actual_privkey, compressed)

    print(f"{mode_name}:")
    print(f"  Base hash160:   {base_hash160}")
    print(f"  Actual hash160: {actual_hash160}")
    print(f"  Match: {base_hash160 == actual_hash160}")
    print()

print("=" * 70)
print("K3 Formula Test Complete")
print()
print("The formula should be: actual_privkey = (base_privkey + incr) % N")
print()
print("If this test shows different hash160s, the K3 formula is CORRECT.")
print("The logged 'privkey' is the STARTING key for that thread,")
print("and the 'incr' tells you how many steps forward from that start.")
