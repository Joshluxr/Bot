#!/usr/bin/env python3
"""
Extract all addresses and private keys from found.txt
Format: CSV with Address,PrivateKey
"""

import re

def parse_found_txt(input_file, output_file):
    """Parse found.txt and extract addresses and private keys"""

    with open(input_file, 'r') as f:
        content = f.read()

    # Pattern to match PubAddress and Priv (HEX)
    # Looking for patterns like:
    # PubAddress: 1GUNPh...
    # Priv (HEX): 0x...

    addresses = re.findall(r'PubAddress:\s*([13][a-km-zA-HJ-NP-Z1-9]{25,34})', content)
    privkeys = re.findall(r'Priv \(HEX\):\s*(0x[0-9a-fA-F]{64})', content)

    print(f"Found {len(addresses)} addresses")
    print(f"Found {len(privkeys)} private keys")

    if len(addresses) != len(privkeys):
        print(f"WARNING: Mismatch! {len(addresses)} addresses vs {len(privkeys)} privkeys")

    # Write to CSV
    with open(output_file, 'w') as f:
        f.write("Address,PrivateKey\n")
        for addr, priv in zip(addresses, privkeys):
            # Remove 0x prefix from private key
            priv_clean = priv.replace('0x', '').upper()
            f.write(f"{addr},{priv_clean}\n")

    print(f"Wrote {len(addresses)} entries to {output_file}")
    return len(addresses)

if __name__ == "__main__":
    input_file = "/root/repo/address_server/found.txt"
    output_file = "/root/repo/bitcoin_keys_recovered.csv"

    count = parse_found_txt(input_file, output_file)

    print()
    print("=" * 70)
    print(f"Extraction complete! {count} Bitcoin addresses with private keys")
    print(f"Output file: {output_file}")
    print("=" * 70)
