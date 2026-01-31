#!/usr/bin/env python3
"""
Derive Bitcoin addresses directly from the private keys in candidate files.
This shows what addresses the logged private keys ACTUALLY generate.
"""

import sys
import hashlib
from coincurve import PrivateKey

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
    # Add version byte (0x00 for mainnet)
    versioned = bytes.fromhex('00' + hash160_hex)

    # Double SHA256 for checksum
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]

    # Combine and encode
    address_bytes = versioned + checksum
    return base58_encode(address_bytes)

def privkey_to_address(privkey_hex: str) -> tuple:
    """
    Derive Bitcoin address from private key.

    Returns:
        (address, hash160, pubkey_hex)
    """
    try:
        # Convert private key to public key
        privkey_bytes = bytes.fromhex(privkey_hex.zfill(64))
        key = PrivateKey(privkey_bytes)

        # Get uncompressed public key
        pubkey = key.public_key.format(compressed=False)

        # Compute hash160
        h160 = hash160(pubkey)
        h160_hex = h160.hex()

        # Convert to address
        address = hash160_to_address(h160_hex)

        return address, h160_hex, pubkey.hex()
    except Exception as e:
        return None, None, str(e)

def process_csv_file(csv_file: str, output_file: str = None, max_lines: int = None):
    """
    Process candidate CSV file and derive addresses from private keys.

    Creates a new CSV with:
    - Original address (from file)
    - Original privkey (from file)
    - Original hash160 (from file)
    - Derived address (computed from privkey)
    - Derived hash160 (computed from privkey)
    - Match status
    """
    if output_file is None:
        output_file = csv_file.replace('.csv', '_DERIVED.csv')

    print(f"Processing: {csv_file}")
    print(f"Output: {output_file}")
    print()

    processed = 0
    matched = 0
    mismatched = 0
    errors = 0

    with open(csv_file, 'r') as infile, open(output_file, 'w') as outfile:
        # Write header
        outfile.write("OriginalAddress,OriginalPrivKey,OriginalHash160,DerivedAddress,DerivedHash160,Match\n")

        for line_num, line in enumerate(infile, 1):
            # Skip header
            if line_num == 1 and ('address' in line.lower() or 'Address' in line):
                continue

            # Max lines limit
            if max_lines and processed >= max_lines:
                break

            line = line.strip()
            if not line:
                continue

            parts = line.split(',')
            if len(parts) < 3:
                continue

            orig_address = parts[0].strip()
            orig_privkey = parts[1].strip()
            orig_hash160 = parts[2].strip()

            # Derive address from private key
            derived_addr, derived_h160, error = privkey_to_address(orig_privkey)

            if derived_addr is None:
                # Error
                outfile.write(f"{orig_address},{orig_privkey},{orig_hash160},ERROR,ERROR,ERROR\n")
                errors += 1
                print(f"Line {line_num}: ERROR - {error}")
            else:
                # Check if it matches
                match = "YES" if derived_addr == orig_address else "NO"
                outfile.write(f"{orig_address},{orig_privkey},{orig_hash160},{derived_addr},{derived_h160},{match}\n")

                if match == "YES":
                    matched += 1
                    if processed < 5:
                        print(f"Line {line_num}: ✓ MATCH - {orig_address}")
                else:
                    mismatched += 1
                    if processed < 5:
                        print(f"Line {line_num}: ✗ MISMATCH")
                        print(f"  Original:  {orig_address}")
                        print(f"  Derived:   {derived_addr}")

            processed += 1

            # Progress indicator
            if processed % 10000 == 0:
                print(f"Processed {processed:,} entries... (Matched: {matched}, Mismatched: {mismatched})")

    print()
    print("=" * 80)
    print("RESULTS:")
    print(f"  Total processed: {processed:,}")
    print(f"  Matched: {matched:,} ({100*matched/processed if processed > 0 else 0:.2f}%)")
    print(f"  Mismatched: {mismatched:,} ({100*mismatched/processed if processed > 0 else 0:.2f}%)")
    print(f"  Errors: {errors:,}")
    print(f"  Output saved to: {output_file}")
    print("=" * 80)

def quick_test(csv_file: str, num_lines: int = 10):
    """Quick test of first few lines"""
    print(f"Quick test - first {num_lines} lines from {csv_file}")
    print("=" * 80)

    with open(csv_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Skip header
            if line_num == 1 and ('address' in line.lower() or 'Address' in line):
                continue

            if line_num > num_lines + 1:
                break

            parts = line.strip().split(',')
            if len(parts) < 3:
                continue

            orig_address = parts[0].strip()
            orig_privkey = parts[1].strip()
            orig_hash160 = parts[2].strip()

            derived_addr, derived_h160, _ = privkey_to_address(orig_privkey)

            print(f"\nEntry {line_num - 1}:")
            print(f"  Original Address:  {orig_address}")
            print(f"  Private Key:       {orig_privkey[:32]}...{orig_privkey[-8:]}")
            print(f"  Original Hash160:  {orig_hash160}")
            print(f"  ───────────────────────────────────────────")
            print(f"  Derived Address:   {derived_addr}")
            print(f"  Derived Hash160:   {derived_h160}")
            print(f"  Match: {'✓ YES' if derived_addr == orig_address else '✗ NO'}")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print()
        print("  Quick test (first 10 lines):")
        print(f"    {sys.argv[0]} <csv_file> test")
        print()
        print("  Process entire file:")
        print(f"    {sys.argv[0]} <csv_file> [output_file]")
        print()
        print("  Process limited lines:")
        print(f"    {sys.argv[0]} <csv_file> <output_file> <max_lines>")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} candidates.csv test")
        print(f"  {sys.argv[0]} candidates.csv")
        print(f"  {sys.argv[0]} candidates.csv derived.csv 1000")
        sys.exit(1)

    csv_file = sys.argv[1]

    # Check for test mode
    if len(sys.argv) >= 3 and sys.argv[2] == 'test':
        num_lines = int(sys.argv[3]) if len(sys.argv) >= 4 else 10
        quick_test(csv_file, num_lines)
    else:
        # Full processing
        output_file = sys.argv[2] if len(sys.argv) >= 3 else None
        max_lines = int(sys.argv[3]) if len(sys.argv) >= 4 else None
        process_csv_file(csv_file, output_file, max_lines)

if __name__ == '__main__':
    main()
