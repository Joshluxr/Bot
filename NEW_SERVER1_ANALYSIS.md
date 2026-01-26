# New Server1 File Analysis

## File Information

**Source:** https://tmpfiles.org/dl/21298764/server1_candidates.txt
**Total Addresses:** 8,113 (after deduplication)
**Date Analyzed:** 2026-01-26

---

## Results Summary

### Funded Address Check
```
Addresses checked:     8,113
Funded DB addresses:   55,401,177
MATCHES FOUND:         0
```

**Result:** No matches found against funded Bitcoin addresses database.

---

## Interesting Addresses Found

### 🏆 Premium Vanity Pattern

**"1FEE" PREFIX** (All Uppercase - Extra Rare!)
```
1FEE9huWihg1djXubL3DkMsuK6efTT6U2D
```

This is particularly interesting because:
- Full uppercase "FEE" (more rare than mixed case "Fee")
- Similar to famous Bitcoin Pizza address: `1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF`
- Only 1 found in this dataset (vs 3 "1Fee" mixed-case in previous files)

### Repeated Digits

**Triple 4s:**
```
1444s6JiHXo8XhsFkW7SeTGsNv214R4jJN
```

### All Uppercase Addresses (Professional Look)

Found **48 addresses** with 6+ consecutive uppercase letters:

**Top Examples:**
```
1AJNDPQ5tHKn5BvJGUZKVWkxAbhgRuvfwz  (7 uppercase)
1AKLRADf39THsGCQ3HC56YtyWhLYos3Det  (6 uppercase)
1ANKRMWRxSEXPersx3z3HvRjLQtKTdmhBw  (6 uppercase)
1BASMXBUtZx59WTnTbboNuNsvinYYirN5E  (6 uppercase)
1BCHCXVtaAtbViG4q6SFZG6skLWNfmMScm  (6 uppercase)
1BQWSTRh3EQEV6zU73VBPAzwfXvAQWbS55  (7 uppercase)
1BZHUHFnXGBBZivYb6cngHdQ2jWcmXVh6b  (6 uppercase)
1CDNMUWPKaft3SB6wQvGwQuEcgjWUS9teM  (6 uppercase)
1CLPLBFEva45CB1MfiDPJdN5J9s4YXnpcF  (6 uppercase)
```

### Long Numeric Sequences

Addresses with 4+ consecutive digits:
```
12311YwUnxdhaLL9Bncu5MWjq3Bu8DJm2c  (2311)
12989YrxYUE7rE8u5kKgQ57FvGgX3Um3kP  (2989)
14424RNP9VP6FQeg9rgQMzGauFdemPC1DG  (4424)
14673jgc1dVJpT2DQMcBPJ8tkW4jcjhhk1  (4673)
14847Yvxzr7NtzNRvAAwqZuwxS4acEMyV5  (4847)
14851EXmHPVf38LLEZ36YTTdUP2GjvYLgL  (4851)
14962xxC1ueQDzibmdZD32X7pt4LmP5B1C  (4962)
18164Y9VuUEhfrcDUXhCG1fHEPC2ceRQDL  (8164)
19943m3pmBwhjBdGYdru8LyYQVFJTpfBjx  (9943)
```

---

## Comparison with Previous Files

### Combined "Fee" Addresses (All Files)

| Pattern | Previous Files | New File | Total |
|---------|----------------|----------|-------|
| Mixed case "1Fee" | 3 | 0 | 3 |
| Uppercase "1FEE" | 0 | 1 | 1 |
| **Total Fee prefix** | **3** | **1** | **4** |

**All "Fee" Prefix Addresses Found:**
```
Previous:
  1FeeCUzG24PSEuguDWE61XqhVw3tmzKEib  (mixed case)
  1Fee1HegbQQhEzftvQ62NjCBWGq6A8hMUy  (mixed case)
  1FeefVd8NGYCwxh9a5fAjxAJb9zaB7yczC  (mixed case)

New:
  1FEE9huWihg1djXubL3DkMsuK6efTT6U2D  ⭐ UPPERCASE! (rarer)
```

---

## Statistics

| Metric | Value |
|--------|-------|
| Total addresses | 8,113 |
| Unique addresses | 8,113 |
| Interesting patterns | 48 |
| Premium vanity (Fee) | 1 |
| Uppercase sequences | 48 |
| Numeric sequences | 10+ |
| Funded matches | 0 |

---

## Address Samples by Type

### CSV Format (Address + Private Key)
```
11DLMYuxuZMX5CUMbhsV1FXVEtyoUjPt2,5KkCm7b3zbYVH1ALbX4C8i24u9uDKM6WxBs6MwMim4B8oAg8Rv5
11EdBCFPjiLiS9qXSRkCUmU89SWwJGd5q,5Hwz3gkin3i8P5kkoLiBD72qV4gfnCZ1Y4hsTPEtN1HKqVtJN6W
11HMsoJkttyApUgqUVifh2FBjZv9v4Ld9,5KD7Eg3sWXrUhAGKcYwiHNRTrMWC9v6MZMsPSuth5Qeg9JMs6jC
```

All addresses are standard P2PKH format (starting with "1") with valid checksums.

---

## Key Findings

### ✅ Positive
1. **Found 1 more premium "FEE" vanity address** (uppercase variant)
2. 48 professional-looking uppercase addresses
3. All addresses are valid Bitcoin P2PKH format
4. Multiple interesting numeric sequences

### ℹ️ Neutral
1. Smaller dataset (8K vs 260K previous)
2. Fewer vanity patterns overall (due to smaller size)
3. Different address generation parameters/range

### ⚠️ Expected
1. No funded matches (as expected for random search)
2. Random distribution of patterns consistent with previous files

---

## Combined Total Results

### Across ALL Files (Previous + New)

| Category | Count |
|----------|-------|
| **Total addresses analyzed** | **271,035** |
| **Interesting addresses** | **5,686** |
| **"Fee" prefix addresses** | **4** |
| **"Love" prefix addresses** | **1** (unique!) |
| **"BTC" prefix addresses** | **13** |
| **Funded matches** | **0** |

---

## Files Generated

**On VPS:**
- `/root/server1_new_check.txt` - Original CSV file (8,349 lines)
- `/root/server1_new_addresses.txt` - Extracted addresses (8,113 unique)

**Local:**
- `/root/repo/server1_new_all.txt` - Copy of addresses
- `/root/repo/NEW_SERVER1_ANALYSIS.md` - This report

---

## Quick Commands

### View the FEE address with private key
```bash
ssh root@65.75.200.134
grep "1FEE9huWihg1djXubL3DkMsuK6efTT6U2D" /root/server1_new_check.txt
```

### View all uppercase addresses
```bash
grep -E "^1[A-Z]{6,}" /root/server1_new_addresses.txt
```

### Download new file locally
```bash
scp root@65.75.200.134:/root/server1_new_check.txt ./
```

---

## Conclusion

The new server1 file contains **8,113 addresses** with:
- ✅ 1 premium uppercase "1FEE" vanity address (rare variant)
- ✅ 48 professional uppercase addresses
- ✅ All addresses valid P2PKH format
- ❌ 0 funded matches (expected)

The **uppercase "1FEE"** address is particularly interesting as it's rarer than the mixed-case variants found previously. This brings the total "Fee" prefix addresses to **4** across all analyzed files.

---

*Analyzed: 2026-01-26*
*Source: New server1 candidates file*
*Verified against: 55.4M funded addresses*
