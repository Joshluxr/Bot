#!/usr/bin/env python3
"""
Analyze latest server1 file for patterns and funded matches
"""

import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

print("="*80)
print("LATEST SERVER1 FILE ANALYSIS")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Load addresses
addrs_file = Path("/root/server1_latest_addrs.txt")
addresses = set()

print("[1/4] Loading addresses...")
with open(addrs_file) as f:
    for line in f:
        if addr := line.strip():
            addresses.add(addr)

print(f"  ✓ Loaded {len(addresses):,} unique addresses\n")

# Find patterns
print("[2/4] Finding interesting patterns...")

PATTERNS = {
    "fee_prefix": r'^1[Ff][Ee][Ee]',
    "love_prefix": r'^1[Ll]ove',
    "btc_prefix": r'^1[Bb][Tt][Cc]',
    "bit_prefix": r'^1[Bb]it',
    "sat_prefix": r'^1[Ss]at',
    "coin_prefix": r'^1[Cc]oin',
    "gold_prefix": r'^1[Gg]old',
    "rich_prefix": r'^1[Rr]ich',
    "quad_1s": r'^1111',
    "quad_7s": r'^1777',
    "quad_8s": r'^1888',
    "quad_9s": r'^1999',
    "triple_same": r'^1([0-9])\1{2}',
    "sequential": r'^1(012|123|234|345|456|567|678|789)',
    "all_upper_7": r'^1[A-Z]{7,}',
    "all_upper_8": r'^1[A-Z]{8,}',
    "all_lower_7": r'^1[a-z]{7,}',
    "alternating": r'^1([A-Z][a-z]){4,}',
}

matches = defaultdict(list)

for addr in addresses:
    for name, regex in PATTERNS.items():
        if re.search(regex, addr):
            matches[name].append(addr)

print("  Pattern counts:")
for name in sorted(matches.keys()):
    print(f"    • {name:20} {len(matches[name]):>4}")

print(f"\n  Total interesting: {len(set(a for addrs in matches.values() for a in addrs)):,}\n")

# Show premium finds
print("[3/4] Premium addresses found:")

premium = ["fee_prefix", "love_prefix", "btc_prefix", "bit_prefix",
          "quad_7s", "quad_8s", "quad_9s"]

for pattern in premium:
    if pattern in matches and matches[pattern]:
        print(f"\n  {pattern.upper().replace('_', ' ')}:")
        for addr in sorted(matches[pattern]):
            print(f"    {addr}")

# Check against funded
print("\n[4/4] Checking against funded addresses...")

funded_file = Path("/root/address_matching/funded.txt")

if funded_file.exists():
    print("  Loading funded database...")
    funded = set()
    with open(funded_file) as f:
        for i, line in enumerate(f, 1):
            if addr := line.strip():
                funded.add(addr)
            if i % 10000000 == 0:
                print(f"\r    Progress: {i:,}...", end="", flush=True)

    print(f"\n  ✓ Loaded {len(funded):,} funded addresses")

    # Check matches
    funded_matches = addresses & funded

    print(f"\n  {'='*70}")
    print(f"  🎯 FUNDED MATCHES: {len(funded_matches):,}")
    print(f"  {'='*70}\n")

    if funded_matches:
        print("  💰💰💰 FUNDED ADDRESSES FOUND! 💰💰💰\n")
        for addr in sorted(funded_matches)[:20]:
            print(f"    ✓ {addr}")

        if len(funded_matches) > 20:
            print(f"    ... and {len(funded_matches) - 20:,} more\n")

        # Save
        with open("/root/repo/LATEST_SERVER1_FUNDED.txt", 'w') as f:
            f.write(f"FUNDED ADDRESSES FOUND!\n")
            f.write(f"Date: {datetime.now()}\n")
            f.write(f"Total: {len(funded_matches):,}\n\n")
            for addr in sorted(funded_matches):
                f.write(f"{addr}\n")
    else:
        print("  No funded matches (expected for random generation)")
else:
    funded_matches = set()
    print("  ⚠ Funded database not found")

# Summary report
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"File: server1_candidates.txt (latest)")
print(f"Source: tmpfiles.org/dl/21301309")
print(f"Addresses: {len(addresses):,}")
print(f"Interesting: {len(set(a for addrs in matches.values() for a in addrs)):,}")
print(f"Funded matches: {len(funded_matches):,}")

# Save report
report = f"""
Latest Server1 Analysis Report
{'='*80}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Source: tmpfiles.org/dl/21301309/server1_candidates.txt
Addresses: {len(addresses):,}
Funded matches: {len(funded_matches):,}

Premium Patterns Found:
"""

for pattern in premium:
    if pattern in matches and matches[pattern]:
        report += f"\n{pattern.upper().replace('_', ' ')} ({len(matches[pattern])} found):\n"
        for addr in sorted(matches[pattern]):
            report += f"  {addr}\n"

with open("/root/repo/LATEST_SERVER1_REPORT.txt", 'w') as f:
    f.write(report)

print("\n✓ Report saved to: /root/repo/LATEST_SERVER1_REPORT.txt")
print("="*80)
