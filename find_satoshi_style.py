#!/usr/bin/env python3
"""
Find addresses similar to famous Bitcoin addresses:
- Satoshi's addresses (Genesis, early mining)
- Top rich list addresses
- Famous vanity addresses
"""

import re
from pathlib import Path
from collections import defaultdict

print("="*80)
print("SEARCHING FOR SATOSHI-STYLE & FAMOUS ADDRESS PATTERNS")
print("="*80)

# Famous addresses to compare against
FAMOUS_ADDRESSES = {
    "Genesis (Satoshi)": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "Bitcoin Pizza": "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF",
    "Satoshi Early": "12cbQLTFMXRnSzktFkuoG3eHoMeFtpTu3S",
    "Binance Cold": "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
    "Bitfinex 1": "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ",
    "Burn Address": "1111111111111111111114oLvT2",
}

print("\nFamous address patterns:")
for name, addr in FAMOUS_ADDRESSES.items():
    print(f"  {name:20} {addr}")

# Analyze patterns
print("\n" + "="*80)
print("PATTERN ANALYSIS")
print("="*80)

def analyze_pattern(addr):
    """Analyze what makes an address interesting"""
    patterns = []
    
    # Check characteristics
    if addr[1] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        patterns.append("starts_uppercase")
    if addr[1] in 'abcdefghijklmnopqrstuvwxyz':
        patterns.append("starts_lowercase")
    if addr[1] in '0123456789':
        patterns.append("starts_digit")
    
    # Check for repeated patterns
    if re.search(r'([A-Za-z0-9])\1{2,}', addr):
        patterns.append("has_repeats")
    
    # Check uppercase/lowercase distribution
    uppers = sum(1 for c in addr if c.isupper())
    lowers = sum(1 for c in addr if c.islower())
    if uppers > lowers * 2:
        patterns.append("mostly_uppercase")
    if lowers > uppers * 2:
        patterns.append("mostly_lowercase")
    
    return patterns

print("\nFamous address characteristics:")
for name, addr in FAMOUS_ADDRESSES.items():
    patterns = analyze_pattern(addr)
    print(f"  {name:20} {', '.join(patterns)}")

# Load all our addresses
print("\n" + "="*80)
print("SEARCHING OUR CANDIDATES")
print("="*80)

all_addresses = set()
files = [
    "/root/address_matching/candidates/server1.txt",
    "/root/address_matching/candidates/server2.txt", 
    "/root/address_matching/candidates/server4.txt",
    "/root/server1_new_addresses.txt",
    "/root/server2_new.txt",
    "/root/server4_new.txt",
    "/root/server1_latest_addrs.txt",
]

print("\nLoading addresses...")
for filepath in files:
    path = Path(filepath)
    if path.exists():
        with open(path) as f:
            for line in f:
                if line.strip():
                    addr = line.strip().split(',')[0]
                    all_addresses.add(addr)

print(f"  ✓ Loaded {len(all_addresses):,} total addresses\n")

# Search for specific patterns
print("PATTERN MATCHING")
print("="*80)

matches = defaultdict(list)

# Genesis/Satoshi style (1A1z... pattern)
print("\n1. Genesis Block Style (1A1z pattern):")
pattern = r'^1A1[a-zA-Z]'
for addr in all_addresses:
    if re.match(pattern, addr):
        matches['genesis_style'].append(addr)

if matches['genesis_style']:
    for addr in sorted(matches['genesis_style'])[:10]:
        print(f"   {addr}")
    if len(matches['genesis_style']) > 10:
        print(f"   ... and {len(matches['genesis_style']) - 10} more")
else:
    print("   None found")

# Satoshi early mining style (12c... pattern)
print("\n2. Early Satoshi Mining Style (12c pattern):")
pattern = r'^12c'
for addr in all_addresses:
    if re.match(pattern, addr):
        matches['satoshi_mining'].append(addr)

if matches['satoshi_mining']:
    for addr in sorted(matches['satoshi_mining'])[:10]:
        print(f"   {addr}")
else:
    print("   None found")

# Rich list style (starts with 3, P2SH)
print("\n3. P2SH Style (like rich list addresses - starts with 3):")
pattern = r'^3'
for addr in all_addresses:
    if re.match(pattern, addr):
        matches['p2sh'].append(addr)

if matches['p2sh']:
    for addr in sorted(matches['p2sh'])[:10]:
        print(f"   {addr}")
else:
    print("   None found (all are P2PKH starting with 1)")

# Addresses with similar structure to Genesis
print("\n4. Similar Structure to Genesis (1A1zP1...):")
# Look for pattern: 1[A-Z]1[a-z][A-Z]1
pattern = r'^1[A-Z]1[a-z][A-Z]1'
for addr in all_addresses:
    if re.match(pattern, addr):
        matches['genesis_structure'].append(addr)

if matches['genesis_structure']:
    for addr in sorted(matches['genesis_structure'])[:10]:
        print(f"   {addr}")
    if len(matches['genesis_structure']) > 10:
        print(f"   ... and {len(matches['genesis_structure']) - 10} more")
else:
    print("   None found")

# Mostly uppercase (like some rich addresses)
print("\n5. Mostly Uppercase (Professional/Exchange style):")
uppercase_addrs = []
for addr in all_addresses:
    if addr[0] == '1':
        rest = addr[1:]
        uppers = sum(1 for c in rest if c.isupper())
        total_letters = sum(1 for c in rest if c.isalpha())
        if total_letters > 10 and uppers / total_letters > 0.7:
            uppercase_addrs.append(addr)

for addr in sorted(uppercase_addrs)[:10]:
    print(f"   {addr}")
if len(uppercase_addrs) > 10:
    print(f"   ... and {len(uppercase_addrs) - 10} more")

# Mostly lowercase (rare, like some Satoshi addresses)
print("\n6. Mostly Lowercase (Early miner style):")
lowercase_addrs = []
for addr in all_addresses:
    if addr[0] == '1':
        rest = addr[1:]
        lowers = sum(1 for c in rest if c.islower())
        total_letters = sum(1 for c in rest if c.isalpha())
        if total_letters > 10 and lowers / total_letters > 0.7:
            lowercase_addrs.append(addr)

for addr in sorted(lowercase_addrs)[:10]:
    print(f"   {addr}")
if len(lowercase_addrs) > 10:
    print(f"   ... and {len(lowercase_addrs) - 10} more")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Genesis-style (1A1x):        {len(matches['genesis_style']):>6,}")
print(f"Satoshi mining (12c):        {len(matches['satoshi_mining']):>6,}")
print(f"Genesis structure:           {len(matches['genesis_structure']):>6,}")
print(f"Mostly uppercase:            {len(uppercase_addrs):>6,}")
print(f"Mostly lowercase:            {len(lowercase_addrs):>6,}")
print(f"P2SH (starts with 3):        {len(matches['p2sh']):>6,}")

# Save results
print("\nSaving results...")
output = Path("/root/repo/satoshi_style_addresses")
output.mkdir(exist_ok=True)

for category, addrs in matches.items():
    if addrs:
        with open(output / f"{category}.txt", 'w') as f:
            for addr in sorted(addrs):
                f.write(f"{addr}\n")

with open(output / "mostly_uppercase.txt", 'w') as f:
    for addr in sorted(uppercase_addrs):
        f.write(f"{addr}\n")

with open(output / "mostly_lowercase.txt", 'w') as f:
    for addr in sorted(lowercase_addrs):
        f.write(f"{addr}\n")

print(f"✓ Saved to: {output}/")
print("="*80)
