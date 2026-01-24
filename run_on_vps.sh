#!/bin/bash
# Script to run key processing on remote VPS

VPS_IP="65.75.200.135"
VPS_PASS="LiA6QhucR470Ia3"
DOWNLOAD_URL="https://tmpfiles.org/dl/20890277/server2_privkeys_only.txt"

echo "Connecting to VPS and processing keys..."

# Use sshpass to automate SSH password authentication
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no root@$VPS_IP << 'ENDSSH'

# Download the key list
echo "Downloading key list..."
wget -O server2_privkeys_only.txt "https://tmpfiles.org/dl/20890277/server2_privkeys_only.txt"

# Create the Python script on the VPS
cat > process_keys.py << 'ENDPYTHON'
#!/usr/bin/env python3
"""
Script to process private keys and generate:
1. Private key (WIF format if applicable)
2. Hexadecimal string key
3. Compressed public address
"""

import hashlib
import binascii
from typing import Tuple

def sha256(data: bytes) -> bytes:
    """Compute SHA256 hash"""
    return hashlib.sha256(data).digest()

def ripemd160(data: bytes) -> bytes:
    """Compute RIPEMD160 hash"""
    h = hashlib.new('ripemd160')
    h.update(data)
    return h.digest()

def base58_encode(data: bytes) -> str:
    """Encode bytes to Base58"""
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

    # Convert bytes to integer
    num = int.from_bytes(data, byteorder='big')

    # Encode
    encoded = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded = alphabet[remainder] + encoded

    # Handle leading zeros
    for byte in data:
        if byte == 0:
            encoded = '1' + encoded
        else:
            break

    return encoded

def private_key_to_wif(private_key_hex: str, compressed: bool = True) -> str:
    """Convert private key hex to WIF format"""
    # Add version byte (0x80 for mainnet)
    extended = '80' + private_key_hex

    # Add compression flag if compressed
    if compressed:
        extended += '01'

    # Convert to bytes
    extended_bytes = bytes.fromhex(extended)

    # Double SHA256 for checksum
    checksum = sha256(sha256(extended_bytes))[:4]

    # Append checksum and encode
    final = extended_bytes + checksum
    return base58_encode(final)

def public_key_from_private(private_key_hex: str) -> Tuple[int, int]:
    """
    Derive public key from private key using secp256k1
    Returns (x, y) coordinates
    """
    # secp256k1 parameters
    p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
    Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
    a = 0

    def mod_inv(a: int, m: int) -> int:
        """Modular inverse"""
        return pow(a, -1, m)

    def point_add(p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[int, int]:
        """Add two points on elliptic curve"""
        if p1 is None:
            return p2
        if p2 is None:
            return p1

        x1, y1 = p1
        x2, y2 = p2

        if x1 == x2:
            if y1 == y2:
                # Point doubling
                s = (3 * x1 * x1 * mod_inv(2 * y1, p)) % p
            else:
                return None
        else:
            # Point addition
            s = ((y2 - y1) * mod_inv(x2 - x1, p)) % p

        x3 = (s * s - x1 - x2) % p
        y3 = (s * (x1 - x3) - y1) % p

        return (x3, y3)

    def point_multiply(k: int, point: Tuple[int, int]) -> Tuple[int, int]:
        """Multiply point by scalar using double-and-add"""
        result = None
        addend = point

        while k:
            if k & 1:
                result = point_add(result, addend)
            addend = point_add(addend, addend)
            k >>= 1

        return result

    # Convert private key to integer
    private_key_int = int(private_key_hex, 16)

    # Multiply generator point by private key
    public_key = point_multiply(private_key_int, (Gx, Gy))

    return public_key

def public_key_to_address(public_key: Tuple[int, int], compressed: bool = True) -> str:
    """Convert public key to Bitcoin address"""
    x, y = public_key

    if compressed:
        # Compressed public key format
        prefix = '02' if y % 2 == 0 else '03'
        public_key_bytes = bytes.fromhex(prefix + format(x, '064x'))
    else:
        # Uncompressed public key format
        public_key_bytes = bytes.fromhex('04' + format(x, '064x') + format(y, '064x'))

    # SHA256 then RIPEMD160
    sha_hash = sha256(public_key_bytes)
    ripe_hash = ripemd160(sha_hash)

    # Add version byte (0x00 for mainnet)
    versioned = b'\x00' + ripe_hash

    # Double SHA256 for checksum
    checksum = sha256(sha256(versioned))[:4]

    # Append checksum and encode
    address_bytes = versioned + checksum
    return base58_encode(address_bytes)

def process_private_key(private_key_hex: str) -> dict:
    """Process a single private key and return all derivatives"""
    # Clean the input
    private_key_hex = private_key_hex.strip().lower()

    # Remove any prefixes
    if private_key_hex.startswith('0x'):
        private_key_hex = private_key_hex[2:]

    # Ensure it's 64 characters (32 bytes)
    private_key_hex = private_key_hex.zfill(64)

    try:
        # Derive public key
        public_key = public_key_from_private(private_key_hex)

        # Generate WIF
        wif_compressed = private_key_to_wif(private_key_hex, compressed=True)

        # Generate compressed address
        address_compressed = public_key_to_address(public_key, compressed=True)

        return {
            'private_key_hex': private_key_hex,
            'wif': wif_compressed,
            'address': address_compressed,
            'public_key_x': format(public_key[0], '064x'),
            'public_key_y': format(public_key[1], '064x')
        }
    except Exception as e:
        return {
            'private_key_hex': private_key_hex,
            'error': str(e)
        }

def main():
    """Main processing function"""
    import sys

    input_file = 'server2_privkeys_only.txt'
    output_file = 'processed_keys.txt'

    print(f"Processing keys from {input_file}...")

    try:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: {input_file} not found!")
        sys.exit(1)

    results = []
    total = len(lines)

    with open(output_file, 'w') as out:
        out.write("Private Key (Hex) | WIF | Compressed Address\n")
        out.write("=" * 150 + "\n")

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            result = process_private_key(line)

            if 'error' in result:
                out.write(f"{result['private_key_hex']} | ERROR: {result['error']}\n")
                print(f"[{i}/{total}] Error processing key: {result['error']}")
            else:
                out.write(f"{result['private_key_hex']} | {result['wif']} | {result['address']}\n")
                print(f"[{i}/{total}] Processed: {result['address']}")

            results.append(result)

    print(f"\nProcessing complete! Results saved to {output_file}")
    print(f"Total keys processed: {len(results)}")
    print(f"Successful: {sum(1 for r in results if 'error' not in r)}")
    print(f"Errors: {sum(1 for r in results if 'error' in r)}")

if __name__ == '__main__':
    main()
ENDPYTHON

# Make script executable
chmod +x process_keys.py

# Run the script
echo "Processing keys..."
python3 process_keys.py

# Show summary
echo ""
echo "Results saved to processed_keys.txt"
echo "First 10 lines of output:"
head -n 12 processed_keys.txt

ENDSSH

echo ""
echo "Processing complete on VPS!"
echo "Retrieving results..."

# Copy the results back
sshpass -p "$VPS_PASS" scp -o StrictHostKeyChecking=no root@$VPS_IP:~/processed_keys.txt ./processed_keys.txt

echo "Results downloaded to ./processed_keys.txt"
