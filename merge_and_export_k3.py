#!/usr/bin/env python3
"""
Merge K3 candidate files and export all Bitcoin addresses with private keys
"""

import csv

def merge_k3_files(file1, file2, output_csv, output_txt):
    """Merge two K3 candidate CSV files"""

    print(f"Reading Server 1: {file1}")
    addresses = []

    # Read Server 1
    with open(file1, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            addresses.append({
                'address': row['Address'],
                'privkey': row['PrivateKey'],
                'hash160': row['Hash160']
            })

    print(f"  Server 1: {len(addresses):,} addresses")

    # Read Server 2
    print(f"Reading Server 2: {file2}")
    server2_start = len(addresses)

    with open(file2, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            addresses.append({
                'address': row['Address'],
                'privkey': row['PrivateKey'],
                'hash160': row['Hash160']
            })

    print(f"  Server 2: {len(addresses) - server2_start:,} addresses")
    print(f"  Total: {len(addresses):,} addresses")

    # Remove duplicates
    print("\nRemoving duplicates...")
    seen = set()
    unique_addresses = []

    for addr in addresses:
        key = addr['address']
        if key not in seen:
            seen.add(key)
            unique_addresses.append(addr)

    print(f"  Unique addresses: {len(unique_addresses):,}")
    print(f"  Duplicates removed: {len(addresses) - len(unique_addresses):,}")

    # Write CSV
    print(f"\nWriting CSV: {output_csv}")
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Address', 'PrivateKey', 'Hash160'])

        for addr in unique_addresses:
            writer.writerow([addr['address'], addr['privkey'], addr['hash160']])

    # Write formatted text
    print(f"Writing TXT: {output_txt}")
    with open(output_txt, 'w') as f:
        f.write("Bitcoin Private Keys - BloomSearch32K3 Recovery\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total Addresses: {len(unique_addresses):,}\n")
        f.write(f"Source: BloomSearch32K3 GPU search\n")
        f.write("=" * 80 + "\n\n")

        for i, addr in enumerate(unique_addresses, 1):
            f.write(f"Entry #{i}\n")
            f.write(f"Address:     {addr['address']}\n")
            f.write(f"Private Key: {addr['privkey']}\n")
            f.write(f"Hash160:     {addr['hash160']}\n")
            f.write("\n")

    print(f"\n{'=' * 80}")
    print(f"✅ Export Complete!")
    print(f"{'=' * 80}")
    print(f"Total unique addresses: {len(unique_addresses):,}")
    print(f"CSV file: {output_csv}")
    print(f"TXT file: {output_txt}")

    return len(unique_addresses)

if __name__ == "__main__":
    file1 = "/root/repo/server1_candidates.csv"
    file2 = "/root/repo/server2_candidates.csv"
    output_csv = "/root/repo/k3_all_addresses.csv"
    output_txt = "/root/repo/k3_all_addresses.txt"

    count = merge_k3_files(file1, file2, output_csv, output_txt)

    print(f"\n🎉 Successfully exported {count:,} Bitcoin addresses from BloomSearch32K3!")
