import sys

# Analyze the privkey_address.csv file
privkeys = set()
addresses = set()
duplicate_privkeys = []
duplicate_addresses = []

with open('privkey_address.csv', 'r') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        
        parts = line.split(',')
        if len(parts) != 2:
            print(f"Line {line_num}: Invalid format - {line}")
            continue
        
        privkey, address = parts
        
        # Check for duplicates
        if privkey in privkeys:
            duplicate_privkeys.append((line_num, privkey))
        else:
            privkeys.add(privkey)
        
        if address in addresses:
            duplicate_addresses.append((line_num, address))
        else:
            addresses.add(address)

print(f"Total lines processed: {line_num}")
print(f"Unique private keys: {len(privkeys)}")
print(f"Unique addresses: {len(addresses)}")
print(f"Duplicate private keys: {len(duplicate_privkeys)}")
print(f"Duplicate addresses: {len(duplicate_addresses)}")

if duplicate_privkeys[:5]:
    print(f"\nFirst 5 duplicate privkeys: {duplicate_privkeys[:5]}")

if duplicate_addresses[:5]:
    print(f"\nFirst 5 duplicate addresses: {duplicate_addresses[:5]}")

# Check private key pattern
sample_privkey = list(privkeys)[0]
print(f"\nSample private key: {sample_privkey}")
print(f"Length: {len(sample_privkey)}")
print(f"All hex? {all(c in '0123456789abcdef' for c in sample_privkey)}")
