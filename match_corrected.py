#!/usr/bin/env python3
"""
CORRECTED Bitcoin Address Matching Script
Properly handles CSV format (address,private_key)
"""

from pathlib import Path
from datetime import datetime

print("="*80)
print("Bitcoin Address Matching System (CORRECTED)")
print("="*80)

# Setup
work_dir = Path("/root/address_matching")
results_dir = work_dir / "results"
results_dir.mkdir(exist_ok=True)

# Load candidates - EXTRACT ONLY ADDRESSES (before comma)
print("\n[1/3] Loading candidate addresses (extracting from CSV format)...")
candidates = {}
all_candidates = set()

servers = ["server1", "server2", "server4"]

for server_name in servers:
    candidate_file = work_dir / "candidates" / f"{server_name}.txt"

    server_addresses = set()
    with open(candidate_file) as f:
        for line in f:
            line = line.strip()
            if line:
                # Extract address (part before comma)
                address = line.split(',')[0] if ',' in line else line
                server_addresses.add(address)

    candidates[server_name] = server_addresses
    all_candidates.update(server_addresses)

    print(f"  ✓ {server_name}: {len(server_addresses):,} addresses")

print(f"\n  Total unique candidate addresses: {len(all_candidates):,}")

# Load funded database
print("\n[2/3] Loading funded addresses database...")
funded_file = work_dir / "funded.txt"

funded = set()
with open(funded_file) as f:
    for i, line in enumerate(f, 1):
        if addr := line.strip():
            funded.add(addr)
        if i % 1000000 == 0:
            print(f"\r    Loaded {i:,} addresses...", end="", flush=True)

print(f"\n  ✓ Total funded addresses: {len(funded):,}")

# Match
print("\n[3/3] Matching addresses...")
all_matches = all_candidates & funded

print(f"\n  {'='*70}")
print(f"  🎯 MATCHES FOUND: {len(all_matches):,}")
print(f"  {'='*70}")

# Per-server analysis
server_results = {}
for server_name, server_addrs in candidates.items():
    matches = server_addrs & funded
    server_results[server_name] = matches
    print(f"  • {server_name}: {len(matches):,} matches")

# Save results
print("\nSaving results...")

# All matches
matches_file = results_dir / "matches_corrected.txt"
with open(matches_file, 'w') as f:
    for addr in sorted(all_matches):
        f.write(f"{addr}\n")

# Per-server matches
for server_name, matches in server_results.items():
    server_file = results_dir / f"{server_name}_matches_corrected.txt"
    with open(server_file, 'w') as f:
        for addr in sorted(matches):
            f.write(f"{addr}\n")

# Generate detailed report
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

report = f"""
{'='*80}
BITCOIN ADDRESS MATCHING REPORT (CORRECTED)
{'='*80}
Generated: {timestamp}

FORMAT FIX APPLIED:
  ✓ Candidate files contained CSV format: address,private_key
  ✓ Script now extracts only address portion (before comma)
  ✓ Proper comparison against funded addresses database

INPUT STATISTICS
{'='*80}
Candidate Sources:
  • server1:     {len(candidates['server1']):>10,} addresses
  • server2:     {len(candidates['server2']):>10,} addresses
  • server4:     {len(candidates['server4']):>10,} addresses
  • Total Unique: {len(all_candidates):>9,} addresses

Funded Database:
  • Total Addresses: {len(funded):>8,} addresses

MATCHING RESULTS
{'='*80}
🎯 TOTAL MATCHES: {len(all_matches):,}

Per-Server Breakdown:
"""

for server_name, matches in server_results.items():
    count = len(matches)
    total = len(candidates[server_name])
    percentage = (count / total * 100) if total > 0 else 0
    report += f"  • {server_name:10} {count:>6,} matches ({percentage:.4f}% of candidates)\n"

if all_matches:
    report += f"\n{'='*80}\nMATCHED ADDRESSES\n{'='*80}\n"

    for i, addr in enumerate(sorted(all_matches)[:50], 1):
        report += f"{i:3d}. {addr}\n"

    if len(all_matches) > 50:
        report += f"\n... and {len(all_matches) - 50:,} more matches\n"

    report += f"\n{'='*80}\nIMPORTANT: MATCHES FOUND!\n{'='*80}\n"
    report += "The addresses above have been used on the Bitcoin network.\n"
    report += "Full list saved to: matches_corrected.txt\n"
else:
    report += f"\n{'='*80}\nNO MATCHES\n{'='*80}\n"
    report += "None of the candidate addresses have been funded on the Bitcoin network.\n"

report += f"""
OUTPUT FILES
{'='*80}
All Matches:      {results_dir / 'matches_corrected.txt'} ({len(all_matches)} addresses)
Server 1 Matches: {results_dir / 'server1_matches_corrected.txt'} ({len(server_results['server1'])} addresses)
Server 2 Matches: {results_dir / 'server2_matches_corrected.txt'} ({len(server_results['server2'])} addresses)
Server 4 Matches: {results_dir / 'server4_matches_corrected.txt'} ({len(server_results['server4'])} addresses)

Report File: {results_dir / 'REPORT_CORRECTED.txt'}
{'='*80}
"""

# Print and save report
print(report)

report_file = results_dir / "REPORT_CORRECTED.txt"
with open(report_file, 'w') as f:
    f.write(report)

print(f"✓ Full report saved to: {report_file}")
print(f"✓ Results directory: {results_dir}/")
print("="*80)
