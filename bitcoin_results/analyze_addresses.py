import re
from collections import Counter

print("=== Bitcoin Address Analysis ===\n")

addresses = []
with open('privkey_address.csv', 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) == 2 and parts[1]:
            addresses.append(parts[1])

# Remove duplicates
unique_addresses = list(set(addresses))
print(f"Total unique addresses: {len(unique_addresses)}")

# Pattern analysis
print("\n=== Pattern Detection ===")

# 1. Repeated characters
repeated_patterns = []
for addr in unique_addresses:
    # Look for 3+ repeated characters
    if re.search(r'(.)\1{2,}', addr):
        matches = re.findall(r'(.)\1{2,}', addr)
        repeated_patterns.append((addr, matches))

print(f"\nAddresses with 3+ repeated characters: {len(repeated_patterns)}")
if repeated_patterns[:10]:
    print("First 10 examples:")
    for addr, patterns in repeated_patterns[:10]:
        print(f"  {addr} - repeats: {patterns}")

# 2. Addresses with many zeros
zero_heavy = [(addr, addr.count('0')) for addr in unique_addresses if addr.count('0') >= 5]
zero_heavy.sort(key=lambda x: x[1], reverse=True)
print(f"\nAddresses with 5+ zeros: {len(zero_heavy)}")
if zero_heavy[:5]:
    print("Top 5:")
    for addr, count in zero_heavy[:5]:
        print(f"  {addr} ({count} zeros)")

# 3. Addresses with many ones (1s)
one_heavy = [(addr, addr.count('1')) for addr in unique_addresses if addr.count('1') >= 8]
one_heavy.sort(key=lambda x: x[1], reverse=True)
print(f"\nAddresses with 8+ ones: {len(one_heavy)}")
if one_heavy[:5]:
    print("Top 5:")
    for addr, count in one_heavy[:5]:
        print(f"  {addr} ({count} ones)")

# 4. Palindromic patterns
palindromic = []
for addr in unique_addresses:
    # Check substrings for palindromes (length 4+)
    for i in range(len(addr) - 3):
        for length in range(4, min(8, len(addr) - i + 1)):
            substr = addr[i:i+length]
            if substr == substr[::-1] and len(substr) >= 4:
                palindromic.append((addr, substr))
                break

print(f"\nAddresses with palindromic substrings (4+ chars): {len(set(a for a,s in palindromic))}")
if palindromic[:5]:
    print("First 5 examples:")
    for addr, pattern in palindromic[:5]:
        print(f"  {addr} - contains: {pattern}")

# 5. Sequential patterns
sequential = []
for addr in unique_addresses:
    # Look for sequences like 123, 234, abc, etc
    if re.search(r'(012|123|234|345|456|567|678|789|abc|bcd|cde|def)', addr, re.IGNORECASE):
        matches = re.findall(r'(012|123|234|345|456|567|678|789|abc|bcd|cde|def)', addr, re.IGNORECASE)
        sequential.append((addr, matches))

print(f"\nAddresses with sequential patterns: {len(sequential)}")
if sequential[:5]:
    print("First 5 examples:")
    for addr, patterns in sequential[:5]:
        print(f"  {addr} - sequences: {patterns}")

# 6. Character distribution anomalies
print("\n=== Character Distribution ===")

# Count all characters (excluding leading '1')
char_counts = Counter()
for addr in unique_addresses:
    for char in addr[1:]:  # Skip the leading '1'
        char_counts[char] += 1

total_chars = sum(char_counts.values())
print("\nCharacter frequency (excluding leading '1'):")
for char in sorted(char_counts.keys()):
    count = char_counts[char]
    pct = (count / total_chars) * 100
    bar = '#' * int(pct / 0.5)
    print(f"  {char}: {count:6d} ({pct:5.2f}%) {bar}")

# 7. Find "interesting" addresses
print("\n=== Potentially Interesting Addresses ===")

interesting = []

# Criteria: Many repeated chars, or unusual patterns
for addr in unique_addresses:
    score = 0
    reasons = []
    
    # High repeat count
    if addr.count('1') >= 10:
        score += 5
        reasons.append(f"{addr.count('1')} ones")
    
    # Many zeros
    if addr.count('0') >= 6:
        score += 3
        reasons.append(f"{addr.count('0')} zeros")
    
    # Repeated character sequences
    repeats = len(re.findall(r'(.)\1{2,}', addr))
    if repeats >= 2:
        score += repeats
        reasons.append(f"{repeats} repeat sequences")
    
    # Low character diversity
    unique_chars = len(set(addr))
    if unique_chars <= 15:
        score += (20 - unique_chars) / 2
        reasons.append(f"only {unique_chars} unique chars")
    
    if score >= 5:
        interesting.append((addr, score, reasons))

interesting.sort(key=lambda x: x[1], reverse=True)

print(f"\nTop 20 most 'interesting' addresses (unusual patterns):")
for i, (addr, score, reasons) in enumerate(interesting[:20], 1):
    print(f"{i:2d}. {addr} (score: {score:.1f})")
    print(f"    → {', '.join(reasons)}")

# 8. Addresses starting with unusual prefixes (not common '1')
print("\n=== Prefix Analysis ===")
prefix_counts = Counter(addr[:2] for addr in unique_addresses)
print("\nMost common 2-char prefixes:")
for prefix, count in prefix_counts.most_common(10):
    pct = (count / len(unique_addresses)) * 100
    print(f"  {prefix}: {count:5d} ({pct:5.2f}%)")
