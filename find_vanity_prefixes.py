#!/usr/bin/env python3
"""
Search for vanity prefixes in all datasets
"""

import csv
from collections import defaultdict

def load_addresses_from_csv(filename):
    """Load addresses from CSV with header"""
    addresses = []
    with open(filename, 'r') as f:
        next(f)  # Skip header
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                addresses.append({'address': parts[0], 'privkey': parts[1]})
    return addresses

def load_addresses_from_txt(filename):
    """Load addresses from txt without header"""
    addresses = []
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                addresses.append({'address': parts[0], 'privkey': parts[1]})
    return addresses

def find_vanity_patterns(addresses):
    """Find addresses with vanity patterns"""

    # Define vanity patterns to search for
    vanity_patterns = {
        # Common words
        '1Fee': [],
        '1Gun': [],
        '1Love': [],
        '1God': [],
        '1War': [],
        '1Win': [],
        '1King': [],
        '1Boss': [],
        '1Rich': [],
        '1Cash': [],
        '1Gold': [],
        '1Moon': [],
        '1Star': [],
        '1Sun': [],
        '1Fire': [],
        '1Ice': [],
        '1Hero': [],
        '1Luck': [],
        '1Baby': [],
        '1Cool': [],
        '1Hot': [],
        '1Fast': [],
        '1Slow': [],
        '1Big': [],
        '1Small': [],

        # Names
        '1Alice': [],
        '1Bob': [],
        '1Eve': [],
        '1John': [],
        '1Mary': [],
        '1Mike': [],
        '1Nick': [],
        '1Sam': [],
        '1Tom': [],
        '1Will': [],

        # Bitcoin related
        '1Bitcoin': [],
        '1BTC': [],
        '1Satoshi': [],
        '1Nakamoto': [],
        '1Nak': [],
        '1Crypto': [],
        '1Coin': [],
        '1Block': [],
        '1Chain': [],
        '1Hodl': [],
        '1HODL': [],
        '1Hash': [],
        '1Miner': [],
        '1Mining': [],

        # Numbers/Patterns
        '1111': [],
        '1234': [],
        '1ABC': [],
        '1XXX': [],
        '1ZZZ': [],

        # Other
        '1Puzzle': [],
        '1Magic': [],
        '1Power': [],
        '1Money': [],
        '1Bank': [],
        '1Wallet': [],
        '1Key': [],
        '1Secret': [],
        '1Diamond': [],
        '1Tiger': [],
        '1Dragon': [],
        '1Eagle': [],
        '1Wolf': [],
        '1Bear': [],
        '1Lion': [],
    }

    for addr_data in addresses:
        addr = addr_data['address']

        for pattern in vanity_patterns.keys():
            if addr.startswith(pattern):
                vanity_patterns[pattern].append(addr_data)

    return vanity_patterns

def main():
    print("=" * 80)
    print("VANITY PREFIX SEARCH - ALL DATASETS")
    print("=" * 80)
    print()

    # Load both datasets
    print("Loading datasets...")

    dataset1 = load_addresses_from_csv('./final_complete.csv')
    print(f"Dataset 1 (final_complete.csv): {len(dataset1):,} addresses")

    dataset2 = load_addresses_from_txt('/tmp/all_candidates_final.txt')
    print(f"Dataset 2 (all_candidates_final.txt): {len(dataset2):,} addresses")

    # Combine for comprehensive search
    all_addresses = dataset1 + dataset2
    print(f"Combined total: {len(all_addresses):,} addresses")
    print()

    # Find vanity patterns
    print("Searching for vanity patterns...")
    vanity_results = find_vanity_patterns(all_addresses)

    print()
    print("=" * 80)
    print("VANITY PREFIX RESULTS")
    print("=" * 80)
    print()

    # Sort by count
    sorted_results = sorted(vanity_results.items(), key=lambda x: len(x[1]), reverse=True)

    # Display results
    found_count = 0
    for pattern, matches in sorted_results:
        if matches:
            found_count += 1
            print(f"{pattern}: {len(matches)} address(es)")

    print()
    print(f"Total vanity patterns found: {found_count}")
    print()

    # Show detailed results for interesting patterns
    print("=" * 80)
    print("DETAILED RESULTS FOR KEY PATTERNS")
    print("=" * 80)
    print()

    key_patterns = ['1Fee', '1Gun', '1Nak', '1BTC', '1Satoshi', '1Bitcoin',
                    '1Love', '1King', '1Rich', '1Gold', '1Moon', '1Luck']

    for pattern in key_patterns:
        if vanity_results[pattern]:
            print(f"\n{pattern} ({len(vanity_results[pattern])} found):")
            print("-" * 60)
            for match in vanity_results[pattern][:10]:  # Show first 10
                print(f"  {match['address']}")
                print(f"  Key: {match['privkey']}")
                print()

    # Save all vanity addresses to CSV
    print("=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    print()

    all_vanity = []
    for pattern, matches in sorted_results:
        if matches:
            for match in matches:
                all_vanity.append({
                    'pattern': pattern,
                    'address': match['address'],
                    'privkey': match['privkey']
                })

    if all_vanity:
        with open('all_vanity_addresses.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['pattern', 'address', 'privkey'])
            writer.writeheader()
            for item in all_vanity:
                writer.writerow(item)

        print(f"Saved {len(all_vanity)} vanity addresses to 'all_vanity_addresses.csv'")

    # Summary statistics
    print()
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print()

    print(f"Total addresses searched: {len(all_addresses):,}")
    print(f"Vanity patterns detected: {found_count}")
    print(f"Total vanity addresses: {len(all_vanity)}")
    print(f"Percentage with vanity: {(len(all_vanity)/len(all_addresses)*100):.3f}%")

    print()
    print("Analysis complete!")

if __name__ == '__main__':
    main()
