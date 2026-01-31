#!/usr/bin/env python3
"""
K3 Private Key Recovery Tool
Uses secp256k1 endomorphism to recover actual private keys from logged seeds
"""

import coincurve as cc
import hashlib

# secp256k1 curve order
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# Endomorphism constants
LAMBDA = 0x5363ad4cc05c30e0a5261c028812645a122e22ea20816678df02967c1b23bd72
BETA = 0x7ae96a2b657c07106e64479eac3434e99cf0497512f58995c1396c28719501ee

# Lambda^2 (lambda squared)
LAMBDA2 = (LAMBDA * LAMBDA) % N

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

def hash160_to_address(hash160_hex):
    """Convert hash160 to Bitcoin address"""
    import base58

    # Add version byte (0x00 for mainnet)
    versioned = bytes.fromhex('00' + hash160_hex)

    # Double SHA256 for checksum
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]

    # Combine and encode
    address_bytes = versioned + checksum
    return base58.b58encode(address_bytes).decode()

def generate_k3_privkeys(seed_privkey):
    """
    Generate all 12 K3 private key variations using endomorphism

    K3 generates 12 addresses from one seed:
    - 6 for compressed: k, k*lambda, k*lambda^2, -k, -k*lambda, -k*lambda^2
    - 6 for uncompressed: same transformations

    Returns: dict mapping incr -> (privkey, compressed)
    """
    k = seed_privkey

    # Calculate all endomorphism transformations
    k_lambda = (k * LAMBDA) % N
    k_lambda2 = (k * LAMBDA2) % N
    neg_k = N - k
    neg_k_lambda = N - k_lambda
    neg_k_lambda2 = N - k_lambda2

    # K3 generates 12 variations
    # Based on standard K3 implementation pattern
    k3_keys = {}

    # Compressed variations (incr values are estimates - need to verify)
    k3_keys[0] = (k, True)              # Base key
    k3_keys[1] = (k_lambda, True)       # lambda * k
    k3_keys[2] = (k_lambda2, True)      # lambda^2 * k
    k3_keys[3] = (neg_k, True)          # -k
    k3_keys[4] = (neg_k_lambda, True)   # -lambda * k
    k3_keys[5] = (neg_k_lambda2, True)  # -lambda^2 * k

    # Uncompressed variations
    k3_keys[6] = (k, False)
    k3_keys[7] = (k_lambda, False)
    k3_keys[8] = (k_lambda2, False)
    k3_keys[9] = (neg_k, False)
    k3_keys[10] = (neg_k_lambda, False)
    k3_keys[11] = (neg_k_lambda2, False)

    return k3_keys

def recover_privkey_from_k3_candidate(logged_privkey_hex, target_hash160, incr):
    """
    Recover actual private key from K3 logged data

    K3 Formula: actual_privkey = logged_privkey + incr (mod N)

    Args:
        logged_privkey_hex: The "privkey" from K3 log (base private key)
        target_hash160: The correct hash160 from the log
        incr: The increment value from the K3 log

    Returns:
        (actual_privkey, compressed, address) or None
    """
    base_privkey = int(logged_privkey_hex, 16)

    # K3 formula: actual = base + incr (mod curve order)
    actual_privkey = (base_privkey + incr) % N

    # Try compressed first (most common)
    for compressed in [True, False]:
        hash160 = privkey_to_hash160(actual_privkey, compressed)

        if hash160 == target_hash160:
            try:
                address = hash160_to_address(hash160)
            except:
                address = "N/A"

            print(f"✓ MATCH FOUND!")
            print(f"  Base privkey: {logged_privkey_hex}")
            print(f"  K3 incr: {incr}")
            print(f"  Actual privkey: {actual_privkey:064x}")
            print(f"  Compressed: {compressed}")
            print(f"  Hash160: {hash160}")
            print(f"  Address: {address}")
            return (actual_privkey, compressed, address)

    print(f"✗ No match found!")
    print(f"  Base: {logged_privkey_hex[:16]}...")
    print(f"  Incr: {incr}")
    print(f"  Actual: {actual_privkey:064x}")
    print(f"  Target: {target_hash160}")
    return None

def test_k3_recovery():
    """Test K3 recovery with sample data from K3_ALGORITHM_ANALYSIS.md"""

    test_seed = 0x3d1709f676b0ad2f920c2a2ee036d8fe0a0d5ea64e6ebcb271c62560b9115950
    target_hash160 = "099822b6b987a7d869ae660a494603e908ea3a30"
    test_incr = 499  # From the log entry

    print("Testing K3 Private Key Recovery")
    print("=" * 60)
    print(f"Base privkey (from log): {test_seed:064x}")
    print(f"Incr (from log): {test_incr}")
    print(f"Target hash160: {target_hash160}")
    print()
    print("K3 Formula: actual_privkey = base_privkey + incr (mod N)")
    print()

    result = recover_privkey_from_k3_candidate(
        f"{test_seed:064x}",
        target_hash160,
        test_incr
    )

    if result:
        privkey, compressed, address = result
        print()
        print("=" * 60)
        print("SUCCESS! Private key recovered using K3 formula.")
        print()
        print(f"Private Key (HEX): {privkey:064x}")
        print(f"Compressed: {compressed}")
        print(f"Address: {address}")
    else:
        print()
        print("=" * 60)
        print("Recovery failed - checking if formula needs adjustment")

def process_k3_candidates_file(filepath):
    """
    Process a file containing K3 candidates

    Expected format:
    [K3 CANDIDATE ...] tid=... incr=NNN
      hash160=...
      privkey=...
    """
    import re

    print(f"Processing K3 candidates from: {filepath}")
    print()

    with open(filepath, 'r') as f:
        content = f.read()

    # Parse K3 candidate entries
    pattern = r'\[K3 CANDIDATE.*?incr=(-?\d+).*?hash160=([0-9a-f]{40}).*?privkey=([0-9a-f]{64})'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    print(f"Found {len(matches)} K3 candidates")
    print()

    recovered = []
    for i, (incr, hash160, base_privkey) in enumerate(matches[:10], 1):  # Test first 10
        print(f"--- Candidate {i} ---")
        result = recover_privkey_from_k3_candidate(base_privkey, hash160, int(incr))
        if result:
            recovered.append(result)
        print()

    print("=" * 60)
    print(f"Successfully recovered: {len(recovered)}/{len(matches[:10])}")
    return recovered

if __name__ == "__main__":
    print("K3 Private Key Recovery Tool")
    print("Using secp256k1 endomorphism transformations")
    print()

    test_k3_recovery()
