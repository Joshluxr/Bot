#!/usr/bin/env python3
"""
Find addresses in our dataset that have similar prefixes to:
1. Top 100 richest Bitcoin addresses
2. Known Satoshi Nakamoto addresses
3. Famous Bitcoin puzzle addresses
"""

import csv
from collections import defaultdict

# Top 100 richest Bitcoin addresses
TOP_RICH_ADDRESSES = [
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
    "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6",
    "bc1ql49ydapnjafl5t2cp9zqpjwe6pdgmxy98859v2",
    "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF",  # Famous puzzle address!
    "1Ay8vMC7R1UbyCCZRVULMV7iQpHSAbguJP",
    "1LdRcdxfbSnmCYYNdeYpUnztiYzVfBEQeC",
    "1AC4fMwgY8j9onSbXEWeH6Zan8QGMSdmtA",
    "1LruNZjwamWJXThX2Y8C2d47QqhAkkc5os",
    "3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW6a",
    "3FHNBLobJnbCTFTVakh5TXmEneyf5PT61B",
    "12ib7dApVFvg82TXKycWBNpN8kFyiAN1dr",
    "3FuhQLprN9s9MR3bZzR5da7mw75fuahsaU",
    "12tkqA9xSoowkzoERHMWNKsTey55YEBqkv",
    "3EMVdMehEq5SFipQ5UfbsfMsH223sSz9A9",
    "3FsDiWdG76meMpdCLbVV4dUXhrFyaLrtxL",
    "39eYrpgAgDhp4tTjrSb1ppZ5kdAc1ikBYw",
    "1N7jWmv63mkMdsYzbNUVHbEYDQfcq1u8Yp",
    "15cHRgVrGKz7qp2JL2N5mkB2MCFGLcnHxv",
    "12XqeqZRVkBDgmPLVY4ZC6Y4ruUUEug8Fx",
    "1PJiGp2yDLvUgqeBsuZVCBADArNsk6XEiw",
    "17rm2dvb439dZqyMe2d4D6AQJSgg6yeNRn",
    "1PeizMg76Cf96nUQrYg8xuoZWLQozU5zGW",
    "34HpHYiyQwg69gFmCq2BGHjF1DZnZnBeBP",
    "38rFtDdFpXc4y6XPbSnNd2UvveEt5Xms2E",
    "1GR9qNz7zgtaW5HwwVpEJWMnGWhsbsieCG",
    "3FM9vDYsN2iuMPKWjAcqgyahdwdrUxhbJ3",
    "1CNtkWbb4grh8xtb8mhoZ6armNE9PHgzA8",
    "39gUvGynQ7Re3i15G3J2gp9DEB9LnLFPMN",
    "1F34duy2eeMz5mSrvFepVzy7Y1rBsnAyWC",
    "1ANkDML9LtVv1E1EF7cwPFEkSv6Bpojwyt",
    "1Q8QR5k32hexiMQnRgkJ6fmmjn5fMWhdv9",
    "162bzZT2hJfv5Gm3ZmWfWfHJjCtMD6rHhw",
    "1Ki3WTEEqTLPNsN5cGTsMkL2sJ4m5mdCXT",
    "1DzsfLRDfbmQM99xm59au2SrTY3YmciBSB",
    "1GUfWdZQoo2pQ4BKHsiegxuZPnheY5ueTm",
    "12HnxiXEeKUVjQRbMVTytsGWnzHd5LdGCt",
    "17uULjz9moeLyjXHoKNwDRgKzf8ahY3Jia",
    "18qNs1yBGGKR8RyErnEF5kegbNUgPfixhS",
    "1DP3VYwN6ozHXDDaETbvNFLd86CAXfaewi",
    "1NhJGUJu8rrTwPS4vopsdTqqcK4nAwdLwJ",
    "1MtUMTqtdrpT6Rar5fgWoyrzAevatssej5",
    "1MewpRkpcbFdqamPPYc1bXa9AJ189Succy",
    "1H2MXWiSniAgg7ykdXEzPHL6oTH1ic4kP",
    "1DcT5Wij5tfb3oVViF8mA8p4WrG98ahZPT",
    "1CY7fykRLWXeSbKB885Kr4KjQxmDdvW923",
    "3GPAWK5aUB5Ve9akvTzZgp69USjgbhFbay",
    "34PhCF947JMQtCn7FD1J3Xd3c2VSxAwda8",
    "1P9fAFAsSLRmMu2P7wZ5CXDPRfLSWTy9N8",
    "17MWdxfjPYP2PYhdy885QtihfbW181r1rn",
    "3KNViZo8uJwnLyxrWed5gRavbPZibEdAq3",
    "1HLvaTs3zR3oev9ya7Pzp3GB9Gqfg6XYJT",
    "33eU1zeB2S4x3p4ccSsnAChXcGJgtMrMtZ",
    "167ZWTT8n6s4ya8cGjqNNQjDwDGY31vmHg",
    "3NWndKFmvV6cJ6ENgXVeaDTo3mBfAvr27H",
    "32qqF3w9W96S6br5x3cR75fgtFZwshjh4X",
]

# Known Satoshi and famous addresses
SATOSHI_ADDRESSES = [
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Genesis block
    "12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX",  # Early Satoshi
    "1HLoD9E4SDFFPDiYfNYnkBLQ85Y51J3Zb1",  # Early mining
]

def calculate_prefix_similarity(addr1, addr2, max_len=10):
    """Calculate how many starting characters match"""
    matches = 0
    for i in range(min(len(addr1), len(addr2), max_len)):
        if addr1[i] == addr2[i]:
            matches += 1
        else:
            break
    return matches

def load_our_addresses():
    """Load all addresses from our dataset"""
    addresses = []
    with open('./final_complete.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            addresses.append(row)
    return addresses

def find_similar_addresses(our_addresses, target_addresses, target_name, min_match=3):
    """Find addresses in our dataset similar to target addresses"""
    matches = []

    for our_addr_data in our_addresses:
        our_addr = our_addr_data['address']

        for target_addr in target_addresses:
            # Skip bc1 addresses (SegWit) - we only have legacy addresses
            if target_addr.startswith('bc1') or target_addr.startswith('3'):
                continue

            similarity = calculate_prefix_similarity(our_addr, target_addr)

            if similarity >= min_match:
                matches.append({
                    'our_address': our_addr,
                    'privkey': our_addr_data['privkey'],
                    'target_address': target_addr,
                    'target_type': target_name,
                    'similarity_score': similarity,
                    'matching_prefix': our_addr[:similarity]
                })

    return matches

def main():
    print("=" * 80)
    print("FINDING ADDRESSES SIMILAR TO RICH WALLETS AND SATOSHI")
    print("=" * 80)
    print()

    # Load our addresses
    print("Loading our complete dataset...")
    our_addresses = load_our_addresses()
    print(f"Loaded {len(our_addresses):,} addresses")
    print()

    # Filter to only legacy addresses (starting with '1')
    legacy_rich = [addr for addr in TOP_RICH_ADDRESSES if addr.startswith('1')]
    print(f"Top rich addresses (legacy format): {len(legacy_rich)}")
    print(f"Satoshi addresses: {len(SATOSHI_ADDRESSES)}")
    print()

    # Find similarities
    print("Analyzing similarities...")
    print()

    # Check for different similarity levels
    results = {
        'rich_wallets': {},
        'satoshi': {}
    }

    for min_match in [6, 5, 4, 3]:
        print(f"Checking for {min_match}+ character matches...")

        rich_matches = find_similar_addresses(our_addresses, legacy_rich, "Rich Wallet", min_match)
        satoshi_matches = find_similar_addresses(our_addresses, SATOSHI_ADDRESSES, "Satoshi", min_match)

        results['rich_wallets'][min_match] = rich_matches
        results['satoshi'][min_match] = satoshi_matches

        print(f"  Rich wallet matches: {len(rich_matches)}")
        print(f"  Satoshi matches: {len(satoshi_matches)}")
        print()

    # Display top matches
    print("=" * 80)
    print("TOP SIMILARITIES TO RICH WALLETS")
    print("=" * 80)
    print()

    # Get best matches (6+ chars first, then 5, etc.)
    best_rich_matches = []
    for min_match in [6, 5, 4]:
        if results['rich_wallets'][min_match]:
            best_rich_matches.extend(results['rich_wallets'][min_match])
            break

    if best_rich_matches:
        # Sort by similarity score
        best_rich_matches.sort(key=lambda x: x['similarity_score'], reverse=True)

        for match in best_rich_matches[:20]:  # Top 20
            print(f"Our Address:    {match['our_address']}")
            print(f"Rich Address:   {match['target_address']}")
            print(f"Match:          '{match['matching_prefix']}' ({match['similarity_score']} characters)")
            print(f"Private Key:    {match['privkey']}")
            print()
    else:
        print("No significant matches found with rich wallet addresses.")
        print()

    print("=" * 80)
    print("TOP SIMILARITIES TO SATOSHI ADDRESSES")
    print("=" * 80)
    print()

    # Get best Satoshi matches
    best_satoshi_matches = []
    for min_match in [6, 5, 4]:
        if results['satoshi'][min_match]:
            best_satoshi_matches.extend(results['satoshi'][min_match])
            break

    if best_satoshi_matches:
        best_satoshi_matches.sort(key=lambda x: x['similarity_score'], reverse=True)

        for match in best_satoshi_matches[:20]:  # Top 20
            print(f"Our Address:      {match['our_address']}")
            print(f"Satoshi Address:  {match['target_address']}")
            print(f"Match:            '{match['matching_prefix']}' ({match['similarity_score']} characters)")
            print(f"Private Key:      {match['privkey']}")
            print()
    else:
        print("No significant matches found with Satoshi addresses.")
        print()

    # Save all matches to CSV
    print("=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    print()

    all_matches = []
    for category in results.values():
        for matches_list in category.values():
            all_matches.extend(matches_list)

    # Remove duplicates
    unique_matches = {}
    for match in all_matches:
        key = (match['our_address'], match['target_address'])
        if key not in unique_matches or unique_matches[key]['similarity_score'] < match['similarity_score']:
            unique_matches[key] = match

    matches_list = list(unique_matches.values())
    matches_list.sort(key=lambda x: x['similarity_score'], reverse=True)

    if matches_list:
        with open('similar_to_rich_addresses.csv', 'w', newline='') as f:
            fieldnames = ['our_address', 'privkey', 'target_address', 'target_type', 'similarity_score', 'matching_prefix']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for match in matches_list:
                writer.writerow(match)

        print(f"Saved {len(matches_list)} similar addresses to 'similar_to_rich_addresses.csv'")

        # Stats
        score_distribution = defaultdict(int)
        for match in matches_list:
            score_distribution[match['similarity_score']] += 1

        print()
        print("Similarity Distribution:")
        for score in sorted(score_distribution.keys(), reverse=True):
            print(f"  {score} characters: {score_distribution[score]} addresses")

    print()
    print("Analysis complete!")

if __name__ == '__main__':
    main()
