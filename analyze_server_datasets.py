#!/usr/bin/env python3
"""
Comprehensive analysis of all three server datasets:
1. Load and combine all addresses
2. Check against funded addresses
3. Find rich wallet similarities
4. Find vanity patterns
5. Generate detailed report
"""

import csv
from collections import defaultdict

def load_server_dataset(filename, server_name):
    """Load addresses from a server dataset"""
    addresses = []
    seen = set()
    duplicates = 0

    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                addr, privkey = parts[0], parts[1]
                if addr in seen:
                    duplicates += 1
                else:
                    seen.add(addr)
                    addresses.append({
                        'address': addr,
                        'privkey': privkey,
                        'server': server_name
                    })

    return addresses, duplicates

def check_funded_matches(addresses):
    """Check addresses against funded database"""
    print("\nChecking against 55+ million funded addresses...")

    addr_lookup = {a['address']: a for a in addresses}
    matches = []
    checked = 0

    with open('/root/repo/bitcoin_results/funded_addresses_sorted.txt', 'r') as f:
        for line in f:
            funded_addr = line.strip()
            if funded_addr in addr_lookup:
                match = addr_lookup[funded_addr]
                matches.append(match)
                print(f"\n🚨 MATCH: {funded_addr} (Server: {match['server']})")

            checked += 1
            if checked % 1000000 == 0:
                print(f"  Progress: {checked:,} / 55,370,071 ({len(matches)} matches)")

    return matches

def find_rich_wallet_similarities(addresses):
    """Find addresses similar to top rich wallets"""

    # Top rich wallet prefixes (5-char)
    rich_prefixes_5 = ['1CY7f', '1Dzsf', '1Mewp', '1Q8QR', '1FeexV']

    # 4-char matches
    rich_prefixes_4 = ['1CY7', '1Dzsf', '1Mewp', '1Q8Q', '1Fee', '12c6', '1A1z', '1HLo']

    matches_5 = []
    matches_4 = []

    for addr_data in addresses:
        addr = addr_data['address']

        # 5-char matches
        for prefix in rich_prefixes_5:
            if addr.startswith(prefix):
                matches_5.append({**addr_data, 'prefix': prefix, 'similarity': 5})
                break

        # 4-char matches
        for prefix in rich_prefixes_4:
            if addr.startswith(prefix):
                matches_4.append({**addr_data, 'prefix': prefix, 'similarity': 4})
                break

    return matches_5, matches_4

def find_vanity_patterns(addresses):
    """Find vanity patterns"""

    vanity_patterns = {
        '1Fee': [], '1Gun': [], '1Nak': [], '1BTC': [],
        '1Eve': [], '1Bob': [], '1Mike': [], '1Alice': [],
        '1Love': [], '1King': [], '1Rich': [], '1Gold': [],
        '1Hodl': [], '1HODL': [], '1Satoshi': [], '1Bitcoin': [],
        '1111': [], '1234': [], '1ABC': [], '1Key': [],
        '1Hot': [], '1Big': [], '1Cool': [],
    }

    for addr_data in addresses:
        addr = addr_data['address']
        for pattern in vanity_patterns.keys():
            if addr.startswith(pattern):
                vanity_patterns[pattern].append(addr_data)

    return vanity_patterns

def main():
    print("=" * 80)
    print("COMPREHENSIVE SERVER DATASETS ANALYSIS")
    print("=" * 80)
    print()

    # Load all server datasets
    print("Loading server datasets...")

    server1, dup1 = load_server_dataset('/tmp/server1_candidates.txt', 'Server 1 (8x 4080S)')
    print(f"Server 1: {len(server1):,} unique addresses ({dup1:,} duplicates)")

    server2, dup2 = load_server_dataset('/tmp/server2_candidates.txt', 'Server 2 (4x 5090)')
    print(f"Server 2: {len(server2):,} unique addresses ({dup2:,} duplicates)")

    server4, dup4 = load_server_dataset('/tmp/server4_candidates.txt', 'Server 4 (4x 5090)')
    print(f"Server 4: {len(server4):,} unique addresses ({dup4:,} duplicates)")

    # Combine all
    all_addresses = server1 + server2 + server4
    print()
    print(f"Combined total: {len(all_addresses):,} addresses")

    # Check for cross-server duplicates
    all_addrs_set = set(a['address'] for a in all_addresses)
    cross_duplicates = len(all_addresses) - len(all_addrs_set)
    if cross_duplicates > 0:
        print(f"Cross-server duplicates: {cross_duplicates:,}")
        # Deduplicate
        unique_map = {}
        for addr_data in all_addresses:
            if addr_data['address'] not in unique_map:
                unique_map[addr_data['address']] = addr_data
        all_addresses = list(unique_map.values())
        print(f"After deduplication: {len(all_addresses):,} unique addresses")

    print()

    # Check funded addresses
    print("=" * 80)
    print("FUNDED ADDRESS CHECK")
    print("=" * 80)

    funded_matches = check_funded_matches(all_addresses)

    print()
    print(f"Result: {len(funded_matches)} funded address(es) found")

    if funded_matches:
        print("\n🚨 FUNDED ADDRESSES FOUND:")
        for match in funded_matches:
            print(f"  {match['address']} (Server: {match['server']})")
            print(f"  Key: {match['privkey']}")

        with open('SERVER_FUNDED_MATCHES.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['server', 'address', 'privkey'])
            writer.writeheader()
            for match in funded_matches:
                writer.writerow(match)
    else:
        print("✅ No funded addresses found - all addresses have zero balance")

    # Rich wallet similarities
    print()
    print("=" * 80)
    print("RICH WALLET SIMILARITIES")
    print("=" * 80)
    print()

    matches_5, matches_4 = find_rich_wallet_similarities(all_addresses)

    print(f"5-character matches: {len(matches_5)}")
    print(f"4-character matches: {len(matches_4)}")

    if matches_5:
        print("\n5-Character Matches (Very Rare):")
        for match in matches_5:
            print(f"  {match['address']} → Prefix: {match['prefix']} (Server: {match['server']})")

    if matches_4:
        print(f"\n4-Character Matches (showing first 10):")
        for match in matches_4[:10]:
            print(f"  {match['address']} → Prefix: {match['prefix']} (Server: {match['server']})")

    # Vanity patterns
    print()
    print("=" * 80)
    print("VANITY PATTERN ANALYSIS")
    print("=" * 80)
    print()

    vanity = find_vanity_patterns(all_addresses)

    found_vanity = {k: v for k, v in vanity.items() if v}
    print(f"Vanity patterns found: {len(found_vanity)}")
    print()

    for pattern, matches in sorted(found_vanity.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{pattern}: {len(matches)} address(es)")
        for match in matches[:3]:  # Show first 3
            print(f"  {match['address']} (Server: {match['server']})")

    # Save results
    print()
    print("=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    print()

    # Save rich wallet similarities
    if matches_5 or matches_4:
        all_rich = matches_5 + matches_4
        with open('server_rich_wallet_similar.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['server', 'address', 'privkey', 'prefix', 'similarity'])
            writer.writeheader()
            for match in all_rich:
                writer.writerow(match)
        print(f"Saved {len(all_rich)} rich wallet similar addresses")

    # Save vanity addresses
    if found_vanity:
        vanity_list = []
        for pattern, matches in found_vanity.items():
            for match in matches:
                vanity_list.append({
                    'pattern': pattern,
                    'server': match['server'],
                    'address': match['address'],
                    'privkey': match['privkey']
                })

        with open('server_vanity_addresses.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['pattern', 'server', 'address', 'privkey'])
            writer.writeheader()
            for item in vanity_list:
                writer.writerow(item)
        print(f"Saved {len(vanity_list)} vanity addresses")

    # Summary stats
    print()
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print()

    print(f"Total addresses analyzed: {len(all_addresses):,}")
    print(f"Funded matches: {len(funded_matches)}")
    print(f"Rich wallet 5-char matches: {len(matches_5)}")
    print(f"Rich wallet 4-char matches: {len(matches_4)}")
    print(f"Vanity patterns found: {len(found_vanity)}")
    print(f"Total vanity addresses: {sum(len(v) for v in found_vanity.values())}")

    # Server breakdown
    print()
    print("Server Breakdown:")
    for server_name in ['Server 1 (8x 4080S)', 'Server 2 (4x 5090)', 'Server 4 (4x 5090)']:
        count = sum(1 for a in all_addresses if a['server'] == server_name)
        print(f"  {server_name}: {count:,} addresses")

    print()
    print("Analysis complete!")

if __name__ == '__main__':
    main()
