#!/usr/bin/env python3
"""
Comprehensive analysis of all_candidates_final.txt:
1. Load and parse the dataset
2. Check against 55M+ funded addresses
3. Analyze patterns and similarities
4. Generate detailed report
"""

import csv
from collections import defaultdict

def load_candidates():
    """Load all candidates from the file"""
    print("Loading candidates...")
    candidates = []
    seen_addresses = set()
    duplicates = 0

    with open('/tmp/all_candidates_final.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(',')
            if len(parts) == 2:
                address, privkey = parts
                if address in seen_addresses:
                    duplicates += 1
                else:
                    seen_addresses.add(address)
                    candidates.append({'address': address, 'privkey': privkey})

    print(f"Loaded {len(candidates):,} unique addresses")
    if duplicates > 0:
        print(f"Found {duplicates:,} duplicate addresses (removed)")

    return candidates

def check_funded_matches(candidates):
    """Check each candidate against funded addresses"""
    print("\nChecking against 55+ million funded addresses...")
    print("This will take a few minutes...")

    # Create address lookup
    candidate_addrs = {c['address']: c for c in candidates}

    matches = []
    checked = 0

    with open('/root/repo/bitcoin_results/funded_addresses_sorted.txt', 'r') as f:
        for line in f:
            funded_addr = line.strip()
            if funded_addr in candidate_addrs:
                match_data = candidate_addrs[funded_addr]
                matches.append(match_data)
                print(f"\n🚨 MATCH FOUND: {funded_addr}")
                print(f"   Private Key: {match_data['privkey']}")

            checked += 1
            if checked % 1000000 == 0:
                print(f"  Progress: {checked:,} / 55,370,071 ({len(matches)} matches)")

    print(f"\nTotal funded addresses checked: {checked:,}")
    return matches

def analyze_patterns(candidates):
    """Analyze various patterns in the candidates"""
    print("\nAnalyzing patterns...")

    patterns = {
        'starts_with_1': 0,
        'starts_with_3': 0,
        'starts_with_bc1': 0,
        'nakamoto_1Nak': [],
        'satoshi_patterns': [],
        'rich_wallet_similar': [],
        'repeating_chars': [],
        'sequential': [],
        'special_words': [],
        'all_caps': [],
    }

    # Known patterns
    satoshi_prefixes = ['1A1zP1', '12c6DSi', '1HLoD9']
    rich_prefixes = ['1CY7f', '1Dzsf', '1Mewp', '1Q8QR', '1FeexV']

    for candidate in candidates:
        addr = candidate['address']

        # Address type
        if addr.startswith('1'):
            patterns['starts_with_1'] += 1
        elif addr.startswith('3'):
            patterns['starts_with_3'] += 1
        elif addr.startswith('bc1'):
            patterns['starts_with_bc1'] += 1

        # Nakamoto
        if addr.startswith('1Nak'):
            patterns['nakamoto_1Nak'].append(candidate)

        # Satoshi patterns
        for prefix in satoshi_prefixes:
            if addr.startswith(prefix):
                patterns['satoshi_patterns'].append(candidate)
                break

        # Rich wallet similar
        for prefix in rich_prefixes:
            if addr.startswith(prefix):
                patterns['rich_wallet_similar'].append(candidate)
                break

        # Repeating chars
        if any(addr[i:i+3] == c*3 for i in range(len(addr)-2) for c in set(addr[i:i+3])):
            patterns['repeating_chars'].append(candidate)

        # Sequential
        if any(seq in addr for seq in ['123', '234', '345', '456', '567', 'abc', 'ABC']):
            patterns['sequential'].append(candidate)

        # Special words
        if any(word in addr for word in ['BTC', 'Bitcoin', 'Satoshi', 'HODL']):
            patterns['special_words'].append(candidate)

        # All caps (first 10 chars after '1')
        if len(addr) > 10 and addr[1:11].isupper():
            patterns['all_caps'].append(candidate)

    return patterns

def main():
    print("=" * 80)
    print("COMPREHENSIVE ANALYSIS: all_candidates_final.txt")
    print("=" * 80)
    print()

    # Load candidates
    candidates = load_candidates()

    # Basic stats
    print()
    print("=" * 80)
    print("BASIC STATISTICS")
    print("=" * 80)
    print(f"Total addresses: {len(candidates):,}")
    print()

    # Check for funded matches
    funded_matches = check_funded_matches(candidates)

    print()
    print("=" * 80)
    print("FUNDED ADDRESS CHECK RESULTS")
    print("=" * 80)
    print()

    if funded_matches:
        print(f"🚨 CRITICAL: Found {len(funded_matches)} FUNDED address(es)!")
        print()
        for match in funded_matches:
            print(f"Address: {match['address']}")
            print(f"Private Key: {match['privkey']}")
            print()

        # Save funded matches
        with open('FUNDED_MATCHES_CANDIDATES.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['address', 'privkey'])
            writer.writeheader()
            for match in funded_matches:
                writer.writerow(match)

        print("⚠️  Matches saved to 'FUNDED_MATCHES_CANDIDATES.csv'")
    else:
        print("✅ No funded addresses found.")
        print("All addresses have zero balance.")

    # Pattern analysis
    print()
    print("=" * 80)
    print("PATTERN ANALYSIS")
    print("=" * 80)
    print()

    patterns = analyze_patterns(candidates)

    print(f"Address Types:")
    print(f"  P2PKH (starts with '1'): {patterns['starts_with_1']:,}")
    print(f"  P2SH (starts with '3'): {patterns['starts_with_3']:,}")
    print(f"  SegWit (starts with 'bc1'): {patterns['starts_with_bc1']:,}")
    print()

    print(f"Special Patterns:")
    print(f"  Nakamoto '1Nak' prefix: {len(patterns['nakamoto_1Nak'])} addresses")
    print(f"  Satoshi-like patterns: {len(patterns['satoshi_patterns'])} addresses")
    print(f"  Rich wallet similar: {len(patterns['rich_wallet_similar'])} addresses")
    print(f"  Repeating characters: {len(patterns['repeating_chars'])} addresses")
    print(f"  Sequential patterns: {len(patterns['sequential'])} addresses")
    print(f"  Special words: {len(patterns['special_words'])} addresses")
    print(f"  All-caps style: {len(patterns['all_caps'])} addresses")
    print()

    # Show examples
    if patterns['nakamoto_1Nak']:
        print("Nakamoto '1Nak' Addresses Found:")
        for addr in patterns['nakamoto_1Nak'][:5]:
            print(f"  {addr['address']} | {addr['privkey']}")
        print()

    if patterns['satoshi_patterns']:
        print("Satoshi-Like Pattern Examples:")
        for addr in patterns['satoshi_patterns'][:5]:
            print(f"  {addr['address']} | {addr['privkey']}")
        print()

    if patterns['rich_wallet_similar']:
        print("Rich Wallet Similar Examples:")
        for addr in patterns['rich_wallet_similar'][:5]:
            print(f"  {addr['address']} | {addr['privkey']}")
        print()

    # Save all results
    print("=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    print()

    # Save interesting patterns
    interesting = []
    interesting.extend(patterns['nakamoto_1Nak'])
    interesting.extend(patterns['satoshi_patterns'])
    interesting.extend(patterns['rich_wallet_similar'])

    if interesting:
        with open('candidates_interesting_patterns.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['address', 'privkey'])
            writer.writeheader()
            # Remove duplicates
            seen = set()
            for item in interesting:
                if item['address'] not in seen:
                    writer.writerow(item)
                    seen.add(item['address'])

        print(f"Saved {len(seen)} interesting addresses to 'candidates_interesting_patterns.csv'")

    print()
    print("Analysis complete!")

if __name__ == '__main__':
    main()
