# Funded Address Check Results

## Overview

Checked interesting addresses with unusual patterns against the Loyce Club database of 55,354,799 funded Bitcoin addresses.

**Date:** January 24, 2026
**Database:** Bitcoin_addresses_LATEST.txt from addresses.loyce.club

## Results Summary

| Pattern | Addresses Checked | Funded Matches | Result |
|---------|------------------|----------------|--------|
| Contains "11111" | 3 | 0 | ✗ None funded |
| Starts with "1feex" | 7 | 0 | ✗ None funded |
| **Total** | **10** | **0** | **✗ None funded** |

## Detailed Results

### Addresses Starting with "11111" (Hash160)

These 3 addresses derived from Hash160s starting with five 1's:

| Address | Funded? | Pattern |
|---------|---------|---------|
| `1LysmAuZVVVpRr2bYwxwCQumqMKfzSFobo` | ✗ No | Hash160: 111115e3... |
| `1CDkPwMVKfdypEAHiSQXTV3BMDt6kMvdAZ` | ✗ No | Hash160: 11111185... |
| `16rzCgtuwvzQwh9XP95RbCxPmfxm9RPwyj` | ✗ No | Hash160: 0b111111... (six 1's) |

**Result:** None are funded.

### Addresses Starting with "1feex"

All 7 addresses with the rare "1feex" prefix:

| # | Address | Funded? | Type |
|---|---------|---------|------|
| 1 | `1FEexfuNrhPaSs8exwezpstvarC3MSDN7j` | ✗ No | Compressed |
| 2 | `1FeeXx39mrWJXU1wJ4Xdu4xyi6E8URXERS` | ✗ No | Compressed |
| 3 | `1FEexaWFK4Z7qBuNCqjqdksLa76NnGfNrp` | ✗ No | Uncompressed |
| 4 | `1FEexmCcUj695svca6n7FPwzndQtGMgCYp` | ✗ No | Uncompressed |
| 5 | `1FeExKGmgQawDb4dJGbEgHJD51G3k1rSbh` | ✗ No | Uncompressed |
| 6 | `1FeExMdMnRAvgsARU1oMS6utLUcSNwu8Jn` | ✗ No | Uncompressed |
| 7 | `1FeeXtuP3tEJpELtFJaF19QtRzpJge1RKD` | ✗ No | Uncompressed |

**Result:** None are funded.

## Analysis

### What This Means

1. **Bloom Filter Candidates Are Unfunded**
   - All these addresses come from bloom filter candidate searches
   - They were flagged as potential matches but turned out to be false positives
   - This confirms the "false positive" designation in the original datasets

2. **No Hidden Treasure**
   - None of these unusual pattern addresses contain Bitcoin
   - Despite their interesting patterns (multiple 1's, rare prefixes), they're just empty addresses
   - The patterns are mathematically interesting but financially worthless

3. **Database Coverage**
   - The Loyce Club database contains 55.3M funded addresses
   - This represents a comprehensive snapshot of addresses that have ever received Bitcoin
   - If these addresses had ever been funded, they would appear in this database

### Statistical Context

Out of 12,147,704 candidate addresses analyzed:
- **0 matched** any funded addresses
- This aligns with the original comparison results
- Confirms these are bloom filter search results, not actual puzzle solutions

## Comparison with Original Full Dataset Check

### Original Comparison (All 12M Addresses)
- **Candidate addresses:** 12,147,704 unique
- **Funded addresses checked:** 55,354,799
- **Matches found:** **0**

### This Focused Check (10 Interesting Addresses)
- **Addresses checked:** 10 (interesting patterns only)
- **Funded addresses checked:** 55,354,799
- **Matches found:** **0**

**Conclusion:** Consistent results - no bloom filter candidates are funded.

## Why Check These Specific Addresses?

These addresses were selected for additional verification because:

1. **Extremely Rare Patterns**
   - "11111" appears in only 86 out of 12M addresses
   - "1feex" appears in only 7 out of 12M addresses
   - Rarity sometimes correlates with interesting origins

2. **Vanity Address Potential**
   - Addresses with repeated characters are often deliberately generated
   - Such addresses might be more likely to be used/funded

3. **User Interest**
   - Specifically requested patterns to investigate
   - Helps understand what types of addresses exist in the dataset

## Security & Privacy Notes

### For These Specific Addresses:

⚠️ **CRITICAL WARNING:** The private keys for all these addresses are **publicly known** and documented in this repository.

**Never send Bitcoin to these addresses:**
- Private keys are published in `1feex_addresses_analysis.md`
- Private keys are published in `addresses_with_11111_analysis.md`
- Anyone can steal funds sent to these addresses immediately
- They exist for research/analysis purposes only

### General Bitcoin Security:

✅ **Good News:** This analysis demonstrates Bitcoin's security:
- Even with massive bloom filter searches (12M+ candidates)
- Targeting specific patterns and ranges
- Using GPU acceleration
- **Still found 0 funded addresses**

This shows that finding funded addresses through random or targeted search is effectively impossible.

## Methodology

### Check Process:

1. **Extract addresses** from bloom filter candidate dataset
2. **Sort both files** for efficient comparison (already done)
3. **Use grep** to search for exact matches in funded database
4. **Pattern:** `grep -q "^$address$" Bitcoin_addresses_sorted.txt`

### Database Details:

- **Source:** http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz
- **Size (compressed):** 1.4GB
- **Size (uncompressed):** 2.2GB
- **Total addresses:** 55,354,799
- **Update frequency:** Periodic snapshots
- **Coverage:** All addresses that have received Bitcoin transactions

## Future Checks

To check other patterns or addresses:

```bash
# On VPS
ssh root@65.75.200.133
cd /root/bitcoin_address_check

# Check a specific address
grep "^YOUR_ADDRESS_HERE$" Bitcoin_addresses_sorted.txt

# Check multiple addresses from file
while read addr; do
  grep -q "^$addr$" Bitcoin_addresses_sorted.txt && echo "FOUND: $addr"
done < your_addresses.txt
```

## Related Documents

- `RESULTS_SUMMARY.md` - Overall comparison of 12M addresses
- `1feex_addresses_analysis.md` - Detailed analysis of 7 "1feex" addresses
- `addresses_with_11111_analysis.md` - Analysis of 86 addresses with "11111"
- `prefix_distribution_analysis.md` - Statistical analysis of all prefixes

## Conclusion

### Key Takeaways:

1. ✗ **No funded addresses** found with interesting patterns
2. ✓ **Confirms bloom filter results** are all false positives
3. ✓ **Demonstrates Bitcoin security** - searching doesn't find funded addresses
4. ⚠️ **Private keys are public** - never use these addresses for real Bitcoin

### Final Verdict:

All 10 interesting pattern addresses checked are **unfunded and empty**. This is consistent with them being bloom filter false positives from puzzle-solving attempts.
