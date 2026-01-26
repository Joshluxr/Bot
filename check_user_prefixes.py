#!/usr/bin/env python3
"""
Check if specific user-provided prefixes exist in candidate addresses
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

# Files to search
candidate_files = [
    "/root/repo/server1_new_all.txt",
    "/root/repo/server1_new.txt",
    "/root/repo/server1_candidates_new.txt"
]

print("=" * 80)
print("CHECKING USER-PROVIDED PREFIXES IN CANDIDATE FILES")
print("=" * 80)
print(f"\nSearching for {len(search_prefixes)} prefixes...")
print("\nPrefixes to check:")
for i, prefix in enumerate(search_prefixes, 1):
    print(f"  {i:2d}. {prefix}")
print()

found_matches = {}
total_checked = 0
files_checked = []

for filename in candidate_files:
    try:
        print(f"\nChecking {filename}...")
        file_addresses = 0
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Handle CSV format (address,privkey)
                if ',' in line:
                    address = line.split(',')[0].strip()
                else:
                    address = line
                
                total_checked += 1
                file_addresses += 1
                
                # Check each prefix
                for prefix in search_prefixes:
                    if address.startswith(prefix):
                        if prefix not in found_matches:
                            found_matches[prefix] = []
                        found_matches[prefix].append({
                            'address': address,
                            'file': filename.split('/')[-1],
                            'line': line_num
                        })
                
                # Progress indicator
                if line_num % 10000 == 0:
                    print(f"  Checked {line_num:,} addresses...")
        
        files_checked.append(filename.split('/')[-1])
        print(f"  ✓ Completed {filename.split('/')[-1]} ({file_addresses:,} addresses)")
    
    except FileNotFoundError:
        print(f"  ⚠ File not found: {filename}")
    except Exception as e:
        print(f"  ✗ Error reading {filename}: {e}")

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"\nFiles checked: {len(files_checked)}")
for f in files_checked:
    print(f"  - {f}")
print(f"\nTotal addresses checked: {total_checked:,}")
print(f"Prefixes with matches: {len(found_matches)}")
print(f"Prefixes without matches: {len(search_prefixes) - len(found_matches)}")

if found_matches:
    print("\n" + "=" * 80)
    print("✓ MATCHES FOUND")
    print("=" * 80)
    
    for prefix in sorted(found_matches.keys()):
        matches = found_matches[prefix]
        print(f"\n✓ Prefix: {prefix}")
        print(f"  Matches: {len(matches)}")
        for match in matches:
            print(f"    • {match['address']}")
            print(f"      → File: {match['file']}, Line: {match['line']}")
else:
    print("\n✗ No matches found for any of the provided prefixes")

# Summary by prefix
print("\n" + "=" * 80)
print("SUMMARY BY PREFIX")
print("=" * 80)
for i, prefix in enumerate(search_prefixes, 1):
    if prefix in found_matches:
        print(f"  {i:2d}. ✓ {prefix:12s} → {len(found_matches[prefix])} match(es) found")
    else:
        print(f"  {i:2d}. ✗ {prefix:12s} → No matches")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if found_matches:
    print(f"\n✓ Found {len(found_matches)} matching prefix(es) out of {len(search_prefixes)} requested")
    print(f"\nTotal matching addresses: {sum(len(matches) for matches in found_matches.values())}")
else:
    print(f"\n✗ None of the {len(search_prefixes)} requested prefixes were found in {total_checked:,} addresses")
    print("\nThis is expected given the vast Bitcoin address space (2^160 possible addresses)")
    print("Your candidate addresses represent a tiny random sample of that space.")

print("\n" + "=" * 80)
