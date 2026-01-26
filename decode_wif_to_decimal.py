#!/usr/bin/env python3
"""
Decode WIF private key to decimal value
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

        # Remove version byte (0x80) and checksum (last 4 bytes)
        # WIF format: [1 byte version][32 bytes private key][4 bytes checksum]
        private_key_bytes = decoded[1:-4]

        # If length is 33, it's compressed (has 0x01 suffix), remove it
        if len(private_key_bytes) == 33:
            private_key_bytes = private_key_bytes[:-1]

        return private_key_bytes.hex()
    except Exception as e:
        return None

def hex_to_decimal(hex_string):
    """Convert hex string to decimal"""
    return int(hex_string, 16)

def main():
    wif = "5JQN9k4eq22giQbFrEUHxuEZAo1LQtpm7iqUikVtHmTbpnTawFZ"

    print("=" * 80)
    print("WIF PRIVATE KEY DECODING")
    print("=" * 80)
    print()

    print(f"WIF Private Key: {wif}")
    print()

    # Decode to hex
    private_key_hex = wif_to_private_key_hex(wif)

    if private_key_hex:
        print(f"Private Key (Hex): {private_key_hex}")
        print()

        # Convert to decimal
        private_key_decimal = hex_to_decimal(private_key_hex)
        print(f"Private Key (Decimal): {private_key_decimal}")
        print()

        # Show in scientific notation
        print(f"Scientific Notation: {private_key_decimal:.6e}")
        print()

        # Calculate position in keyspace
        max_private_key = 2**256 - 1
        position_percent = (private_key_decimal / max_private_key) * 100

        print("=" * 80)
        print("KEYSPACE POSITION")
        print("=" * 80)
        print()
        print(f"Bitcoin Keyspace Size: 2^256")
        print(f"Max Private Key: {max_private_key:.6e}")
        print()
        print(f"This Key Position: {position_percent:.15f}%")
        print()

        # Show bit range
        bit_length = private_key_decimal.bit_length()
        print(f"Bit Length: {bit_length} bits")
        print(f"Approximate Range: 2^{bit_length-1} to 2^{bit_length}")
        print()

        # Additional context
        print("=" * 80)
        print("CONTEXT")
        print("=" * 80)
        print()

        if bit_length < 128:
            print("⚠️  WARNING: Very low range (insecure)")
        elif bit_length < 160:
            print("⚠️  Low range (potentially vulnerable)")
        elif bit_length < 200:
            print("ℹ️  Mid-lower range")
        elif bit_length < 220:
            print("ℹ️  Mid range")
        elif bit_length < 240:
            print("ℹ️  Mid-upper range")
        else:
            print("✅ High range (secure)")

        print()
        print("This key is part of systematic decimal keyspace exploration,")
        print("likely starting from a specific decimal number and incrementing.")

    else:
        print("❌ Failed to decode WIF")

if __name__ == '__main__':
    main()
