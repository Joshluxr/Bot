#!/usr/bin/env python3
"""
Match Bitcoin addresses against blockchain.info API
"""
import requests
import time
import sys
from collections import defaultdict

def check_balance(address):
    """Check balance of a Bitcoin address using blockchain.info API"""
    try:
        url = f"https://blockchain.info/q/addressbalance/{address}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return int(response.text)
        return None
    except Exception as e:
        print(f"Error checking {address}: {e}", file=sys.stderr)
        return None

def main():
    input_file = "server1_full_addresses.txt"

    print(f"Loading addresses from {input_file}...")
    addresses = []
    with open(input_file, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 2:
                addresses.append((parts[0], parts[1]))

    print(f"Total addresses loaded: {len(addresses):,}")

    # Sample addresses to check (checking all 1.4M would take too long)
    # Check first 100, last 100, and 300 random samples
    import random
    random.seed(42)

    sample_indices = set()
    # First 100
    sample_indices.update(range(min(100, len(addresses))))
    # Last 100
    sample_indices.update(range(max(0, len(addresses)-100), len(addresses)))
    # Random 300
    if len(addresses) > 500:
        sample_indices.update(random.sample(range(100, len(addresses)-100), min(300, len(addresses)-200)))

    sample_addresses = [addresses[i] for i in sorted(sample_indices)]

    print(f"\nChecking {len(sample_addresses):,} sampled addresses for balances...")
    print("This will take a few minutes due to API rate limits...\n")

    funded_addresses = []
    checked = 0

    for addr, privkey in sample_addresses:
        checked += 1
        balance = check_balance(addr)

        if balance is not None and balance > 0:
            print(f"\n🚨 MATCH FOUND! 🚨")
            print(f"Address: {addr}")
            print(f"Private Key: {privkey}")
            print(f"Balance: {balance} satoshis ({balance/100000000:.8f} BTC)")
            funded_addresses.append((addr, privkey, balance))

        if checked % 10 == 0:
            print(f"Checked {checked}/{len(sample_addresses)} addresses...", end='\r')

        # Rate limiting - blockchain.info allows ~1 request per second
        time.sleep(1.1)

    print(f"\n\nResults:")
    print(f"Total addresses in file: {len(addresses):,}")
    print(f"Addresses checked: {len(sample_addresses):,}")
    print(f"Funded addresses found: {len(funded_addresses)}")

    if funded_addresses:
        print("\nFunded addresses:")
        for addr, privkey, balance in funded_addresses:
            print(f"  {addr}: {balance} satoshis ({balance/100000000:.8f} BTC) - Key: {privkey}")
    else:
        print("\nNo funded addresses found in the sample.")
        print("This is expected given Bitcoin's 2^256 keyspace security.")

if __name__ == "__main__":
    main()
