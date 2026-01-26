# K3 Addresses Analysis - Bitcoin Funded Address Comparison

**Analysis Date:** 2026-01-26
**Source File:** k3_addresses_privkeys.csv
**Funded Address Database:** Bitcoin_addresses_LATEST.txt.gz (55M+ addresses from Loyce Club)
**Total Candidates Checked:** 38,995

## Results Summary

**MATCHES FOUND: 0 out of 38,995**

All 38,995 candidate addresses were checked against the funded Bitcoin address database. **None of the candidates matched any funded addresses.**

## Pattern Analysis

### 1. Systematic Key Generation - Round Decimal Numbers

The private keys show a **VERY STRONG PATTERN** of being generated from round decimal numbers:

**Examples:**
- Address #1: `80 × 10^72 + 7,975,272`
- Address #2: `45 × 10^72 + 74,298,331`
- Address #3: `45 × 10^72 + 75,649,763`
- Address #4: `10 × 10^72 + 13,954,881`
- Address #5: `35 × 10^72 + 10,765,837`

This indicates **systematic keyspace exploration** starting from multiples of 10^72.

### 2. Trailing Zeros in Hex

The hexadecimal representation reveals extensive trailing zeros:

| Trailing Zeros | Count | Percentage |
|----------------|-------|------------|
| 0 zeros | 36,474 | 93.5% |
| 1 zero | 2,374 | 6.1% |
| 2 zeros | 136 | 0.35% |
| 3 zeros | 10 | 0.03% |
| 4 zeros | 1 | 0.003% |

The trailing zeros in hex form are a direct result of the decimal-based generation pattern.

### 3. Address Prefix Distribution

Top 20 most common address prefixes:
1. `133` - 59 addresses
2. `19V` - 55 addresses
3. `15k` - 51 addresses
4. `1A3` - 50 addresses
5. `1By` - 49 addresses
6. `1Jo` - 49 addresses
7. `19R` - 49 addresses

The distribution appears relatively uniform with no significant clustering, suggesting the keys generate addresses distributed across the address space.

### 4. Sample Keys and Patterns

**Key #1:**
```
Hex:     0xb0de65388cc8ada83b25a55f43294bcbbbad2f8b8ca88000000000000079b168
Decimal: 80000000000000000000000000000000000000000000000000000000000000000000007975272
Address: 1111CeycppWGSfKZn2ythuSSszBgfEMcY
Pattern: 80 × 10^72 + 7,975,272
```

**Key #2 (same as Candidate #9 from previous analysis):**
```
Hex:     0x637d18efcf30e1aea1452d0595c73aa299916abe7f1ec80000000000046db3db
Decimal: 45000000000000000000000000000000000000000000000000000000000000000000074298331
Address: 112qAeXYdrq15PpoQ1Q2ngpgfXnnDr3dJ
Pattern: 45 × 10^72 + 74,298,331
```

**Key #4:**
```
Hex:     0x161bcca7119915b50764b4abe86529797775a5f1719510000000000000d4ef41
Decimal: 10000000000000000000000000000000000000000000000000000000000000000000013954881
Address: 11FXhVVyBiRoSoGwkESczWDQEy4EfJpHA
Pattern: 10 × 10^72 + 13,954,881
```

## Key Observations

### 1. Systematic Search Strategy
This dataset represents a **systematic exploration** of the Bitcoin keyspace using:
- Base values: Multiples of 10^72 (10, 15, 20, 25, 30, 35, 40, 45, 50, ... 80, etc.)
- Offsets: Small integers added to each base value
- Purpose: Likely testing bloom filter hits or exploring specific keyspace regions

### 2. Decimal-Based Generation
Unlike typical Bitcoin key generation (which is hex/binary-based), these keys are clearly:
- Generated in decimal form first
- Then converted to hexadecimal
- This explains the trailing zeros pattern

### 3. Bloom Filter False Positives
All 38,995 addresses are likely **bloom filter false positives**:
- Generated keys matched bloom filter patterns
- But DO NOT correspond to actual funded addresses
- Confirms bloom filter methodology has high false positive rate

### 4. Keyspace Coverage
The keys span different regions of the keyspace:
- Lowest: ~10 × 10^72 (~8.6% of keyspace)
- Highest: ~80 × 10^72 (~69% of keyspace)
- Multiple discrete ranges being explored

## Statistical Analysis

**Total Analysis to Date:**
- Previous candidates: 53,241
- This batch: 38,995
- **Grand Total: 92,236 candidate addresses analyzed**
- **Funded matches found: 0**

**Probability Analysis:**
- Bitcoin address space: ~2^160 ≈ 1.46 × 10^48 addresses
- Funded addresses: ~55 million ≈ 5.5 × 10^7
- Random hit probability: ~3.8 × 10^-41 per attempt
- Expected matches from 92,236 attempts: ~3.5 × 10^-36 (essentially zero)

## Conclusions

1. **Zero Funded Matches**: Consistent with all previous analyses
2. **Systematic Generation**: Clear pattern of decimal-based key generation from round numbers
3. **Bloom Filter Strategy**: This appears to be output from a bloom filter search tool
4. **Bitcoin Security Confirmed**: No vulnerability found despite testing 92,236+ candidates
5. **False Positive Rate**: 100% false positive rate for bloom filter candidates

## Technical Details

**Private Key Format:**
- All keys are 256-bit (64 hex characters)
- Trailing zeros indicate decimal generation
- WIF format provided for each key

**Address Format:**
- All Legacy Bitcoin addresses (P2PKH)
- Start with "1"
- Mix of compressed and uncompressed formats

## Security Notice

**CRITICAL WARNING:** These private keys are publicly known and published. Never use these keys or send any Bitcoin to these addresses, as funds would be immediately vulnerable to theft.

## Recommendations

1. **Continue Monitoring**: Track new candidate batches
2. **Pattern Recognition**: This systematic approach helps understand bloom filter search strategies
3. **False Positive Analysis**: High false positive rate confirms difficulty of keyspace search
4. **Security Validation**: Results continue to validate Bitcoin's cryptographic security

## Related Files

- Previous 11 candidates analysis: `new_11_candidates_analysis.md`
- Decimal values: `11_candidates_decimals.txt`
- Complete comparison results: `COMPLETE_COMPARISON_RESULTS.md`
