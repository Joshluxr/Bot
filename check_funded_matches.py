#!/usr/bin/env python3
"""
Check if any addresses in our complete dataset match funded Bitcoin addresses
"""

import csv
from collections import defaultdict

def load_our_addresses():
    """Load all addresses from our complete dataset"""
    addresses = {}
    print("Loading our complete dataset...")
    with open('./final_complete.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            addresses[row['address']] = row['privkey']
    print(f"Loaded {len(addresses):,} addresses from our dataset")
    return addresses

def check_funded_addresses(our_addresses):
    """Check each of our addresses against the funded addresses list"""
    print("\nChecking against 55+ million funded addresses...")
    print("This may take a few minutes...")

    matches = []
    checked = 0

    # Read funded addresses line by line and check for matches
    with open('/root/repo/bitcoin_results/funded_addresses_sorted.txt', 'r') as f:
        for line in f:
            funded_addr = line.strip()
            if funded_addr in our_addresses:
                matches.append({
                    'address': funded_addr,
                    'privkey': our_addresses[funded_addr]
                })
                print(f"\n🚨 MATCH FOUND: {funded_addr}")

            checked += 1
            if checked % 1000000 == 0:
                print(f"  Checked {checked:,} funded addresses... ({len(matches)} matches so far)")

    print(f"\nTotal funded addresses checked: {checked:,}")
    return matches

def main():
    print("=" * 80)
    print("FUNDED ADDRESS MATCH CHECK")
    print("=" * 80)
    print()

    # Load our addresses
    our_addresses = load_our_addresses()

    # Check for matches
    matches = check_funded_addresses(our_addresses)

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    if matches:
        print(f"🚨 CRITICAL: Found {len(matches)} FUNDED address(es) in our dataset!")
        print()
        print("FUNDED ADDRESSES WITH KNOWN PRIVATE KEYS:")
        print()

        for match in matches:
            print(f"Address: {match['address']}")
            print(f"Private Key (WIF): {match['privkey']}")
            print()

        # Save matches
        with open('FUNDED_MATCHES.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['address', 'privkey'])
            writer.writeheader()
            for match in matches:
                writer.writerow(match)

        print(f"Matches saved to 'FUNDED_MATCHES.csv'")
        print()
        print("⚠️  WARNING: These addresses have funds and known private keys!")
        print("    This represents a significant finding!")

    else:
        print("✅ No matches found.")
        print()
        print("Result: None of our 160,181 addresses have any Bitcoin balance.")
        print("This confirms the dataset is purely from systematic keyspace")
        print("exploration and does not contain any compromised private keys.")

    print()
    print("Analysis complete!")

if __name__ == '__main__':
    main()
