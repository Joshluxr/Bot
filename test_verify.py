#!/usr/bin/env python3
"""
Test the keypair verification with known valid Bitcoin keypairs.
"""

import sys
sys.path.insert(0, '/root/repo')

from verify_keypairs import verify_keypair, hash160_to_address, privkey_to_pubkey, hash160

def test_known_keypair():
    """Test with a known valid Bitcoin keypair"""
    print("Testing with known Bitcoin keypair...")
    print("=" * 80)

    # Test case 1: Well-known keypair
    # Private key: 1
    privkey1 = "0000000000000000000000000000000000000000000000000000000000000001"
    # Expected address for privkey=1 (uncompressed): 1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm
    expected_addr1 = "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm"

    print(f"\nTest 1: Private Key = 1")
    print(f"  Private Key: {privkey1}")
    print(f"  Expected Address: {expected_addr1}")

    is_valid, msg = verify_keypair(privkey1, expected_addr1)
    print(f"  Result: {msg}\n")

    # Test case 2: Another known keypair
    # Private key: 2
    privkey2 = "0000000000000000000000000000000000000000000000000000000000000002"
    expected_addr2 = "1LagHJk2FyCV2VzrNHVqg3gYG4TSYwDV4m"

    print(f"Test 2: Private Key = 2")
    print(f"  Private Key: {privkey2}")
    print(f"  Expected Address: {expected_addr2}")

    is_valid, msg = verify_keypair(privkey2, expected_addr2)
    print(f"  Result: {msg}\n")

    # Test case 3: Test incorrect address (should fail)
    print(f"Test 3: Intentionally wrong address (should fail)")
    print(f"  Private Key: {privkey1}")
    print(f"  Wrong Address: {expected_addr2}")

    is_valid, msg = verify_keypair(privkey1, expected_addr2)
    print(f"  Result: {msg}\n")

    print("=" * 80)

def test_manual_conversion():
    """Manually test the conversion process"""
    print("\n\nManual Conversion Test")
    print("=" * 80)

    privkey = "0000000000000000000000000000000000000000000000000000000000000001"
    print(f"Private Key: {privkey}")

    # Get public key
    pubkey = privkey_to_pubkey(privkey)
    if pubkey:
        print(f"Public Key (uncompressed): {pubkey.hex()}")

        # Get hash160
        h160 = hash160(pubkey)
        print(f"Hash160: {h160.hex()}")

        # Get address
        address = hash160_to_address(h160.hex())
        print(f"Bitcoin Address: {address}")
    else:
        print("ERROR: Could not generate public key")

    print("=" * 80)

if __name__ == '__main__':
    test_known_keypair()
    test_manual_conversion()
