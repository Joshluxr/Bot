#!/usr/bin/env python3
"""
Extract All Private Keys from K3 Candidates
Uses the confirmed formula: actual_privkey = (base_privkey + incr) % N
"""

import coincurve as cc
import hashlib
import base58
import re
import sys
import os

N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def privkey_to_hash160(privkey_int, compressed=True):
    """Convert private key to hash160"""
    privkey_bytes = privkey_int.to_bytes(32, 'big')
    pubkey = cc.PublicKey.from_secret(privkey_bytes)
    pubkey_bytes = pubkey.format(compressed=compressed)
    sha256 = hashlib.sha256(pubkey_bytes).digest()
    ripemd160 = hashlib.new('ripemd160', sha256).digest()
    return ripemd160.hex()

def hash160_to_address(hash160_hex):
    """Convert hash160 to Bitcoin address"""
    versioned = bytes.fromhex('00' + hash160_hex)
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    address_bytes = versioned + checksum
    return base58.b58encode(address_bytes).decode()

def privkey_to_wif(privkey_int, compressed=True):
    """Convert private key to WIF format"""
    extended = b'\x80' + privkey_int.to_bytes(32, 'big')
    if compressed:
        extended += b'\x01'
    checksum = hashlib.sha256(hashlib.sha256(extended).digest()).digest()[:4]
    return base58.b58encode(extended + checksum).decode()

def recover_k3_privkey(base_privkey_hex, target_hash160, incr):
    """
    Recover actual private key using K3 formula

    Returns: (privkey, compressed, address, wif) or None
    """
    base = int(base_privkey_hex, 16)
    actual_privkey = (base + incr) % N

    # Try both compressed and uncompressed
    for compressed in [True, False]:
        hash160 = privkey_to_hash160(actual_privkey, compressed)

        if hash160 == target_hash160:
            address = hash160_to_address(hash160)
            wif = privkey_to_wif(actual_privkey, compressed)
            return (actual_privkey, compressed, address, wif)

    return None

def parse_k3_log_file(filepath):
    """
    Parse K3 candidate log file

    Expected format:
    [K3 CANDIDATE COMP/UNCOMP iter=...] tid=... incr=NNN
      hash160=...
      privkey=...
    """
    with open(filepath, 'r') as f:
        content = f.read()

    # Pattern to match K3 candidate entries
    pattern = r'\[K3 CANDIDATE\s+(COMP|UNCOMP).*?incr=(-?\d+).*?hash160=([0-9a-f]{40}).*?privkey=([0-9a-f]{64})'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    return matches

def process_k3_candidates(filepath, output_file=None):
    """Process all K3 candidates from a log file"""

    print("=" * 90)
    print(f"Processing K3 Candidates: {filepath}")
    print("=" * 90)
    print()

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return

    candidates = parse_k3_log_file(filepath)
    print(f"Found {len(candidates)} K3 candidates in log file")
    print()

    results = []
    success_count = 0
    fail_count = 0

    for i, (mode, incr, hash160, base_privkey) in enumerate(candidates, 1):
        print(f"[{i}/{len(candidates)}] Processing candidate...")
        print(f"  Mode: {mode}, Incr: {incr}, Hash160: {hash160[:16]}...")

        result = recover_k3_privkey(base_privkey, hash160, int(incr))

        if result:
            privkey, compressed, address, wif = result
            success_count += 1

            print(f"  ✓ RECOVERED!")
            print(f"    Address:    {address}")
            print(f"    Private Key: {privkey:064x}")
            print(f"    WIF:        {wif}")

            results.append({
                'address': address,
                'privkey_hex': f"{privkey:064x}",
                'wif': wif,
                'compressed': compressed,
                'hash160': hash160,
                'base_privkey': base_privkey,
                'incr': incr
            })
        else:
            fail_count += 1
            print(f"  ✗ Failed to recover")

        print()

    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"Total candidates: {len(candidates)}")
    print(f"Successfully recovered: {success_count}")
    print(f"Failed: {fail_count}")
    print()

    # Write results to output file
    if output_file and results:
        with open(output_file, 'w') as f:
            f.write("# K3 Private Key Recovery Results\n")
            f.write(f"# Total Recovered: {len(results)}\n")
            f.write("#\n")
            f.write("# Format: Address | Private Key (HEX) | WIF | Compressed\n")
            f.write("#" + "=" * 88 + "\n\n")

            for r in results:
                f.write(f"Address:    {r['address']}\n")
                f.write(f"PrivKey:    {r['privkey_hex']}\n")
                f.write(f"WIF:        {r['wif']}\n")
                f.write(f"Compressed: {r['compressed']}\n")
                f.write(f"Hash160:    {r['hash160']}\n")
                f.write("\n")

        print(f"Results written to: {output_file}")
        print()

    return results

if __name__ == "__main__":
    print()
    print("=" * 90)
    print(" " * 30 + "K3 PRIVATE KEY EXTRACTOR")
    print("=" * 90)
    print()
    print("Formula: actual_privkey = (base_privkey + incr) % N")
    print()

    # Check for log files
    log_files = []

    # Search for candidate log files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if 'candidate' in file.lower() or ('k3' in file.lower() and file.endswith('.log')):
                log_files.append(os.path.join(root, file))

    if log_files:
        print(f"Found {len(log_files)} potential K3 log file(s):")
        for lf in log_files:
            print(f"  - {lf}")
        print()

        for log_file in log_files:
            output_file = log_file.replace('.log', '_recovered.txt').replace('.txt', '_recovered.txt')
            process_k3_candidates(log_file, output_file)
    else:
        print("No K3 candidate log files found in current directory.")
        print()
        print("Usage: python3 extract_all_privkeys.py [logfile]")
        print()
        print("Or provide a log file as argument:")
        if len(sys.argv) > 1:
            log_file = sys.argv[1]
            output_file = log_file.replace('.log', '_recovered.txt')
            process_k3_candidates(log_file, output_file)
