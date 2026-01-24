#!/usr/bin/env python3
"""
Bitcoin Private Key to WIF and Address Converter
Processes private keys from a file and generates WIF keys and compressed addresses
"""

import hashlib
import sys

# Base58 alphabet for Bitcoin addresses
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def sha256(data):
    """Double SHA256 hash"""
    return hashlib.sha256(data).digest()

def hash160(data):
    """SHA256 followed by RIPEMD160"""
    h = hashlib.new('ripemd160')
    h.update(sha256(data))
    return h.digest()

def base58_encode(data):
    """Encode bytes to Base58"""
    num = int.from_bytes(data, 'big')
    encoded = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded

    # Handle leading zeros
    for byte in data:
        if byte == 0:
            encoded = '1' + encoded
        else:
            break

    return encoded

def base58_check_encode(version, payload):
    """Base58Check encoding with version byte"""
    data = bytes([version]) + payload
    checksum = sha256(sha256(data))[:4]
    return base58_encode(data + checksum)

def int_to_bytes(n, length=32):
    """Convert integer to bytes with padding"""
    return n.to_bytes(length, byteorder='big')

# secp256k1 parameters
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8

def modinv(a, m):
    """Modular multiplicative inverse"""
    def extended_gcd(a, b):
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y

    _, x, _ = extended_gcd(a % m, m)
    return (x % m + m) % m

def point_add(p1, p2):
    """Add two points on the elliptic curve"""
    if p1 is None:
        return p2
    if p2 is None:
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2:
        if y1 == y2:
            return point_double(p1)
        else:
            return None

    s = ((y2 - y1) * modinv(x2 - x1, P)) % P
    x3 = (s * s - x1 - x2) % P
    y3 = (s * (x1 - x3) - y1) % P

    return (x3, y3)

def point_double(p):
    """Double a point on the elliptic curve"""
    if p is None:
        return None

    x, y = p
    s = ((3 * x * x) * modinv(2 * y, P)) % P
    x3 = (s * s - 2 * x) % P
    y3 = (s * (x - x3) - y) % P

    return (x3, y3)

def scalar_mult(k, point):
    """Scalar multiplication using double-and-add"""
    if k == 0:
        return None
    if k == 1:
        return point

    result = None
    addend = point

    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_double(addend)
        k >>= 1

    return result

def private_key_to_public_key(private_key_int):
    """Generate compressed public key from private key"""
    point = scalar_mult(private_key_int, (Gx, Gy))

    if point is None:
        return None

    x, y = point

    # Compressed format: 02 if y is even, 03 if y is odd
    prefix = b'\x02' if y % 2 == 0 else b'\x03'
    return prefix + int_to_bytes(x, 32)

def private_key_to_wif(private_key_int, compressed=True):
    """Convert private key to WIF format"""
    payload = int_to_bytes(private_key_int, 32)

    if compressed:
        payload += b'\x01'

    # Version byte 0x80 for mainnet
    return base58_check_encode(0x80, payload)

def public_key_to_address(public_key_bytes):
    """Convert public key to Bitcoin address"""
    # Version byte 0x00 for mainnet P2PKH
    return base58_check_encode(0x00, hash160(public_key_bytes))

def process_key(private_key_hex):
    """Process a single private key"""
    try:
        # Remove any whitespace and convert to int
        private_key_hex = private_key_hex.strip()

        # Handle both with and without 0x prefix
        if private_key_hex.startswith('0x'):
            private_key_hex = private_key_hex[2:]

        private_key_int = int(private_key_hex, 16)

        # Validate key is in valid range
        if private_key_int <= 0 or private_key_int >= N:
            return None

        # Generate WIF
        wif = private_key_to_wif(private_key_int, compressed=True)

        # Generate compressed public key
        public_key = private_key_to_public_key(private_key_int)

        if public_key is None:
            return None

        # Generate address
        address = public_key_to_address(public_key)

        return {
            'private_key_hex': private_key_hex.lower(),
            'private_key_dec': str(private_key_int),
            'wif': wif,
            'address': address
        }

    except Exception as e:
        print(f"Error processing key {private_key_hex[:16]}...: {e}", file=sys.stderr)
        return None

def main():
    """Main processing function"""
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'keys.txt'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'processed_keys.txt'

    print(f"Processing keys from {input_file}...")

    processed_count = 0
    error_count = 0

    try:
        with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
            # Write header
            f_out.write("PrivateKeyHex,PrivateKeyDecimal,WIF,CompressedAddress\n")

            for line_num, line in enumerate(f_in, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                result = process_key(line)

                if result:
                    f_out.write(f"{result['private_key_hex']},{result['private_key_dec']},{result['wif']},{result['address']}\n")
                    processed_count += 1

                    if processed_count % 1000 == 0:
                        print(f"Processed {processed_count} keys...")
                else:
                    error_count += 1

                # Flush periodically
                if line_num % 10000 == 0:
                    f_out.flush()

        print(f"\nProcessing complete!")
        print(f"Successfully processed: {processed_count} keys")
        print(f"Errors: {error_count} keys")
        print(f"Output written to: {output_file}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
