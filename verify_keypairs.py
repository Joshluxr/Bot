#!/usr/bin/env python3
"""
Verify that Bitcoin public addresses match their private keys.
This script validates keypairs from candidate data files.
"""

import hashlib
import sys
import os
from typing import Tuple, Optional

def hash160(data: bytes) -> bytes:
    """Compute HASH160 (RIPEMD160(SHA256(data)))"""
    sha256_hash = hashlib.sha256(data).digest()
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(sha256_hash)
    return ripemd160.digest()

def base58_encode(data: bytes) -> str:
    """Encode data in base58 format"""
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

    # Convert bytes to integer
    num = int.from_bytes(data, byteorder='big')

    # Convert to base58
    encoded = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded = alphabet[remainder] + encoded

    # Add '1' for each leading zero byte
    for byte in data:
        if byte == 0:
            encoded = '1' + encoded
        else:
            break

    return encoded

def hash160_to_address(hash160_hex: str) -> str:
    """Convert hash160 to Bitcoin address"""
    try:
        # Add version byte (0x00 for mainnet)
        versioned = bytes.fromhex('00' + hash160_hex)

        # Double SHA256 for checksum
        checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]

        # Combine and encode
        address_bytes = versioned + checksum
        return base58_encode(address_bytes)
    except Exception as e:
        return f"ERROR: {str(e)}"

def privkey_to_pubkey(privkey_hex: str) -> Optional[bytes]:
    """
    Convert private key to uncompressed public key using secp256k1.
    Returns None if conversion fails.
    """
    try:
        # Try using coincurve (faster, libsecp256k1 wrapper)
        try:
            from coincurve import PrivateKey
            privkey_bytes = bytes.fromhex(privkey_hex.zfill(64))
            key = PrivateKey(privkey_bytes)
            return key.public_key.format(compressed=False)
        except ImportError:
            pass

        # Fallback to ecdsa library
        try:
            from ecdsa import SigningKey, SECP256k1
            privkey_bytes = bytes.fromhex(privkey_hex.zfill(64))
            sk = SigningKey.from_string(privkey_bytes, curve=SECP256k1)
            vk = sk.get_verifying_key()
            # Return uncompressed format (0x04 + x + y)
            return b'\x04' + vk.to_string()
        except ImportError:
            pass

        print("ERROR: No secp256k1 library available. Install coincurve or ecdsa:")
        print("  pip install coincurve")
        print("  or")
        print("  pip install ecdsa")
        return None

    except Exception as e:
        print(f"ERROR converting private key: {e}")
        return None

def verify_keypair(privkey_hex: str, expected_address: str, expected_hash160: str = None) -> Tuple[bool, str]:
    """
    Verify that a private key generates the expected Bitcoin address.

    Returns:
        (is_valid, message)
    """
    try:
        # Convert private key to public key
        pubkey = privkey_to_pubkey(privkey_hex)
        if pubkey is None:
            return False, "Failed to generate public key (library missing)"

        # Compute hash160 from public key
        computed_hash160 = hash160(pubkey).hex()

        # Convert to address
        computed_address = hash160_to_address(computed_hash160)

        # Compare addresses
        if computed_address == expected_address:
            return True, f"✓ VALID - Address matches"
        else:
            msg = f"✗ MISMATCH\n"
            msg += f"  Expected: {expected_address}\n"
            msg += f"  Computed: {computed_address}\n"
            if expected_hash160:
                msg += f"  Expected hash160: {expected_hash160}\n"
            msg += f"  Computed hash160: {computed_hash160}"
            return False, msg

    except Exception as e:
        return False, f"ERROR: {str(e)}"

def verify_from_csv(csv_file: str, max_lines: int = None, sample_every: int = None):
    """
    Verify keypairs from a CSV file.

    Args:
        csv_file: Path to CSV file (format: address,privkey,hash160 or similar)
        max_lines: Maximum number of lines to check (None = all)
        sample_every: Check every Nth line (None = check all)
    """
    if not os.path.exists(csv_file):
        print(f"ERROR: File not found: {csv_file}")
        return

    print(f"\nVerifying keypairs from: {csv_file}")
    print("=" * 80)

    total = 0
    valid = 0
    invalid = 0
    errors = 0

    with open(csv_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Skip header
            if line_num == 1 and ('address' in line.lower() or 'privkey' in line.lower()):
                continue

            # Sampling logic
            if sample_every and line_num % sample_every != 0:
                continue

            # Max lines limit
            if max_lines and total >= max_lines:
                break

            line = line.strip()
            if not line:
                continue

            total += 1
            parts = line.split(',')

            if len(parts) < 2:
                print(f"Line {line_num}: Invalid format (need at least address,privkey)")
                errors += 1
                continue

            address = parts[0].strip()
            privkey = parts[1].strip()
            hash160_expected = parts[2].strip() if len(parts) > 2 else None

            # Verify
            is_valid, msg = verify_keypair(privkey, address, hash160_expected)

            if is_valid:
                valid += 1
                if total <= 10 or total % 100 == 0:
                    print(f"Line {line_num}: {msg}")
            else:
                invalid += 1
                print(f"\nLine {line_num}: {msg}")
                print(f"  Address: {address}")
                print(f"  PrivKey: {privkey}\n")

    print("\n" + "=" * 80)
    print(f"RESULTS:")
    print(f"  Total checked: {total}")
    print(f"  Valid: {valid} ({100*valid/total if total > 0 else 0:.1f}%)")
    print(f"  Invalid: {invalid}")
    print(f"  Errors: {errors}")

    return valid, invalid, errors

def verify_single_keypair(privkey: str, address: str):
    """Verify a single keypair"""
    print(f"\nVerifying single keypair:")
    print(f"  Private Key: {privkey}")
    print(f"  Expected Address: {address}")
    print("-" * 80)

    is_valid, msg = verify_keypair(privkey, address)
    print(msg)

    return is_valid

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Verify CSV file:")
        print(f"    {sys.argv[0]} <csv_file> [max_lines] [sample_every]")
        print()
        print("  Verify single keypair:")
        print(f"    {sys.argv[0]} <privkey_hex> <address>")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} candidates.csv")
        print(f"  {sys.argv[0]} candidates.csv 100")
        print(f"  {sys.argv[0]} candidates.csv 1000 10  # Check 1000 lines, sample every 10th")
        print(f"  {sys.argv[0]} 1234567890abcdef... 1FeexV6bAH...")
        sys.exit(1)

    if len(sys.argv) == 3 and not sys.argv[1].endswith('.csv'):
        # Single keypair verification
        privkey = sys.argv[1]
        address = sys.argv[2]
        verify_single_keypair(privkey, address)
    else:
        # CSV file verification
        csv_file = sys.argv[1]
        max_lines = int(sys.argv[2]) if len(sys.argv) > 2 else None
        sample_every = int(sys.argv[3]) if len(sys.argv) > 3 else None
        verify_from_csv(csv_file, max_lines, sample_every)

if __name__ == '__main__':
    main()
