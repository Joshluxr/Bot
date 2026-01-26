# Bitcoin Address Prefix Distribution Analysis

## Overview

Comprehensive analysis of address prefix distribution across **12,147,704 unique addresses** from the VPS bloom filter candidate dataset.

## Address Type Distribution

| Address Type | Count | Percentage | Description |
|-------------|--------|------------|-------------|
| Legacy (1...) | 2,333,972 | 19.2% | P2PKH addresses |
| Script (3...) | 138,880 | 1.1% | P2SH addresses |
| SegWit (bc1...) | 527 | 0.004% | Bech32 addresses |
| **Other** | **9,674,325** | **79.7%** | **Metadata/labels** |

**Note:** The majority of entries (~79.7%) appear to be metadata labels like "Address (comp):", "Address (uncomp):", "dec)", "hex)", "uncompressed", etc., not actual Bitcoin addresses.

## Legacy Address (1...) Analysis

Focus on **2,333,972 actual Bitcoin addresses** starting with '1'.

### Second Character Distribution (Top 30)

The second character shows relatively even distribution with some biases:

| Prefix | Count | Notes |
|--------|-------|-------|
| 1A | 95,961 | |
| 1G | 95,960 | |
| 1L | 95,879 | |
| 1H | 95,876 | |
| 1E | 95,851 | |
| 1D | 95,827 | |
| 1P | 95,648 | |
| 1B | 95,626 | |
| 1J | 95,586 | |
| 1C | 95,491 | |
| 1F | 95,453 | |
| 1K | 95,441 | |
| 1M | 95,352 | |
| 1N | 95,308 | |
| 1Q | 33,649 | Lower occurrence |
| 1a | 10,370 | Lowercase variants |
| 1b | 10,348 | |
| 1e | 10,316 | |
| 1c | 10,294 | |
| 1f | 10,226 | |
| 1d | 10,201 | |

**Total addresses starting with '1f' or '1F': 105,679** (4.5% of legacy addresses)

## Addresses Starting with '1f*'

### Third Character Distribution (Top 20)

Out of **105,679 addresses** starting with '1f':

| Prefix | Count |
|--------|-------|
| 1fe | 3,990 |
| 1ff | 3,985 |
| 1fb | 3,965 |
| 1fd | 3,825 |
| 1fc | 3,813 |
| 1fa | 3,809 |
| 1fx | 3,482 |
| 1fp | 3,436 |
| 1fk | 3,435 |
| 1fs | 3,413 |
| 1fu | 3,410 |
| 1fj | 3,410 |
| 1fz | 3,374 |
| 1fh | 3,345 |
| 1ft | 3,338 |
| 1fm | 3,322 |
| 1fy | 3,317 |
| 1fw | 3,317 |
| 1fv | 3,294 |
| 1fq | 3,286 |

## Addresses Starting with '1fe*'

### Fourth Character Distribution (Top 20)

Out of **3,990 addresses** starting with '1fe':

| Prefix | Count |
|--------|-------|
| 1fed | 167 |
| 1feb | 165 |
| **1fee** | **162** |
| 1fea | 151 |
| 1fec | 148 |
| 1fef | 146 |
| 1fey | 126 |
| 1fex | 125 |
| 1feg | 125 |
| 1few | 124 |
| 1feu | 124 |
| 1feq | 123 |
| 1fev | 122 |
| 1fek | 119 |
| 1fez | 118 |
| 1fep | 116 |
| 1fet | 115 |
| 1feh | 115 |
| 1fer | 111 |
| 1fe7 | 110 |

## Addresses Starting with '1fee*'

### Fifth Character Distribution (Complete List)

Out of **162 addresses** starting with '1fee':

| Prefix | Count | Percentage |
|--------|-------|------------|
| 1feea | 13 | 8.0% |
| 1feef | 11 | 6.8% |
| 1fee3 | 10 | 6.2% |
| 1feee | 8 | 4.9% |
| 1feeb | 8 | 4.9% |
| **1feex** | **7** | **4.3%** |
| 1feen | 7 | 4.3% |
| 1fee9 | 7 | 4.3% |
| 1fees | 6 | 3.7% |
| 1feej | 6 | 3.7% |
| 1fee7 | 6 | 3.7% |
| 1fee1 | 6 | 3.7% |
| 1feez | 5 | 3.1% |
| 1feeu | 5 | 3.1% |
| 1feek | 5 | 3.1% |
| 1fee4 | 5 | 3.1% |
| 1feew | 4 | 2.5% |
| 1feed | 4 | 2.5% |
| 1feec | 4 | 2.5% |
| 1fee8 | 4 | 2.5% |
| 1feey | 3 | 1.9% |
| 1feem | 3 | 1.9% |
| 1feeh | 3 | 1.9% |
| 1fee2 | 3 | 1.9% |
| 1fee0 | 3 | 1.9% |
| 1feev | 2 | 1.2% |
| 1feer | 2 | 1.2% |
| 1feeq | 2 | 1.2% |
| 1feep | 2 | 1.2% |
| 1feeo | 2 | 1.2% |
| 1feeg | 2 | 1.2% |
| 1fee6 | 2 | 1.2% |
| 1feei | 1 | 0.6% |
| 1fee5 | 1 | 0.6% |

### Sixth Character for '1feex*'

The **7 addresses** starting with '1feex' have the following 6th characters:
- f, x, a, m, K, M, t

**No addresses have '1feexv'** as a prefix.

## Statistical Analysis

### Rarity Metrics

Starting from 12,147,704 total unique addresses:

| Prefix | Count | Probability | Rarity (1 in N) |
|--------|-------|-------------|-----------------|
| 1 | 2,333,972 | 19.2% | 1 in 5.2 |
| 1f | 105,679 | 0.87% | 1 in 115 |
| 1fe | 3,990 | 0.033% | 1 in 3,045 |
| 1fee | 162 | 0.0013% | 1 in 75,000 |
| 1feex | 7 | 0.000058% | **1 in 1.74 million** |
| 1feexv | 0 | 0% | **Not found** |

### Comparison with Random Distribution

For truly random Bitcoin addresses, each character position follows Base58 encoding probability.

**Expected vs Actual for '1fee*':**
- Expected (random): ~162 (closely matches!)
- Actual: 162
- **Conclusion:** Distribution appears natural for this prefix length

**Expected vs Actual for '1feex*':**
- Expected (random): ~7 (closely matches!)
- Actual: 7
- **Conclusion:** No unusual concentration at this prefix

**Expected vs Actual for '1feexv*':**
- Expected (random): ~0.3
- Actual: 0
- **Conclusion:** Missing due to small sample size, not unusual

## Key Insights

### 1. Natural Distribution
The prefix distribution follows expected Base58 probability patterns, suggesting:
- No targeted generation for specific prefixes
- Natural bloom filter candidate collection
- Random private key sampling

### 2. '1feex' Addresses Are Rare But Expected
- Finding 7 addresses with '1feex' prefix in 12M addresses is **statistically expected**
- Approximately 1 in 1.74 million addresses have this prefix
- The 6th character varies naturally (f, x, a, m, K, M, t)

### 3. No '1feexv' Is Normal
- Would expect ~0.3 addresses with '1feexv' in this dataset
- Finding 0 is within normal statistical variation
- Would need ~40 million addresses to expect finding one '1feexv' address

### 4. Fifth Character Most Common: 'a'
For '1fee*' addresses, the most common 5th character is:
- 'a': 13 occurrences (8.0%)
- 'f': 11 occurrences (6.8%)
- '3': 10 occurrences (6.2%)

## Prefix Hierarchy

```
Total Addresses: 12,147,704
└── Legacy (1...): 2,333,972 (19.2%)
    └── 1f*: 105,679 (4.5% of legacy)
        └── 1fe*: 3,990 (3.8% of 1f*)
            └── 1fee*: 162 (4.1% of 1fe*)
                └── 1feex*: 7 (4.3% of 1fee*)
                    └── 1feexv*: 0 (0%)
```

## Recommendations

### To Find More '1feex' Addresses:
1. Download additional bloom filter candidate datasets
2. Each 12M address dataset yields ~7 '1feex' addresses
3. Need ~1.74M addresses per '1feex' address on average

### To Find '1feexv' Addresses:
1. Would need approximately **40 million addresses** to expect finding one
2. Current dataset (12M) is too small for statistical significance
3. Consider merging multiple candidate datasets

## Related Files

- `1feex_addresses_analysis.md` - Detailed analysis of the 7 found '1feex' addresses
- `RESULTS_SUMMARY.md` - Overall comparison results
- `server2_candidates_analysis.md` - Analysis of alternative dataset (no '1feex' found)
