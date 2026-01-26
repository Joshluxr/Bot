#!/usr/bin/env python3
"""
Find interesting/unique Bitcoin addresses from candidate files
Looks for patterns similar to famous addresses, vanity addresses, etc.
"""

import re
from collections import defaultdict
from pathlib import Path

# Famous Bitcoin address patterns to look for
INTERESTING_PATTERNS = {
    "repeated_chars": r'^1([0-9])\1{3,}',  # 11111, 12222, etc
    "sequential": r'^1(012|123|234|345|456|567|678|789|abc|bcd|cde)',
    "fee_pattern": r'^1[Ff]ee',
    "love_pattern": r'^1[Ll]ove',
    "btc_pattern": r'^1[Bb][Tt][Cc]',
    "bit_pattern": r'^1[Bb]it',
    "sat_pattern": r'^1[Ss]at',
    "all_upper": r'^1[A-Z]{6,}',
    "all_lower": r'^1[a-z]{6,}',
    "all_digits": r'^1[0-9]{6,}',
    "alternating": r'^1([A-Z][a-z]){3,}',
}

def analyze_address(address):
    """Analyze address for interesting patterns"""
    patterns_found = []

    for pattern_name, regex in INTERESTING_PATTERNS.items():
        if re.match(regex, address):
            patterns_found.append(pattern_name)

    # Additional interesting features
    if address[1:5] == address[5:9]:  # Repeated sequence
        patterns_found.append("repeated_sequence")

    # Check for interesting substrings
    addr_lower = address.lower()
    interesting_words = ['fee', 'love', 'btc', 'bit', 'sat', 'rich', 'coin', 'punk', 'rare', 'gold']
    for word in interesting_words:
        if word in addr_lower:
            patterns_found.append(f"contains_{word}")

    return patterns_found

def main():
    print("="*80)
    print("INTERESTING ADDRESS FINDER")
    print("="*80)
    print()

    # Check VPS candidates
    vps_path = Path("/root/address_matching/candidates")
    local_path = Path("/root/repo")

    candidates_dir = vps_path if vps_path.exists() else local_path

    all_addresses = []
    interesting_addresses = defaultdict(list)

    # Load all candidate files
    print("[1/3] Loading candidate addresses...")

    candidate_files = [
        "server1.txt",
        "server2.txt",
        "server4.txt"
    ]

    for filename in candidate_files:
        filepath = candidates_dir / filename
        if not filepath.exists():
            print(f"  ⚠ {filename} not found, skipping")
            continue

        with open(filepath) as f:
            for line in f:
                if line.strip():
                    # Extract address (before comma if CSV)
                    address = line.strip().split(',')[0]
                    all_addresses.append(address)

    print(f"  ✓ Loaded {len(all_addresses):,} addresses")

    # Analyze for interesting patterns
    print("\n[2/3] Analyzing for interesting patterns...")

    for address in all_addresses:
        patterns = analyze_address(address)
        if patterns:
            for pattern in patterns:
                interesting_addresses[pattern].append(address)

    print(f"  ✓ Found {sum(len(v) for v in interesting_addresses.values()):,} interesting addresses")

    # Display results
    print("\n[3/3] Interesting Addresses by Pattern")
    print("="*80)

    # Sort by most interesting (most patterns)
    address_scores = defaultdict(list)
    for pattern, addresses in interesting_addresses.items():
        for addr in addresses:
            address_scores[addr].append(pattern)

    # Get top addresses by score
    top_addresses = sorted(address_scores.items(),
                          key=lambda x: len(x[1]),
                          reverse=True)[:100]

    if top_addresses:
        print("\n🏆 TOP INTERESTING ADDRESSES (by number of patterns matched)")
        print("-"*80)
        for i, (address, patterns) in enumerate(top_addresses[:30], 1):
            print(f"{i:2d}. {address}")
            print(f"    Patterns: {', '.join(patterns)}")
            print()

    # Display by category
    print("\n📊 ADDRESSES BY CATEGORY")
    print("="*80)

    categories = [
        ("repeated_chars", "Repeated Characters (1111, 1222, etc)"),
        ("sequential", "Sequential Patterns"),
        ("contains_fee", "Contains 'Fee'"),
        ("contains_love", "Contains 'Love'"),
        ("contains_btc", "Contains 'BTC'"),
        ("contains_bit", "Contains 'Bit'"),
        ("all_upper", "6+ Uppercase Letters"),
        ("all_lower", "6+ Lowercase Letters"),
        ("all_digits", "6+ Consecutive Digits"),
    ]

    for pattern_key, description in categories:
        if pattern_key in interesting_addresses:
            addresses = interesting_addresses[pattern_key][:20]
            print(f"\n{description}: {len(interesting_addresses[pattern_key]):,} found")
            print("-"*80)
            for addr in addresses:
                print(f"  {addr}")

    # Save results
    print("\n" + "="*80)
    print("SAVING RESULTS")
    print("="*80)

    output_dir = Path("/root/repo/interesting_addresses")
    output_dir.mkdir(exist_ok=True)

    # Save all interesting addresses
    with open(output_dir / "all_interesting.txt", 'w') as f:
        for address, patterns in sorted(top_addresses):
            f.write(f"{address}\t{','.join(patterns)}\n")

    # Save by category
    for pattern, addresses in interesting_addresses.items():
        filename = output_dir / f"{pattern}.txt"
        with open(filename, 'w') as f:
            for addr in sorted(addresses):
                f.write(f"{addr}\n")

    print(f"  ✓ Saved to: {output_dir}/")
    print(f"  ✓ Categories: {len(interesting_addresses)}")
    print(f"  ✓ Total interesting addresses: {len(top_addresses)}")

    # Compare with famous addresses
    print("\n" + "="*80)
    print("COMPARISON WITH FAMOUS ADDRESS PATTERNS")
    print("="*80)

    famous_examples = {
        "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF": "Bitcoin Pizza (10k BTC)",
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa": "Genesis Block (Satoshi)",
        "1111111111111111111114oLvT2": "Burn Address",
        "1LoveYo7VFgDWmJDvjgHk4r1qkVPvNd7X": "Vanity 'Love'",
        "1BitcoinEaterAddressDontSendf59kuE": "Bitcoin Eater",
    }

    print("\nFamous Address Patterns:")
    print("-"*80)
    for addr, desc in famous_examples.items():
        print(f"  {addr}")
        print(f"    Description: {desc}")
        patterns = analyze_address(addr)
        if patterns:
            print(f"    Patterns: {', '.join(patterns)}")
        print()

    print("\nYour closest matches:")
    print("-"*80)

    # Find addresses starting with 1Fee, 1Love, etc
    special_prefixes = ['1Fee', '1fee', '1Love', '1love', '1Bit', '1bit', '1111', '1BTC', '1Btc']

    for prefix in special_prefixes:
        matches = [a for a in all_addresses if a.startswith(prefix)]
        if matches:
            print(f"\n{prefix}* pattern: {len(matches)} found")
            for addr in matches[:10]:
                print(f"  {addr}")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
