#!/usr/bin/env python3
"""
Extract all addresses and private keys from found.txt
Properly parse 3-line groups: PubAddress, Priv (WIF), Priv (HEX)
"""

def parse_found_txt(input_file, output_csv, output_txt):
    """Parse found.txt and extract addresses and private keys"""

    with open(input_file, 'r') as f:
        lines = f.readlines()

    addresses = []
    privkeys_hex = []
    privkeys_wif = []

    # Parse in groups of 3 lines
    for i in range(0, len(lines), 3):
        if i + 2 < len(lines):
            addr_line = lines[i].strip()
            wif_line = lines[i + 1].strip()
            hex_line = lines[i + 2].strip()

            # Extract address
            if 'PubAddress:' in addr_line:
                addr = addr_line.split('PubAddress:')[1].strip()
                addresses.append(addr)

            # Extract WIF
            if 'Priv (WIF):' in wif_line:
                wif = wif_line.split('Priv (WIF):')[1].strip()
                privkeys_wif.append(wif)

            # Extract HEX
            if 'Priv (HEX):' in hex_line:
                hex_key = hex_line.split('Priv (HEX):')[1].strip()
                # Remove 0x prefix
                hex_key = hex_key.replace('0x', '').upper()
                privkeys_hex.append(hex_key)

    print(f"Parsed {len(addresses)} addresses")
    print(f"Parsed {len(privkeys_wif)} WIF keys")
    print(f"Parsed {len(privkeys_hex)} HEX keys")

    # Write CSV (Address, HEX Private Key)
    with open(output_csv, 'w') as f:
        f.write("Address,PrivateKey\n")
        for addr, priv_hex in zip(addresses, privkeys_hex):
            f.write(f"{addr},{priv_hex}\n")

    # Write formatted TXT (Address + both formats)
    with open(output_txt, 'w') as f:
        f.write("Bitcoin Private Keys - Recovered from K3\n")
        f.write("=" * 80 + "\n\n")

        for i, (addr, wif, hex_key) in enumerate(zip(addresses, privkeys_wif, privkeys_hex), 1):
            f.write(f"Entry #{i}\n")
            f.write(f"Address:     {addr}\n")
            f.write(f"Private Key (HEX): {hex_key}\n")
            f.write(f"Private Key (WIF): {wif}\n")
            f.write("\n")

    print(f"\nWrote {len(addresses)} entries to:")
    print(f"  - CSV:  {output_csv}")
    print(f"  - TXT:  {output_txt}")

    return len(addresses)

if __name__ == "__main__":
    input_file = "/root/repo/address_server/found.txt"
    output_csv = "/root/repo/bitcoin_keys_recovered.csv"
    output_txt = "/root/repo/bitcoin_keys_recovered.txt"

    count = parse_found_txt(input_file, output_csv, output_txt)

    print()
    print("=" * 80)
    print(f"✅ Extraction Complete! {count:,} Bitcoin addresses with private keys")
    print("=" * 80)
