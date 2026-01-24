import sys
from collections import Counter

print("=" * 80)
print("Private Key Pattern Analysis")
print("=" * 80)

# Read all private keys
with open('all_private_keys_hex.txt', 'r') as f:
    keys = [line.strip() for line in f if line.strip()]

print(f"Total private keys: {len(keys)}\n")

# 1. Check for common prefixes
print("=== Prefix Analysis ===")
prefix_lengths = [2, 4, 8, 16, 32]

for length in prefix_lengths:
    prefixes = [key[:length] for key in keys]
    unique_prefixes = set(prefixes)
    counter = Counter(prefixes)
    most_common = counter.most_common(5)
    
    print(f"\nPrefix length {length} chars: {len(unique_prefixes)} unique")
    if len(unique_prefixes) < len(keys):
        print(f"  Top 5 most common:")
        for prefix, count in most_common:
            pct = (count / len(keys)) * 100
            print(f"    {prefix}{'.' * (length - len(prefix))} : {count:3d} keys ({pct:5.2f}%)")

# 2. Check for common suffixes
print("\n=== Suffix Analysis ===")
for length in [2, 4, 8, 16]:
    suffixes = [key[-length:] for key in keys]
    unique_suffixes = set(suffixes)
    counter = Counter(suffixes)
    most_common = counter.most_common(5)
    
    print(f"\nSuffix length {length} chars: {len(unique_suffixes)} unique")
    if len(unique_suffixes) < len(keys):
        print(f"  Top 5 most common:")
        for suffix, count in most_common:
            pct = (count / len(keys)) * 100
            print(f"    ...{suffix} : {count:3d} keys ({pct:5.2f}%)")

# 3. Hex character distribution
print("\n=== Hex Character Distribution ===")
all_chars = ''.join(keys)
char_counts = Counter(all_chars)

print("\nCharacter frequency:")
for char in '0123456789abcdef':
    count = char_counts[char]
    expected = len(all_chars) / 16
    pct = (count / len(all_chars)) * 100
    deviation = ((count - expected) / expected) * 100
    bar = '#' * int(pct / 0.4)
    print(f"  {char}: {count:5d} ({pct:5.2f}%) {bar:20s} {deviation:+6.2f}% vs expected")

# 4. Statistical properties
print("\n=== Statistical Properties ===")

# Convert to integers for analysis
key_ints = [int(k, 16) for k in keys]

min_key = min(key_ints)
max_key = max(key_ints)
mean_key = sum(key_ints) / len(key_ints)

print(f"Minimum: {min_key:064x}")
print(f"Maximum: {max_key:064x}")
print(f"Mean:    {int(mean_key):064x}")

# Check if keys are sequential or have pattern
sorted_keys = sorted(key_ints)
differences = [sorted_keys[i+1] - sorted_keys[i] for i in range(len(sorted_keys)-1)]

min_diff = min(differences)
max_diff = max(differences)
avg_diff = sum(differences) / len(differences)

print(f"\nKey spacing analysis:")
print(f"  Minimum difference: {min_diff}")
print(f"  Maximum difference: {max_diff}")
print(f"  Average difference: {avg_diff:.2e}")

# Check for sequential keys
sequential_count = sum(1 for d in differences if d == 1)
print(f"  Sequential pairs (diff=1): {sequential_count}")

# 5. Leading zeros
print("\n=== Leading Characteristics ===")
leading_zeros = Counter(len(key) - len(key.lstrip('0')) for key in keys)
print("Leading zeros distribution:")
for zeros, count in sorted(leading_zeros.items()):
    pct = (count / len(keys)) * 100
    print(f"  {zeros} leading zeros: {count:3d} keys ({pct:5.2f}%)")

# 6. Check for common patterns
print("\n=== Pattern Detection ===")

# Repeated characters
repeated = []
for key in keys:
    for i in range(len(key) - 3):
        if key[i] == key[i+1] == key[i+2] == key[i+3]:
            repeated.append((key, key[i:i+4]))
            break

if repeated:
    print(f"Keys with 4+ repeated characters: {len(repeated)}")
    for key, pattern in repeated[:5]:
        print(f"  {key} - contains '{pattern}'")

# Very low/high values
print("\n=== Extreme Values ===")
sorted_by_value = sorted(enumerate(key_ints, 1), key=lambda x: x[1])

print("5 Smallest values:")
for idx, val in sorted_by_value[:5]:
    print(f"  #{idx:3d}: {val:064x}")

print("\n5 Largest values:")
for idx, val in sorted_by_value[-5:]:
    print(f"  #{idx:3d}: {val:064x}")

# 7. Bit analysis
print("\n=== Bit-Level Analysis ===")
bit_counts = []
for key_int in key_ints:
    bit_count = bin(key_int).count('1')
    bit_counts.append(bit_count)

avg_bits = sum(bit_counts) / len(bit_counts)
min_bits = min(bit_counts)
max_bits = max(bit_counts)

print(f"Average '1' bits per key: {avg_bits:.2f} (expected: 128 for random 256-bit)")
print(f"Minimum '1' bits: {min_bits}")
print(f"Maximum '1' bits: {max_bits}")

# Check if any keys are very weak (low Hamming weight)
weak_keys = [(i+1, keys[i], bit_counts[i]) for i in range(len(keys)) if bit_counts[i] < 100]
if weak_keys:
    print(f"\nWeak keys (< 100 '1' bits): {len(weak_keys)}")
    for idx, key, bits in weak_keys[:5]:
        print(f"  #{idx}: {key} ({bits} bits)")

print("\n" + "=" * 80)
