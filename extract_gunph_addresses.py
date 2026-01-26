#!/usr/bin/env python3
"""
Extract all 1GUNPh addresses with their private keys
"""

matches = []
current_entry = {}

print("Extracting 1GUNPh addresses from found.txt...")

with open('/root/repo/address_server/found.txt', 'r') as f:
    for line in f:
        line = line.strip()
        
        if line.startswith("PubAddress:"):
            address = line.split("PubAddress:")[1].strip()
            if address.startswith("1GUNPh"):
                current_entry = {'address': address}
        
        elif line.startswith("Priv (WIF):") and current_entry:
            wif = line.split("Priv (WIF):")[1].strip()
            current_entry['wif'] = wif
        
        elif line.startswith("Priv (HEX):") and current_entry:
            hex_key = line.split("Priv (HEX):")[1].strip()
            current_entry['hex'] = hex_key
            matches.append(current_entry)
            current_entry = {}

print(f"\nExtracted {len(matches):,} addresses with 1GUNPh prefix")

# Save to file
output_file = '/root/repo/1GUNPh_ADDRESSES.txt'
with open(output_file, 'w') as f:
    f.write("="*80 + "\n")
    f.write("ADDRESSES WITH 1GUNPh PREFIX\n")
    f.write("="*80 + "\n")
    f.write(f"\nTotal Found: {len(matches):,}\n\n")
    
    for i, match in enumerate(matches, 1):
        f.write(f"{'='*60}\n")
        f.write(f"#{i:,}\n")
        f.write(f"{'='*60}\n")
        f.write(f"Address: {match['address']}\n")
        f.write(f"WIF:     {match['wif']}\n")
        f.write(f"HEX:     {match['hex']}\n")
        f.write("\n")

print(f"\n✓ Saved all addresses to: {output_file}")

# Show first 10
print("\n" + "="*80)
print("FIRST 10 ADDRESSES WITH 1GUNPh PREFIX")
print("="*80)
for i, match in enumerate(matches[:10], 1):
    print(f"\n#{i}")
    print(f"Address: {match['address']}")
    print(f"WIF:     {match['wif']}")
    print(f"HEX:     {match['hex']}")

print("\n" + "="*80)
print(f"Total: {len(matches):,} addresses")
print(f"All saved to: {output_file}")
print("="*80)
