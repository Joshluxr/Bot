# Candidates_Final.csv - Comprehensive Analysis

**Analysis Date:** 2026-01-26
**Source File:** candidates_final.csv
**Funded Address Database:** Bitcoin_addresses_LATEST.txt.gz (55M+ addresses from Loyce Club)
**Total Candidates Checked:** 87,240

## Results Summary

**MATCHES FOUND: 0 out of 87,240**

All 87,240 candidate addresses were checked against the funded Bitcoin address database. **None of the candidates matched any funded addresses.**

## Dataset Comparison

### Overlap with K3 Dataset
- K3 dataset addresses: 38,995
- Final dataset addresses: 87,240
- **Overlap between datasets: 37,973** (97.4% of K3 is included)
- **New addresses in final dataset: 46,874**

This dataset appears to be an expanded version that includes most of the K3 dataset plus nearly 47,000 additional addresses.

## Vanity-Like Addresses Found

### 1. Quad 1s - "1111" (1 address)
```
Address: 1111CeycppWGSfKZn2ythuSSszBgfEMcY
WIF:     5KABTPrNwJuajCzwkRMoNraY7Bfaxamn42yEVn5VUb9GChVY6v5
Hex:     b0de65388cc8ada83b25a55f43294bcbbbad2f8b8ca88000000000000079b168
Decimal: 80 × 10^72 + 7,975,272
```

### 2. FEE Prefix - "1FEE" (4 addresses)
```
1. 1FEEcgPihbyAKdyNzFmPEdsLJwCNgRGE9u
   WIF: 5Ja6tLEpBkStGonxwPLQW1679zVAkpp6f8CY1CdMSqA5weYmooC

2. 1FeE3CjSYew9gXJ1WRyeePZV71ivcZ94cj
   WIF: 5JKVnSya9epawCzQJf3EhMJnBCGREvq6M29x5XS9hpHRU3NbkJQ

3. 1FeEG5EGmv5ya3DykBiWjXN556yC685Jo8
   WIF: 5Ja6tLEpBkStGonxwPLQW1679zVAkpp6f8CY1CdMSskT6zYfSQE

4. 1Feev67GRysi53ZwDjvPEf1UYD8xbyhgS6 (NEW!)
   WIF: 5Ja6tLEpBkStGonxwPLQW1679zVAkpp6f8CY1CdMT4e3zXEuRYd
```

### 3. BTC Prefix - "1BTC" (2 addresses)
```
1. 1BTco7LZXtgMGfKf9p1smKohKWZCrCSW4L (NEW!)
   WIF: 5J9m3roQnvQPNonhDWB8AFTEBznatzqkocnto5JgYvW7HF7MBSx

2. 1BtcGDrBnw7DNZ5NYwyUTVCRFd9vtoocC8
   WIF: 5JKVnSya9epawCzQJf3EhMJnBCGREvq6M29x5XS9hradkC2ooFs
```

### 4. Triple A - "1AAA" (3 addresses)
```
1. 1AAag2X42W8a6ERAp5W1dtLtGmHHEBy8cp
   WIF: 5Ja6tLEpBkStGonxwPLQW1679zVAkpp6f8CY1CdMSwWY2R7Aqvj

2. 1AAauSg1KaC1YaH4BgM1AdT9z66bQedKRx
   WIF: 5JEdR9tVUHcVA1PYm5cBRoP1BbXW4xqRaKURSJNR8MTeNctMMMc

3. 1Aaa1sPh5kqiVtty8bi9KkP8B59vgJ7CkB (NEW!)
   WIF: 5JVEX39jWPEnVcC7PouMETALAPkFarpRtRX1MyZcrraZkr1M4Sh
```

### 5. ABC Sequence - "1ABC" / "1abc" (2 addresses)
```
1. 1ABCZ215ZYmqJUV4BiiVf9BjAZ372Z8vBE (NEW! - Uppercase ABC)
   WIF: 5J9m3roQnvQPNonhDWB8AFTEBznatzqkocnto5JgYx9A8VEuSBj

2. 1AbCN1Fzjrw1Kn5k6DfAwcR8ptE1Pp3H4b
   WIF: 5KABTPrNwJuajCzwkRMoNraY7Bfaxamn42yEVn5VUe4ezYcCME3
```

### 6. Sequential "1234" (1 address)
```
Address: 1234MLdwmer8FuzH3KX54iyB7mNEGQj6q3 (NEW!)
WIF:     5Ja6tLEpBkStGonxwPLQW1679zVAkpp6f8CY1CdMT3j7NUXVhiH
```

## Pattern Analysis

### Private Key Generation
All private keys show the same decimal-based generation pattern:
- Trailing zeros in hexadecimal form
- Base values: Multiples of 10^72
- Small offsets added to base values
- Example: `b0de65388cc8ada83b25a55f43294bcbbbad2f8b8ca88000000000000079b168`

### Trailing Zero Distribution (First 100 Keys)
- 0 trailing zeros: 91 keys (91%)
- 1 trailing zero: 9 keys (9%)

Similar pattern to K3 dataset, confirming decimal-based generation.

### Address Prefix Distribution

**Top 10 2-character prefixes:**
1. '1J' - 3,964 addresses
2. '13' - 3,868 addresses
3. '1M' - 3,854 addresses
4. '18' - 3,852 addresses
5. '1F' - 3,823 addresses
6. '1K' - 3,818 addresses
7. '17' - 3,815 addresses
8. '12' - 3,811 addresses
9. '1N' - 3,807 addresses
10. '1D' - 3,795 addresses

Distribution is relatively uniform, showing no significant clustering.

### Addresses Starting with "11"
- Total: 336 addresses (0.39%)
- Same percentage as K3 dataset

## New Vanity Addresses (Not in K3)

This expanded dataset includes **4 new vanity-like addresses**:
1. **1Feev67GRysi53ZwDjvPEf1UYD8xbyhgS6** - 4th "1FEE" address
2. **1BTco7LZXtgMGfKf9p1smKohKWZCrCSW4L** - 2nd "1BTC" address
3. **1Aaa1sPh5kqiVtty8bi9KkP8B59vgJ7CkB** - 3rd "1AAA" address
4. **1ABCZ215ZYmqJUV4BiiVf9BjAZ372Z8vBE** - Uppercase "1ABC"
5. **1234MLdwmer8FuzH3KX54iyB7mNEGQj6q3** - Sequential "1234"

## Statistical Analysis

### Total Analysis to Date
- Previous candidates: 53,241
- K3 dataset: 38,995
- Candidates_final (unique): 87,240
- **Total unique addresses analyzed: ~131,000+**
- **Funded matches found: 0**

### Probability Context
- Bitcoin address space: ~2^160 ≈ 1.46 × 10^48 addresses
- Funded addresses: ~55 million ≈ 5.5 × 10^7
- Random hit probability: ~3.8 × 10^-41 per attempt
- Expected matches from 131,000 attempts: ~5.0 × 10^-36 (essentially zero)

## Key Observations

1. **Zero Funded Matches**: Consistent with all previous analyses
2. **Expanded Dataset**: Contains 97.4% of K3 dataset plus 46,874 new addresses
3. **More Vanity Addresses**: 5 new interesting prefixes found
4. **Same Generation Method**: Decimal-based systematic keyspace exploration
5. **Bloom Filter False Positives**: 100% false positive rate maintained

## Comparison with Previous Datasets

| Dataset | Addresses | Vanity Patterns | Funded Matches |
|---------|-----------|----------------|----------------|
| Server 1 original | 27,208 | - | 0 |
| Server 2 original | 25,867 | - | 0 |
| WIF keys | 155 | - | 0 |
| 11 candidates | 11 | - | 0 |
| K3 dataset | 38,995 | 8 | 0 |
| **Candidates_final** | **87,240** | **13** | **0** |

## Conclusions

1. **Largest Dataset Yet**: 87,240 addresses is the largest single batch analyzed
2. **Systematic Generation**: All keys follow decimal-based generation from round numbers
3. **Vanity Collection**: More vanity-like addresses than any previous dataset
4. **Security Validated**: Zero funded matches confirms Bitcoin's cryptographic strength
5. **False Positive Confirmation**: All candidates are bloom filter false positives
6. **Ineffective Search**: Systematic keyspace exploration continues to be ineffective

## Technical Details

**File Format:**
- CSV with address and WIF private key
- 87,240 total entries
- All Legacy Bitcoin addresses (P2PKH)
- Mix of compressed and uncompressed keys

**Generation Pattern:**
- Base: N × 10^72 where N ∈ {10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, ...}
- Offset: Small integer (typically < 100M)
- Result: Base + Offset = Private Key (decimal)

## Security Notice

**CRITICAL WARNING:** All 87,240 private keys are publicly known. Never send Bitcoin to these addresses. Any funds would be immediately vulnerable to theft. These keys are for research and cryptographic analysis only.

## Recommendations

1. **Continue Monitoring**: Track additional candidate batches if they emerge
2. **Pattern Documentation**: This systematic approach helps understand bloom filter search limitations
3. **False Positive Analysis**: Confirms high false positive rate in bloom filter strategies
4. **Bitcoin Security**: Results validate Bitcoin's resistance to systematic keyspace exploration

## Related Files

- K3 analysis: `k3_addresses_analysis.md`
- K3 unique prefixes: `k3_unique_prefixes_analysis.txt`
- Previous 11 candidates: `new_11_candidates_analysis.md`
- Complete results: `COMPLETE_COMPARISON_RESULTS.md`
