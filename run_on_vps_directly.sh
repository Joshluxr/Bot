#!/bin/bash
# This script can be copied and pasted directly into the VPS terminal
# Or run via: curl -sSL <url> | bash

set -e

echo "================================================"
echo "Bitcoin Address Matching - Quick Start"
echo "================================================"
echo "VPS: $(hostname -I | awk '{print $1}')"
echo "Started: $(date)"
echo ""

# Create Python script inline
cat > /root/match_addresses.py << 'PYTHON_SCRIPT_EOF'
#!/usr/bin/env python3
import urllib.request
import gzip
from pathlib import Path
from datetime import datetime

print("="*80)
print("Bitcoin Address Matching System")
print("="*80)

# Setup
work_dir = Path("/root/address_matching")
work_dir.mkdir(exist_ok=True)
(work_dir / "candidates").mkdir(exist_ok=True)
(work_dir / "results").mkdir(exist_ok=True)

# Download candidates
print("\n[1/4] Downloading candidate files...")
candidates = set()
servers = {
    "server1": ("https://tmpfiles.org/dl/21294684/server1_candidates.txt", 153690),
    "server2": ("https://tmpfiles.org/dl/21294681/server2_candidates.txt", 51274),
    "server4": ("https://tmpfiles.org/dl/21294682/server4_candidates.txt", 57958),
}

for name, (url, expected) in servers.items():
    print(f"  Downloading {name}...")
    dest = work_dir / "candidates" / f"{name}.txt"
    urllib.request.urlretrieve(url, dest)
    with open(dest) as f:
        addrs = set(line.strip() for line in f if line.strip())
    candidates.update(addrs)
    print(f"    ✓ {name}: {len(addrs):,} addresses (expected ~{expected:,})")

print(f"\n  Total unique candidates: {len(candidates):,}")

# Download funded database
print("\n[2/4] Downloading funded addresses database...")
db_gz = work_dir / "funded.txt.gz"
db_txt = work_dir / "funded.txt"

print("  Downloading (this may take several minutes)...")
urllib.request.urlretrieve(
    "http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz",
    db_gz
)

print("  Extracting...")
with gzip.open(db_gz, 'rb') as f_in:
    with open(db_txt, 'wb') as f_out:
        f_out.write(f_in.read())

print("  Loading funded addresses...")
funded = set()
with open(db_txt) as f:
    for i, line in enumerate(f, 1):
        if addr := line.strip():
            funded.add(addr)
        if i % 1000000 == 0:
            print(f"\r    Loaded {i:,} addresses...", end="", flush=True)
print(f"\n  ✓ Total funded: {len(funded):,}")

# Match
print("\n[3/4] Matching addresses...")
matches = candidates & funded
print(f"  ✓ MATCHES FOUND: {len(matches):,}")

# Save results
print("\n[4/4] Saving results...")
results_file = work_dir / "results" / "matches.txt"
with open(results_file, 'w') as f:
    for addr in sorted(matches):
        f.write(f"{addr}\n")

# Report
report = f"""
{"="*80}
MATCHING COMPLETE
{"="*80}
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Statistics:
  • Candidates checked:  {len(candidates):>10,}
  • Funded addresses:    {len(funded):>10,}
  • MATCHES FOUND:       {len(matches):>10,}

Results saved to: {results_file}

"""

if matches:
    report += "First 20 matches:\n"
    for i, addr in enumerate(sorted(matches)[:20], 1):
        report += f"  {i:2d}. {addr}\n"
    if len(matches) > 20:
        report += f"  ... and {len(matches) - 20:,} more\n"

report += "="*80 + "\n"

print(report)

# Save report
with open(work_dir / "results" / "REPORT.txt", 'w') as f:
    f.write(report)

print(f"Report saved to: {work_dir / 'results' / 'REPORT.txt'}")
print(f"All data in: {work_dir}/")
PYTHON_SCRIPT_EOF

# Make executable
chmod +x /root/match_addresses.py

# Run it
echo "Starting matching process..."
echo ""
python3 /root/match_addresses.py 2>&1 | tee /root/matching_output.log

echo ""
echo "================================================"
echo "Complete! Log saved to: /root/matching_output.log"
echo "================================================"
