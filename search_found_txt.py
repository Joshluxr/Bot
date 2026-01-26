#!/usr/bin/env python3
"""
Search found.txt for user-provided prefixes
"""

# User-provided prefixes to search for
search_prefixes = [
    "1ANkDM",
    "1Ki3WTEE",
    "1MtUMTq",
    "1CY7fyk",
    "1HLvaT",
    "198aMn",
    "15Z5YJa",
    "1AYLzYN",
    "178E8tYZ",
    "138EMxw",
    "13n67sF",
    "1BeouDc",
    "1ARWCRE",
    "1Btud1p",
    "1VeMPNg",
    "1812yXz",
    "18eY9o",
    "18F838",
    "1FvUkW8",
    "17GGGH",
    "1GUNPh",
    "1AenFm",
    "1NY5KheH",
    "3281T7i"
]

print("=" * 80)
print("SEARCHING found.txt FOR USER-PROVIDED PREFIXES")
print("=" * 80)
print(f"\nSearching for {len(search_prefixes)} prefixes in found.txt...")
print()

found_matches = {}
total_addresses = 0

with open('/root/repo/address_server/found.txt', 'r') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        
        # Extract address from "PubAddress: " lines
        if line.startswith("PubAddress:"):
            address = line.split("PubAddress:")[1].strip()
            total_addresses += 1
            
            # Check each prefix
            for prefix in search_prefixes:
                if address.startswith(prefix):
                    if prefix not in found_matches:
                        found_matches[prefix] = []
                    found_matches[prefix].append({
                        'address': address,
                        'line': line_num
                    })
            
            # Progress indicator
            if total_addresses % 10000 == 0:
                print(f"Checked {total_addresses:,} addresses...")

print(f"\nTotal addresses checked: {total_addresses:,}")

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"\nPrefixes with matches: {len(found_matches)}")
print(f"Prefixes without matches: {len(search_prefixes) - len(found_matches)}")

if found_matches:
    print("\n" + "=" * 80)
    print("✓✓✓ MATCHES FOUND! ✓✓✓")
    print("=" * 80)
    
    total_match_count = sum(len(matches) for matches in found_matches.values())
    print(f"\nTotal matching addresses: {total_match_count}")
    
    for prefix in sorted(found_matches.keys()):
        matches = found_matches[prefix]
        print(f"\n{'='*60}")
        print(f"✓ Prefix: {prefix}")
        print(f"  Matches: {len(matches)}")
        print(f"{'='*60}")
        for i, match in enumerate(matches[:20], 1):  # Show first 20
            print(f"  {i:3d}. {match['address']}")
            print(f"       Line {match['line']:,}")
        if len(matches) > 20:
            print(f"  ... and {len(matches) - 20} more")
else:
    print("\n✗ No matches found for any of the provided prefixes")

# Summary by prefix
print("\n" + "=" * 80)
print("SUMMARY BY PREFIX")
print("=" * 80)
for i, prefix in enumerate(search_prefixes, 1):
    if prefix in found_matches:
        print(f"  {i:2d}. ✓✓✓ {prefix:12s} → {len(found_matches[prefix]):,} match(es) FOUND!")
    else:
        print(f"  {i:2d}. ✗   {prefix:12s} → No matches")

print("\n" + "=" * 80)
