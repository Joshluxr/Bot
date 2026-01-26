#!/usr/bin/env python3
"""
Show exact decimal values for the two Genesis-prefix addresses
"""

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
    decoded = base58_decode(wif)
    private_key_bytes = decoded[1:-4]
    if len(private_key_bytes) == 33:
        private_key_bytes = private_key_bytes[:-1]
    return private_key_bytes.hex()

def main():
    print()
    print("=" * 80)
    print("EXACT DECIMAL VALUES - TWO GENESIS PREFIX ADDRESSES")
    print("=" * 80)
    print()

    # Genesis #1
    wif1 = "5JQN9k4eq22giQbFrEUHxuEZAo1LQtpm7iqUikVtHmTbpnTawFZ"
    addr1 = "1A1z244TJRj6W1bgaedcJ6J517emToLqmc"

    # Genesis #2
    wif2 = "5KABTPrNwJuajCzwkRMoNraY7Bfaxamn42yEVn5VV7VfVrxAMCq"
    addr2 = "1A1zZTPwc17wwLbrbqDgBMG8tQrPVd5QQy"

    # Decode both
    hex1 = wif_to_private_key_hex(wif1)
    hex2 = wif_to_private_key_hex(wif2)

    dec1 = int(hex1, 16)
    dec2 = int(hex2, 16)

    # Bitcoin keyspace max
    max_key = 2**256 - 1

    print("GENESIS ADDRESS #1")
    print("-" * 80)
    print(f"Address:     {addr1}")
    print(f"WIF:         {wif1}")
    print()
    print(f"Hex:         {hex1}")
    print()
    print("Decimal:")
    print(f"{dec1}")
    print()

    pos1 = (dec1 / max_key) * 100
    print(f"Position:    {pos1}%")
    print()
    print()

    print("GENESIS ADDRESS #2")
    print("-" * 80)
    print(f"Address:     {addr2}")
    print(f"WIF:         {wif2}")
    print()
    print(f"Hex:         {hex2}")
    print()
    print("Decimal:")
    print(f"{dec2}")
    print()

    pos2 = (dec2 / max_key) * 100
    print(f"Position:    {pos2}%")
    print()
    print()

    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print()
    print(f"Bitcoin Keyspace Maximum (2^256 - 1):")
    print(f"{max_key}")
    print()
    print(f"Genesis #1 Decimal:")
    print(f"{dec1}")
    print()
    print(f"Genesis #2 Decimal:")
    print(f"{dec2}")
    print()
    print(f"Difference:")
    print(f"{dec2 - dec1}")
    print()
    print(f"Genesis #1 Position: {pos1:.20f}%")
    print(f"Genesis #2 Position: {pos2:.20f}%")
    print()

if __name__ == '__main__':
    main()
