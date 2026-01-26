#!/usr/bin/env python3
"""
Analyze new server1 file for interesting addresses and funded matches
"""

import re
from pathlib import Path
from collections import defaultdict

print("="*80)
print("NEW SERVER1 FILE ANALYSIS")
print("="*80)

# Load new addresses
new_addrs_file = Path("/root/server1_new_addresses.txt")
new_addresses = set()

print("\n[1/4] Loading new server1 addresses...")
with open(new_addrs_file) as f:
    for line in f:
        if addr := line.strip():
            new_addresses.add(addr)

print(f"  ✓ Loaded {len(new_addresses):,} addresses")

# Check for interesting patterns
print("\n[2/4] Checking for interesting patterns...")

INTERESTING_PATTERNS = {
    "fee": r'^1[Ff]ee',
    "love": r'^1[Ll]ove',
    "btc": r'^1[Bb][Tt][Cc]',
    "bit": r'^1[Bb]it',
    "1111": r'^1111',
    "7777": r'^17777',
    "sequential": r'^1(012|123|234|345|456|567|678|789)',
    "all_upper_6": r'^1[A-Z]{6,}',
    "repeated": r'^1([0-9])\1{3,}',
}

pattern_matches = defaultdict(list)

for addr in new_addresses:
    for pattern_name, regex in INTERESTING_PATTERNS.items():
        if re.match(regex, addr):
            pattern_matches[pattern_name].append(addr)

print("\n  Interesting patterns found:")
for pattern, matches in sorted(pattern_matches.items()):
    print(f"    • {pattern:15} {len(matches):>4} addresses")

# Show samples
print("\n[3/4] Sample interesting addresses:")
for pattern in ["fee", "love", "btc", "1111", "sequential"]:
    if pattern in pattern_matches:
        print(f"\n  {pattern.upper()} pattern:")
        for addr in sorted(pattern_matches[pattern])[:5]:
            print(f"    {addr}")

# Match against funded database
print("\n[4/4] Checking against funded addresses...")
funded_file = Path("/root/address_matching/funded.txt")

if funded_file.exists():
    print("  Loading funded addresses (this may take a moment)...")
    funded = set()
    with open(funded_file) as f:
        for i, line in enumerate(f, 1):
            if addr := line.strip():
                funded.add(addr)
            if i % 5000000 == 0:
                print(f"\r    Loaded {i:,} addresses...", end="", flush=True)

    print(f"\n  ✓ Loaded {len(funded):,} funded addresses")

    # Check for matches
    matches = new_addresses & funded

    print(f"\n  {'='*70}")
    print(f"  🎯 FUNDED MATCHES: {len(matches)}")
    print(f"  {'='*70}")

    if matches:
        print("\n  MATCHED ADDRESSES (FUNDED!):")
        for addr in sorted(matches)[:20]:
            print(f"    ✓ {addr}")

        if len(matches) > 20:
            print(f"    ... and {len(matches) - 20} more")

        # Save matches
        with open("/root/repo/new_server1_funded_matches.txt", 'w') as f:
            for addr in sorted(matches):
                f.write(f"{addr}\n")
        print(f"\n  ✓ Saved to: /root/repo/new_server1_funded_matches.txt")
    else:
        print("\n  No funded addresses found.")
else:
    print("  ⚠ Funded database not found, skipping match check")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"New server1 addresses:     {len(new_addresses):,}")
print(f"Interesting patterns:      {sum(len(v) for v in pattern_matches.values()):,}")
if funded_file.exists():
    print(f"Funded matches:            {len(matches):,}")
print("="*80)
