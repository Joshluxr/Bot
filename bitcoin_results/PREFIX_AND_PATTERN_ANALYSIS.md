# Private Key Prefix & Address Pattern Analysis
## privkey_address.csv Deep Dive

**Date:** 2026-01-24
**Analyst:** Terry (Terragon Labs)
**Dataset:** 27,208 unique private keys & addresses

---

## Executive Summary

### Key Findings

1. **ONLY 1 UNIQUE PREFIX** across all 27,208 private keys
2. **51-character common prefix** (out of 64 total)
3. **Highly systematic generation** - NOT random sampling
4. **Only 13 variable characters** per key
5. **Addresses appear normal** - no unusual patterns indicating funded wallets

---

## Private Key Prefix Analysis

### Prefix Uniqueness

| Prefix Length | Unique Prefixes | Coverage |
|---------------|-----------------|----------|
| 4 characters  | **1** | 100% identical |
| 8 characters  | **1** | 100% identical |
| 16 characters | **1** | 100% identical |
| 32 characters | **1** | 100% identical |
| 48 characters | **1** | 100% identical |

**Result:** ALL 27,208 keys share the SAME prefix for the first 51 characters!

### Maximum Common Prefix

```
Prefix (51 chars): 44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2
Variable (13 chars): [varies by key]
```

**Structure:**
- **Fixed portion:** 51 characters (79.7% of key)
- **Variable portion:** 13 characters (20.3% of key)
- **Total key length:** 64 characters (256 bits)

### Sample Keys Showing Pattern

```
Fixed Prefix                                           |Variable Portion
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|0ecb540b32a00
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|0ecb640b32a00
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|0ecb840b32a00
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|0ecbc40b32a00
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|0ecbf40b32a00
...
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|1ecb040b32a00
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|1ecb140b32a00
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|1ecb240b32a00
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|1ecb340b32a00
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2|1ecb440b32a00
```

---

## Variable Portion Analysis

### Statistics

- **Unique variable portions:** 27,208 (all unique)
- **Variable portion length:** 13 characters (consistent)
- **Character set:** Hexadecimal (0-9, a-f)

### Hex Digit Distribution in Variable Portion

| Digit | Count | Percentage | Distribution |
|-------|-------|------------|--------------|
| **0** | 90,619 | **25.62%** | ############# (HIGHLY OVERREPRESENTED) |
| 1 | 32,191 | 9.10% | #### |
| 2 | 34,138 | 9.65% | #### |
| 3 | 33,890 | 9.58% | #### |
| 4 | 33,846 | 9.57% | #### |
| 5 | 7,155 | 2.02% | # |
| 6 | 6,930 | 1.96% | |
| 7 | 6,834 | 1.93% | |
| 8 | 6,709 | 1.90% | |
| 9 | 6,580 | 1.86% | |
| a | 33,772 | 9.55% | #### |
| b | 34,108 | 9.64% | #### |
| c | 6,755 | 1.91% | |
| d | 6,388 | 1.81% | |
| e | 7,096 | 2.01% | # |
| f | 6,693 | 1.89% | |

**Expected:** ~6.25% per digit (uniform distribution)

**Anomalies:**
- **'0' is 4x overrepresented** (25.62% vs 6.25% expected)
- Digits 1-4, a-b are ~1.5x overrepresented
- Digits 5-9, c-f are ~3x underrepresented

**Interpretation:**
- **NOT random generation** (would have uniform distribution)
- Likely **vanity search** targeting addresses with specific patterns
- The '0' bias suggests filtering by some bloom filter or pattern matcher
- Could indicate GPU-generated keys with specific jump function

---

## Address Pattern Analysis

### Overall Statistics

- **Total unique addresses:** 27,209 (one more than keys - duplicate compressed/uncompressed)
- **All start with '1'** (P2PKH format)
- **Character distribution:** Nearly uniform (expected for valid Bitcoin addresses)

### Pattern Detection Results

#### 1. Repeated Characters (3+ consecutive)

**Found:** 258 addresses (0.95%)

**Examples:**
```
1LJCWfS1EiMPssssaxTCYeyCAwdkfRf75o  - 4 consecutive 's'
1ftTXGRbzHqBUfCuFSY4Ty9SSSwK1ABLw  - 3 consecutive 'S'
1NRQeM6itirg7FGz5g1QkVTTThjiA6EvCF - 3 consecutive 'T'
14hzXqXgNi4TZbxSSSZ9QxwvXP4DQAzogn - 3 consecutive 'S'
19LCvjVEhMptsdxMmauUdMMMqoQ1SmUdLt - 3 consecutive 'M'
```

**Normal Expectation:** ~1-2% of random addresses have 3+ repeats (this is within normal range)

#### 2. Addresses with Many Zeros

**Found:** 0 addresses with 5+ zeros

**Conclusion:** No unusual '0' concentration in addresses (unlike private keys)

#### 3. Addresses with Many Ones

**Found:** 0 addresses with 8+ ones

**Conclusion:** No unusual '1' patterns

#### 4. Palindromic Substrings (4+ characters)

**Found:** 472 addresses (1.73%)

**Examples:**
```
1LJCWfS1EiMPssssaxTCYeyCAwdkfRf75o - contains: ssss
1DuuDDcPU9z3coyApwymwHP1qpbSjecYBx - contains: DuuD
17NtDy4A4KBeCEStE3UU3atJSxg9P5QZr5 - contains: 3UU3
19moX6rr6aJJ6PwmCX9CdSLW7zrRfofQRo - contains: 6rr6
1MMdPzii6sd2nKuKnRgofvhkhpYSTDWqm7 - contains: nKuKn
```

**Normal Expectation:** ~1-3% (this is within normal range)

#### 5. Sequential Patterns (123, abc, etc.)

**Found:** 184 addresses (0.68%)

**Examples:**
```
1McKkARpGJbabCDXER6pnRNYwSyvtpYauq - sequences: abC
1Dt997FwuXAt369kr1b4wS3MWCDez49xoE - sequences: CDe
1L73WungqSNSCUBKcDe1n8TotHmxtAGqXj - sequences: cDe
1Jxxrvf1uMNg5n6n32zebcd4jxFDj3QrTo - sequences: bcd
14g4habCzKF7RpykNxnYbfxA14aWpFc12w - sequences: abC
```

**Normal Expectation:** ~0.5-1% (this is within normal range)

#### 6. "Interesting" Addresses

**Criteria:** High score based on:
- Many repeated characters
- Many zeros or ones
- Low character diversity
- Multiple repeat sequences

**Result:** 0 addresses scored above threshold (5.0)

**Interpretation:** No addresses show the hallmarks of vanity generation or unusual patterns

### Character Distribution in Addresses

**All characters (excluding leading '1'):** Nearly perfect uniform distribution

| Range | Average % | Expected % | Status |
|-------|-----------|------------|--------|
| 0-9 | 1.76% | 1.72% | ✓ Normal |
| A-Z | 1.75% | 1.72% | ✓ Normal |
| a-z | 1.67% | 1.72% | ✓ Normal |

**Conclusion:** Address character distribution is statistically normal - no anomalies

### Prefix Distribution (2-character)

**Top 10 most common:**

| Prefix | Count | Percentage |
|--------|-------|------------|
| 1A | 1,268 | 4.66% |
| 16 | 1,262 | 4.64% |
| 18 | 1,217 | 4.47% |
| 1E | 1,215 | 4.47% |
| 1J | 1,209 | 4.44% |
| 1K | 1,208 | 4.44% |
| 1D | 1,194 | 4.39% |
| 1C | 1,188 | 4.37% |
| 17 | 1,187 | 4.36% |
| 1M | 1,183 | 4.35% |

**Expected:** ~4.35% per prefix (assuming 23 possible second characters: 2-9, A-Z)

**Conclusion:** Distribution matches expectations - no targeting of specific prefixes

---

## Interpretation & Conclusions

### What Generated These Keys?

Based on the analysis, this dataset was **definitely NOT randomly generated**. Evidence:

1. **Single 51-character prefix** across ALL keys
   - Probability of this occurring randomly: ~0% (essentially impossible)
   - Clear evidence of systematic generation starting from a specific base key

2. **Non-uniform hex distribution in variable portion**
   - '0' digit appears 4x more than expected
   - Other digits show bias patterns
   - Indicates filtering/selection process

3. **Only 13 variable characters**
   - Searching a narrow keyspace: 16^13 ≈ 2^52 possible keys
   - Out of Bitcoin's full 2^256 keyspace
   - **Reduced search space by a factor of 2^204** (incomprehensibly huge reduction)

### Most Likely Generation Method

**Hypothesis:** VanitySearch or similar GPU-based bloom filter search

**Supporting Evidence:**
1. Common 51-character prefix suggests starting point/base key
2. 13-character variable portion = jump function increments
3. '0' bias in variable portion = bloom filter false positive pattern
4. All addresses yielded zero funded matches = bloom filter false positives
5. GPU-friendly keyspace (systematic increments)

**Alternative Hypothesis:** Targeted range search for puzzle solving

**Less likely because:**
- Bitcoin puzzles typically use consecutive keys or power-of-2 boundaries
- This dataset shows non-uniform hex distribution (not simple increments)
- Puzzle searches would show different patterns

### Why Zero Funded Addresses?

The **51-character common prefix** means all keys fall within a **minuscule fraction** of Bitcoin's keyspace:

**Effective search space:**
- Variable portion: 13 hex characters = 2^52 possibilities
- Bitcoin's full keyspace: 2^256
- **Coverage:** 2^52 / 2^256 = 2^-204 = 0.00000000000000000000000000000000000000000000000000000000006%

**Probability of hitting a funded address in this range:**
- Funded addresses: ~55 million ≈ 2^26
- Total keyspace: 2^256
- This search range: 2^52
- Expected hits: (2^26 × 2^52) / 2^256 = 2^-178 ≈ **0** (essentially zero)

**Conclusion:** Searching this specific keyspace range was statistically guaranteed to yield zero funded addresses.

---

## Security Implications

### Private Key Generation Practice

**Red Flags:**
- ⚠️ **Terrible key generation practice** (if used for real wallets)
- ⚠️ Using a common prefix reduces entropy by 204 bits
- ⚠️ Effective security: 2^52 instead of 2^256 (trivially breakable)

**If these were real wallet keys:**
- An attacker knowing the prefix could brute force 2^52 keys in **hours** on a single GPU
- This represents a **catastrophic security failure**

**However:**
- These appear to be research/search keys, not wallet keys
- Likely generated for bloom filter testing or puzzle solving attempts
- No indication they were ever used to store funds

### Bloom Filter False Positives

This dataset is an **excellent example** of bloom filter false positive generation:

**Characteristics:**
1. ✓ High concentration of '0' in variable portion (bloom filter matching pattern)
2. ✓ Non-uniform distribution (filtering effect)
3. ✓ Zero funded matches (all false positives)
4. ✓ Systematic generation (GPU-based batch processing)

**Educational Value:**
- Demonstrates why bloom filters alone are insufficient
- Shows importance of verifying against actual funded database
- Illustrates the futility of narrow keyspace searches

---

## Comparison to Normal Key Generation

### Expected vs Actual

| Metric | Random Generation | This Dataset | Status |
|--------|-------------------|--------------|--------|
| Unique prefixes (51 chars) | ~27,208 | **1** | ❌ Anomalous |
| Hex distribution | Uniform (~6.25% each) | Non-uniform (0='25.62%') | ❌ Anomalous |
| Address patterns | Random | Normal | ✓ Expected |
| Funded matches | ~0 (statistically) | 0 | ✓ Expected |

### Normal Bitcoin Wallet Key Generation

**Standard Practice:**
1. Generate 256 bits of cryptographically secure random data
2. Ensure uniform distribution across all bits
3. No common prefixes between keys
4. Full entropy (2^256 keyspace coverage)

**This Dataset:**
1. ❌ NOT cryptographically secure (predictable pattern)
2. ❌ Non-uniform distribution (biased toward '0')
3. ❌ Common 51-character prefix (reduces entropy)
4. ❌ Tiny keyspace (2^52 instead of 2^256)

**Security Difference:** 2^256 / 2^52 = **2^204 times weaker** (incomprehensibly huge difference)

---

## Recommendations

### For Understanding This Dataset

1. ✓ **Recognize as research/bloom filter output** - not production wallet keys
2. ✓ **Understand systematic generation** - narrow keyspace search
3. ✓ **Appreciate statistical reality** - zero funded matches is expected
4. ✓ **Use as educational example** - demonstrates bloom filter false positives

### For Searching Funded Addresses

If attempting to find funded addresses (e.g., for research or puzzle solving):

1. ❌ **Don't use narrow keyspace ranges** - statistically guaranteed to fail
2. ❌ **Don't rely on bloom filters alone** - verify against funded database
3. ✅ **Focus on known weak keys** - brain wallets, biased RNG, etc.
4. ✅ **Analyze blockchain vulnerabilities** - nonce reuse, implementation bugs
5. ✅ **Use full keyspace random sampling** (if doing statistical research)

### For Key Generation (If Relevant)

1. ✅ **Use cryptographically secure random number generators**
2. ✅ **Ensure full 256-bit entropy**
3. ✅ **Verify uniform distribution**
4. ✅ **Never use predictable patterns or common prefixes**
5. ✅ **Test against known weak key databases**

---

## Summary Table

| Aspect | Finding | Interpretation |
|--------|---------|----------------|
| **Prefix Uniqueness** | 1 unique prefix (51 chars) | Systematic generation, NOT random |
| **Variable Portion** | 13 characters, 27,208 unique | Narrow keyspace search (2^52) |
| **Hex Distribution** | '0' overrepresented (25.62%) | Bloom filter artifacts |
| **Address Patterns** | Normal distribution | No vanity targeting |
| **Funded Matches** | 0 out of 27,208 | Statistically expected |
| **Effective Keyspace** | 2^52 (vs Bitcoin's 2^256) | 2^204 times smaller |
| **Security (if wallet)** | Catastrophically weak | Trivially breakable |
| **Actual Purpose** | Research/bloom filter test | Not production keys |
| **Educational Value** | High | Excellent false positive example |

---

## Weird Addresses: None Found

**Expected:** If these were vanity addresses or targeted funded wallets, we'd see:
- Many repeated characters (e.g., "1111111...")
- Specific words or patterns
- Low character diversity
- Concentration of specific prefixes

**Actual:** Addresses show completely normal statistical distribution

**Conclusion:**
- ✓ No weird addresses detected
- ✓ No targeting of funded wallets
- ✓ No vanity patterns
- ✓ All addresses appear to be standard outputs of private→public→address derivation
- ✓ The "special" part is in the private keys (common prefix), not the addresses

---

## Final Answer to User's Questions

### Q1: How many different prefixes in the 27,208 unique private keys?

**Answer: 1 (ONE) unique prefix**

All 27,208 private keys share the exact same 51-character prefix:
```
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b2
```

Only the last 13 characters vary.

### Q2: Any weird looking addresses?

**Answer: NO weird addresses found**

- 0 addresses with excessive zeros
- 0 addresses with excessive ones
- 0 addresses with unusual patterns
- 258 addresses with 3+ repeated chars (normal: ~1-2%)
- 472 addresses with palindromes (normal: ~1-3%)
- 184 addresses with sequences (normal: ~0.5-1%)

**All addresses exhibit normal statistical patterns** - no indication of vanity generation or funded wallet targeting.

The "weird" part is the **private keys** (single common prefix), not the addresses.

---

**Analysis Date:** 2026-01-24
**Dataset:** privkey_address.csv (27,208 unique keys)
**Key Finding:** Highly systematic generation with zero funded matches
