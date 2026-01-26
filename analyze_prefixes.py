import sys
from collections import Counter

print("=== Private Key Prefix Analysis ===\n")

privkeys = []
with open('privkey_address.csv', 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) == 2:
            privkeys.append(parts[0])

# Remove duplicates
unique_privkeys = list(set(privkeys))
print(f"Total unique private keys: {len(unique_privkeys)}")

# Analyze different prefix lengths
prefix_lengths = [4, 8, 16, 32, 48]

for length in prefix_lengths:
    prefixes = [pk[:length] for pk in unique_privkeys]
    unique_prefixes = set(prefixes)
    print(f"\nPrefix length {length} chars: {len(unique_prefixes)} unique prefixes")
    
    # Show most common prefixes
    counter = Counter(prefixes)
    top_5 = counter.most_common(5)
    for prefix, count in top_5:
        print(f"  {prefix}... : {count} keys")

# Full analysis - find the common prefix
print("\n=== Finding Maximum Common Prefix ===")

# Sort to make comparison easier
sorted_keys = sorted(unique_privkeys)
first_key = sorted_keys[0]
last_key = sorted_keys[-1]

common_prefix = ""
for i in range(min(len(first_key), len(last_key))):
    if first_key[i] == last_key[i]:
        common_prefix += first_key[i]
    else:
        break

print(f"\nMaximum common prefix (all keys): {common_prefix}")
print(f"Length: {len(common_prefix)} characters")

# Variable portion
variable_start = len(common_prefix)
print(f"\nVariable portion starts at position: {variable_start}")

# Sample keys showing the pattern
print(f"\nSample keys:")
for i, key in enumerate(sorted_keys[:5]):
    print(f"{i+1}. {key[:variable_start]}|{key[variable_start:]}")
print("...")
for i, key in enumerate(sorted_keys[-5:]):
    print(f"{len(sorted_keys)-4+i}. {key[:variable_start]}|{key[variable_start:]}")

# Analyze the variable portion
print(f"\n=== Variable Portion Analysis ===")
variable_parts = [pk[variable_start:] for pk in unique_privkeys]
unique_variable = set(variable_parts)
print(f"Unique variable portions: {len(unique_variable)}")

# Check if variable portions have patterns
var_lengths = set(len(v) for v in variable_parts)
print(f"Variable portion lengths: {var_lengths}")

# Hex digit distribution in variable portion
from collections import defaultdict
hex_dist = defaultdict(int)
for var in variable_parts:
    for char in var:
        hex_dist[char] += 1

print(f"\nHex digit distribution in variable portion:")
for digit in sorted(hex_dist.keys()):
    count = hex_dist[digit]
    pct = (count / sum(hex_dist.values())) * 100
    bar = '#' * int(pct / 2)
    print(f"  {digit}: {count:6d} ({pct:5.2f}%) {bar}")
