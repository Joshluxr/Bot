#!/usr/bin/env python3
"""
Comprehensive analysis of all new candidate files
- Checks against funded addresses database
- Finds interesting patterns
- Generates detailed report
"""

import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

print("="*80)
print("COMPREHENSIVE NEW FILES ANALYSIS")
print("="*80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# File sources
NEW_FILES = {
    "server1_new": {
        "path": "/root/server1_new_check.txt",
        "expected": 8349,
        "source": "tmpfiles.org/dl/21298764"
    },
    "server2_new": {
        "path": "/root/server2_new.txt",
        "expected": 78740,
        "source": "tmpfiles.org/dl/21300385"
    },
    "server4_new": {
        "path": "/root/server4_new.txt",
        "expected": 75272,
        "source": "tmpfiles.org/dl/21300381"
    }
}

# Load all addresses
all_new_addresses = set()
per_server_addresses = {}

print("[1/5] Loading all new candidate files...")
print("-"*80)

for server_name, info in NEW_FILES.items():
    filepath = Path(info['path'])
    if not filepath.exists():
        print(f"  ⚠ {server_name}: File not found")
        continue

    addresses = set()
    with open(filepath) as f:
        for line in f:
            if line.strip():
                # Extract address (before comma)
                addr = line.strip().split(',')[0]
                addresses.add(addr)

    per_server_addresses[server_name] = addresses
    all_new_addresses.update(addresses)

    print(f"  ✓ {server_name:15} {len(addresses):>8,} addresses")

print(f"\n  Total unique addresses: {len(all_new_addresses):,}")

# Find interesting patterns
print("\n[2/5] Analyzing for interesting patterns...")
print("-"*80)

INTERESTING_PATTERNS = {
    "fee_prefix": r'^1[Ff][Ee][Ee]',
    "love_prefix": r'^1[Ll]ove',
    "btc_prefix": r'^1[Bb][Tt][Cc]',
    "bit_prefix": r'^1[Bb]it',
    "sat_prefix": r'^1[Ss]at',
    "quad_1s": r'^1111',
    "quad_7s": r'^17777',
    "quad_8s": r'^18888',
    "sequential_123": r'^1123',
    "sequential_234": r'^1234',
    "sequential_345": r'^1345',
    "sequential_456": r'^1456',
    "sequential_567": r'^1567',
    "sequential_678": r'^1678',
    "sequential_789": r'^1789',
    "all_upper_7": r'^1[A-Z]{7,}',
    "all_upper_8": r'^1[A-Z]{8,}',
    "all_lower_7": r'^1[a-z]{7,}',
    "alternating": r'^1([A-Z][a-z]){4,}',
    "repeated_char": r'^1([0-9])\1{3,}',
    "contains_gold": r'[Gg]old',
    "contains_rich": r'[Rr]ich',
    "contains_coin": r'[Cc]oin',
    "contains_punk": r'[Pp]unk',
}

pattern_matches = defaultdict(list)

for addr in all_new_addresses:
    for pattern_name, regex in INTERESTING_PATTERNS.items():
        if re.search(regex, addr):
            pattern_matches[pattern_name].append(addr)

print("\n  Interesting patterns found:")
total_interesting = 0
for pattern, matches in sorted(pattern_matches.items(), key=lambda x: len(x[1]), reverse=True):
    if matches:
        print(f"    • {pattern:20} {len(matches):>6,} addresses")
        total_interesting += len(set(matches))

print(f"\n  Total interesting: {len(set(addr for addrs in pattern_matches.values() for addr in addrs)):,}")

# Check against funded database
print("\n[3/5] Checking against funded addresses database...")
print("-"*80)

funded_file = Path("/root/address_matching/funded.txt")

if funded_file.exists():
    print("  Loading funded addresses (55.4M addresses)...")
    funded = set()
    with open(funded_file) as f:
        for i, line in enumerate(f, 1):
            if addr := line.strip():
                funded.add(addr)
            if i % 10000000 == 0:
                print(f"\r    Progress: {i:,} addresses loaded...", end="", flush=True)

    print(f"\n  ✓ Loaded {len(funded):,} funded addresses")

    # Check for matches
    print("\n  Checking for funded matches...")
    all_matches = all_new_addresses & funded

    print(f"\n  {'='*70}")
    print(f"  🎯 TOTAL FUNDED MATCHES: {len(all_matches):,}")
    print(f"  {'='*70}")

    if all_matches:
        print("\n  ✓✓✓ FUNDED ADDRESSES FOUND! ✓✓✓")
        print("  " + "="*70)
        for addr in sorted(all_matches)[:50]:
            print(f"    💰 {addr}")

        if len(all_matches) > 50:
            print(f"    ... and {len(all_matches) - 50:,} more!")

        # Save matches
        matches_file = Path("/root/repo/FUNDED_MATCHES_FOUND.txt")
        with open(matches_file, 'w') as f:
            f.write(f"FUNDED BITCOIN ADDRESSES FOUND!\n")
            f.write(f"{'='*80}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total matches: {len(all_matches):,}\n\n")
            for addr in sorted(all_matches):
                f.write(f"{addr}\n")

        print(f"\n  ✓ Saved to: {matches_file}")

        # Check per server
        print("\n  Per-server funded matches:")
        for server_name, addresses in per_server_addresses.items():
            server_matches = addresses & funded
            if server_matches:
                print(f"    💰 {server_name:15} {len(server_matches):>6,} FUNDED!")
            else:
                print(f"       {server_name:15} {len(server_matches):>6,}")
    else:
        print("\n  No funded matches found.")
        print("  (This is expected for random address generation)")
else:
    print("  ⚠ Funded database not found")
    all_matches = set()

# Display premium patterns
print("\n[4/5] Premium Pattern Highlights")
print("-"*80)

premium_patterns = ["fee_prefix", "love_prefix", "btc_prefix", "bit_prefix",
                   "quad_1s", "quad_7s", "quad_8s"]

for pattern in premium_patterns:
    if pattern in pattern_matches and pattern_matches[pattern]:
        print(f"\n  {pattern.upper().replace('_', ' ')}:")
        for addr in sorted(pattern_matches[pattern])[:10]:
            print(f"    {addr}")
        if len(pattern_matches[pattern]) > 10:
            print(f"    ... and {len(pattern_matches[pattern]) - 10} more")

# Generate summary report
print("\n[5/5] Generating Summary Report")
print("-"*80)

report = f"""
{'='*80}
NEW CANDIDATE FILES - COMPREHENSIVE ANALYSIS REPORT
{'='*80}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

INPUT FILES
{'='*80}
"""

for server_name, info in NEW_FILES.items():
    if server_name in per_server_addresses:
        count = len(per_server_addresses[server_name])
        report += f"  • {server_name:15} {count:>8,} addresses (source: {info['source']})\n"

report += f"""
  • Total Unique:    {len(all_new_addresses):>8,} addresses

FUNDED ADDRESS MATCHING
{'='*80}
Database checked:     55,401,177 funded Bitcoin addresses
New addresses:        {len(all_new_addresses):,}
FUNDED MATCHES:       {len(all_matches):,}

"""

if all_matches:
    report += f"""
🎉🎉🎉 FUNDED ADDRESSES FOUND! 🎉🎉🎉
{'='*80}

This is a SIGNIFICANT finding! These addresses currently have or previously
had Bitcoin transactions.

Matched Addresses:
"""
    for addr in sorted(all_matches)[:100]:
        report += f"  💰 {addr}\n"

    if len(all_matches) > 100:
        report += f"\n  ... and {len(all_matches) - 100:,} more matches!\n"
else:
    report += """No funded matches found. This is expected for random address generation
where the probability of finding a funded address is astronomically low."""

report += f"""

INTERESTING PATTERNS FOUND
{'='*80}
"""

for pattern, matches in sorted(pattern_matches.items(), key=lambda x: len(x[1]), reverse=True):
    if matches:
        report += f"  • {pattern:25} {len(matches):>6,} addresses\n"

report += f"""

PREMIUM VANITY ADDRESSES
{'='*80}
"""

if "fee_prefix" in pattern_matches and pattern_matches["fee_prefix"]:
    report += f"\nFEE PREFIX ({len(pattern_matches['fee_prefix'])} found):\n"
    for addr in sorted(pattern_matches["fee_prefix"]):
        report += f"  {addr}\n"

if "love_prefix" in pattern_matches and pattern_matches["love_prefix"]:
    report += f"\nLOVE PREFIX ({len(pattern_matches['love_prefix'])} found):\n"
    for addr in sorted(pattern_matches["love_prefix"]):
        report += f"  {addr}\n"

if "btc_prefix" in pattern_matches and pattern_matches["btc_prefix"]:
    report += f"\nBTC PREFIX ({len(pattern_matches['btc_prefix'])} found):\n"
    for addr in sorted(pattern_matches["btc_prefix"])[:20]:
        report += f"  {addr}\n"
    if len(pattern_matches["btc_prefix"]) > 20:
        report += f"  ... and {len(pattern_matches['btc_prefix']) - 20} more\n"

report += f"""

{'='*80}
SUMMARY
{'='*80}
Total new addresses analyzed: {len(all_new_addresses):,}
Interesting patterns:         {len(set(addr for addrs in pattern_matches.values() for addr in addrs)):,}
Funded matches:               {len(all_matches):,}

Report saved: /root/repo/ALL_NEW_FILES_REPORT.txt
{'='*80}
"""

# Save report
report_file = Path("/root/repo/ALL_NEW_FILES_REPORT.txt")
with open(report_file, 'w') as f:
    f.write(report)

print(report)
print(f"✓ Report saved to: {report_file}")

if all_matches:
    print("\n" + "!"*80)
    print("!!! ATTENTION: FUNDED ADDRESSES WERE FOUND !!!")
    print("!"*80)
    print(f"Total funded: {len(all_matches):,}")
    print(f"Saved to: /root/repo/FUNDED_MATCHES_FOUND.txt")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
