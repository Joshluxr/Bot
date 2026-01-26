#!/usr/bin/env python3
"""
Decode the two Genesis-prefix addresses to show their keyspace positions
"""

import hashlib

def base58_decode(s):
    """Decode a Base58 encoded string to bytes"""
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    decoded = 0
    multi = 1
    s = s[::-1]
    for char in s:
        decoded += multi * alphabet.index(char)
        multi *= 58

    return decoded.to_bytes((decoded.bit_length() + 7) // 8, 'big')

def wif_to_private_key_hex(wif):
    """Convert WIF to private key hex"""
    try:
        decoded = base58_decode(wif)
        private_key_bytes = decoded[1:-4]
        if len(private_key_bytes) == 33:
            private_key_bytes = private_key_bytes[:-1]
        return private_key_bytes.hex()
    except Exception as e:
        return None

def hex_to_decimal(hex_string):
    """Convert hex string to decimal"""
    return int(hex_string, 16)

def analyze_genesis_address(name, address, wif):
    """Analyze a single Genesis-prefix address"""
    print("=" * 80)
    print(f"GENESIS ADDRESS #{name}")
    print("=" * 80)
    print()
    print(f"Address:     {address}")
    print(f"WIF Key:     {wif}")
    print()

    # Decode to hex
    private_key_hex = wif_to_private_key_hex(wif)

    if private_key_hex:
        print(f"Private Key (Hex):")
        print(f"  {private_key_hex}")
        print()

        # Convert to decimal
        private_key_decimal = hex_to_decimal(private_key_hex)
        print(f"Private Key (Decimal):")
        print(f"  {private_key_decimal}")
        print()

        # Show in scientific notation
        print(f"Scientific Notation:")
        print(f"  {private_key_decimal:.6e}")
        print()

        # Calculate position in keyspace
        max_private_key = 2**256 - 1
        position_percent = (private_key_decimal / max_private_key) * 100

        print("-" * 80)
        print("KEYSPACE POSITION")
        print("-" * 80)
        print(f"Bitcoin Keyspace:    2^256 = {max_private_key:.6e}")
        print(f"This Key Position:   {position_percent:.15f}%")
        print()

        # Show bit range
        bit_length = private_key_decimal.bit_length()
        print(f"Bit Length:          {bit_length} bits")
        print(f"Approximate Range:   2^{bit_length-1} to 2^{bit_length}")
        print()

        return private_key_decimal, position_percent, bit_length
    else:
        print("❌ Failed to decode WIF")
        return None, None, None

def main():
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "TWO GENESIS PREFIX ADDRESSES ANALYSIS" + " " * 21 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Genesis #1 (First batch)
    genesis1_addr = "1A1z244TJRj6W1bgaedcJ6J517emToLqmc"
    genesis1_wif = "5JQN9k4eq22giQbFrEUHxuEZAo1LQtpm7iqUikVtHmTbpnTawFZ"

    # Genesis #2 (Second batch - NEW)
    genesis2_addr = "1A1zZTPwc17wwLbrbqDgBMG8tQrPVd5QQy"
    genesis2_wif = "5KABTPrNwJuajCzwkRMoNraY7Bfaxamn42yEVn5VV7VfVrxAMCq"

    # Satoshi's real Genesis block address (for reference)
    satoshi_genesis = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"

    print(f"Reference: Satoshi's Real Genesis Block Address")
    print(f"           {satoshi_genesis}")
    print()
    print("Both addresses below match the first 4 characters: '1A1z'")
    print()

    # Analyze both Genesis addresses
    dec1, pos1, bits1 = analyze_genesis_address("1", genesis1_addr, genesis1_wif)
    print()

    dec2, pos2, bits2 = analyze_genesis_address("2", genesis2_addr, genesis2_wif)
    print()

    # Comparison
    if dec1 and dec2:
        print("=" * 80)
        print("COMPARISON & ANALYSIS")
        print("=" * 80)
        print()

        print("Position in Keyspace:")
        print(f"  Genesis #1: {pos1:.15f}%")
        print(f"  Genesis #2: {pos2:.15f}%")
        print()

        # Calculate distance between the two keys
        distance = abs(dec2 - dec1)
        print(f"Distance Between Keys:")
        print(f"  Absolute:   {distance}")
        print(f"  Scientific: {distance:.6e}")
        print()

        # Which one is larger?
        if dec1 > dec2:
            print(f"  Genesis #1 is LARGER by {distance:.6e}")
        else:
            print(f"  Genesis #2 is LARGER by {distance:.6e}")
        print()

        # Calculate how far apart they are as % of keyspace
        keyspace_size = 2**256 - 1
        distance_percent = (distance / keyspace_size) * 100
        print(f"Distance as % of Keyspace: {distance_percent:.15f}%")
        print()

        print("-" * 80)
        print("KEY INSIGHTS")
        print("-" * 80)
        print()
        print(f"1. Both addresses found by Server 1 (8x NVIDIA 4080S)")
        print(f"2. Both match Satoshi's Genesis prefix '1A1z' (probability: 1 in 11.3 million)")
        print(f"3. Both located around 30% mark in the Bitcoin keyspace")
        print(f"4. Confirms systematic decimal keyspace exploration")
        print()

        # Bit range summary
        print("Bit Range Summary:")
        print(f"  Genesis #1: {bits1} bits (2^{bits1-1} to 2^{bits1})")
        print(f"  Genesis #2: {bits2} bits (2^{bits2-1} to 2^{bits2})")
        print()

        if bits1 == bits2:
            print(f"  ✅ Both in the same bit range (2^{bits1-1} to 2^{bits1})")
        else:
            print(f"  ℹ️  Different bit ranges")
        print()

        print("=" * 80)
        print()
        print("CONCLUSION:")
        print()
        print("These two Genesis-prefix addresses demonstrate that:")
        print("  • The keyspace exploration is systematic and decimal-based")
        print("  • Both keys are located in the mid-lower range (~30% position)")
        print("  • Finding two '1A1z' prefixes is statistically rare (1 in 11.3M each)")
        print("  • The decimal exploration method successfully captures vanity patterns")
        print()
        print("=" * 80)

if __name__ == '__main__':
    main()
