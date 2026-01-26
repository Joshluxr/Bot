#!/usr/bin/env python3
"""
Analyze the 30,097 new unique addresses to find interesting patterns
"""

import csv
import re
from collections import defaultdict

def load_full_dataset(filename):
    """Load addresses with private keys"""
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def load_unique_addresses(filename):
    """Load the list of unique addresses"""
    addresses = set()
    with open(filename, 'r') as f:
        for line in f:
            addresses.add(line.strip())
    return addresses

def analyze_patterns(addresses_data):
    """Analyze various patterns in the addresses"""

    patterns = {
        'satoshi_like': [],  # Known Satoshi-like prefixes
        'nakamoto': [],  # 1Nak prefix
        'repeating_chars': [],  # AAA, BBB, 111, 222, etc
        'sequential': [],  # 123, 234, abc, etc
        'palindromes': [],  # Palindromic sequences
        'all_caps': [],  # All uppercase after 1
        'all_numbers': [],  # Heavy numeric presence
        'special_words': [],  # Bitcoin, BTC, Satoshi, etc
        'rare_prefixes': [],  # Uncommon starting patterns
    }

    satoshi_prefixes = ['1A1zP1', '12c6DSi', '1FeexV', '1Gun', '1Nak']
    special_words = ['BTC', 'Bitcoin', 'Satoshi', 'Nakamoto', 'Coin', 'Money', 'Gold', 'HODL']

    for entry in addresses_data:
        addr = entry['address']

        # Satoshi-like
        for prefix in satoshi_prefixes:
            if addr.startswith(prefix):
                patterns['satoshi_like'].append(entry)
                break

        # Nakamoto
        if addr.startswith('1Nak'):
            patterns['nakamoto'].append(entry)

        # Repeating characters (3+ in a row)
        if re.search(r'(.)\1{2,}', addr):
            patterns['repeating_chars'].append(entry)

        # Sequential patterns
        if any(seq in addr for seq in ['123', '234', '345', '456', '567', '678', '789',
                                        'abc', 'bcd', 'cde', 'def', 'ABC', 'BCD', 'CDE']):
            patterns['sequential'].append(entry)

        # Check for palindromes (4+ chars)
        for i in range(len(addr) - 3):
            substr = addr[i:i+4]
            if substr == substr[::-1]:
                patterns['palindromes'].append(entry)
                break

        # All caps (excluding the leading '1')
        if len(addr) > 1 and addr[1:].isupper() and not any(c.isdigit() for c in addr[1:10]):
            patterns['all_caps'].append(entry)

        # Heavy numeric (50%+ numbers in first 15 chars)
        check_portion = addr[:15]
        if sum(c.isdigit() for c in check_portion) >= len(check_portion) * 0.5:
            patterns['all_numbers'].append(entry)

        # Special words
        for word in special_words:
            if word in addr:
                patterns['special_words'].append(entry)
                break

    return patterns

def main():
    print("=" * 80)
    print("ANALYSIS OF 30,097 NEW UNIQUE BITCOIN ADDRESSES")
    print("=" * 80)
    print()

    # Load unique addresses
    print("Loading unique addresses...")
    unique_addrs = load_unique_addresses('unique_from_download.txt')
    print(f"Loaded {len(unique_addrs):,} unique addresses")
    print()

    # Load full dataset
    print("Loading full dataset with private keys...")
    full_data = load_full_dataset('/tmp/final_downloaded.csv')
    print(f"Loaded {len(full_data):,} total entries")
    print()

    # Filter to only the new unique addresses
    print("Filtering to new unique addresses...")
    new_data = [entry for entry in full_data if entry['address'] in unique_addrs]
    print(f"Found {len(new_data):,} new unique entries with private keys")
    print()

    # Analyze patterns
    print("Analyzing patterns in new addresses...")
    patterns = analyze_patterns(new_data)
    print()

    # Report findings
    print("=" * 80)
    print("PATTERN ANALYSIS RESULTS")
    print("=" * 80)
    print()

    for pattern_name, matches in patterns.items():
        if matches:
            print(f"{pattern_name.upper().replace('_', ' ')}: {len(matches)} addresses")

    print()
    print("=" * 80)
    print("INTERESTING FINDINGS")
    print("=" * 80)
    print()

    # Show examples of each pattern
    for pattern_name, matches in patterns.items():
        if matches and pattern_name in ['satoshi_like', 'nakamoto', 'special_words']:
            print(f"\n{pattern_name.upper().replace('_', ' ')} Examples:")
            for entry in matches[:10]:  # Show first 10
                print(f"  {entry['address']} | {entry['privkey']}")

    # Save interesting patterns
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    print()

    # Save all new addresses with patterns
    output_file = 'new_addresses_with_patterns.csv'
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['address', 'privkey', 'patterns']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for entry in new_data:
            addr = entry['address']
            pattern_list = []
            for pattern_name, matches in patterns.items():
                if any(m['address'] == addr for m in matches):
                    pattern_list.append(pattern_name)

            writer.writerow({
                'address': entry['address'],
                'privkey': entry['privkey'],
                'patterns': ','.join(pattern_list) if pattern_list else 'none'
            })

    print(f"Saved all {len(new_data):,} new addresses to '{output_file}'")

    # Save highly interesting patterns separately
    interesting = []
    for pattern_name in ['satoshi_like', 'nakamoto', 'special_words']:
        interesting.extend(patterns[pattern_name])

    if interesting:
        interesting_file = 'highly_interesting_new_addresses.csv'
        with open(interesting_file, 'w', newline='') as f:
            fieldnames = ['address', 'privkey']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in interesting:
                writer.writerow(entry)
        print(f"Saved {len(interesting)} highly interesting addresses to '{interesting_file}'")

    print()
    print("Analysis complete!")

if __name__ == '__main__':
    main()
