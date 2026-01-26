#!/usr/bin/env python3
"""
Check balances of interesting addresses and generate final report
"""

import csv
import subprocess
import json
import time

def get_address_balance(address):
    """Get balance using blockchain.info API"""
    try:
        result = subprocess.run(
            ['curl', '-s', f'https://blockchain.info/q/addressbalance/{address}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                balance_satoshis = int(result.stdout.strip())
                balance_btc = balance_satoshis / 100000000
                return balance_btc
            except ValueError:
                return 0
        return 0
    except Exception as e:
        print(f"  Error checking {address}: {e}")
        return 0

def main():
    print("=" * 80)
    print("CHECKING BALANCES FOR HIGHLY INTERESTING NEW ADDRESSES")
    print("=" * 80)
    print()

    # Load unique addresses
    addresses_data = []
    seen = set()

    with open('highly_interesting_new_addresses.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['address'] not in seen:
                seen.add(row['address'])
                addresses_data.append(row)

    print(f"Checking {len(addresses_data)} unique addresses...")
    print()

    results = []
    for i, entry in enumerate(addresses_data, 1):
        addr = entry['address']
        print(f"[{i}/{len(addresses_data)}] Checking {addr}...")

        balance = get_address_balance(addr)
        results.append({
            'address': addr,
            'privkey': entry['privkey'],
            'balance_btc': balance
        })

        print(f"  Balance: {balance} BTC")
        time.sleep(1)  # Rate limiting

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    for entry in results:
        print(f"{entry['address']} | {entry['balance_btc']} BTC")

    # Save results
    with open('balance_check_results.csv', 'w', newline='') as f:
        fieldnames = ['address', 'privkey', 'balance_btc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in results:
            writer.writerow(entry)

    print()
    print(f"Results saved to 'balance_check_results.csv'")

    # Check for any non-zero balances
    funded = [e for e in results if e['balance_btc'] > 0]
    if funded:
        print()
        print("=" * 80)
        print(f"ALERT: {len(funded)} ADDRESS(ES) WITH BALANCE FOUND!")
        print("=" * 80)
        for entry in funded:
            print(f"{entry['address']}: {entry['balance_btc']} BTC")
    else:
        print()
        print("All addresses have zero balance (as expected).")

if __name__ == '__main__':
    main()
