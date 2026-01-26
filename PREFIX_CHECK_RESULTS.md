# User Prefix Check Results

## Summary

Checked **24 user-provided prefixes** against candidate address databases.

**Result:** ✓ **1 prefix found with 46,933 matching addresses!**

---

## Prefixes Checked

| # | Prefix | Status | Count |
|---|--------|--------|-------|
| 1 | 1ANkDM | ✗ Not found | 0 |
| 2 | 1Ki3WTEE | ✗ Not found | 0 |
| 3 | 1MtUMTq | ✗ Not found | 0 |
| 4 | 1CY7fyk | ✗ Not found | 0 |
| 5 | 1HLvaT | ✗ Not found | 0 |
| 6 | 198aMn | ✗ Not found | 0 |
| 7 | 15Z5YJa | ✗ Not found | 0 |
| 8 | 1AYLzYN | ✗ Not found | 0 |
| 9 | 178E8tYZ | ✗ Not found | 0 |
| 10 | 138EMxw | ✗ Not found | 0 |
| 11 | 13n67sF | ✗ Not found | 0 |
| 12 | 1BeouDc | ✗ Not found | 0 |
| 13 | 1ARWCRE | ✗ Not found | 0 |
| 14 | 1Btud1p | ✗ Not found | 0 |
| 15 | 1VeMPNg | ✗ Not found | 0 |
| 16 | 1812yXz | ✗ Not found | 0 |
| 17 | 18eY9o | ✗ Not found | 0 |
| 18 | 18F838 | ✗ Not found | 0 |
| 19 | 1FvUkW8 | ✗ Not found | 0 |
| 20 | 17GGGH | ✗ Not found | 0 |
| 21 | **1GUNPh** | **✓✓✓ FOUND!** | **46,933** |
| 22 | 1AenFm | ✗ Not found | 0 |
| 23 | 1NY5KheH | ✗ Not found | 0 |
| 24 | 3281T7i | ✗ Not found | 0 |

---

## ✓ Match Found: 1GUNPh

**Prefix:** `1GUNPh`
**Matches Found:** 46,933 addresses
**Source File:** `/root/repo/address_server/found.txt`
**Full List:** `/root/repo/1GUNPh_ADDRESSES.txt`

### Sample Addresses

```
1. 1GUNPhAJRtoXRUtkU97LFwAV7mAKiR83o7
   WIF: p2pkh:KyZjHt1NxgJJKtxM6y4fCCNrsMbsFjNEFLW4H4qgsU6b9xnKhuRC
   HEX: 0x45F92EE4717C6708089D906954DBE5EF1E2664F747FCADC5E0AB4AF56959D6D1

2. 1GUNPh1g6NBUcK87XqqGcHMj7KakR8y7FZ
   WIF: p2pkh:KwLnq38o8q8YTVkmtHXP3UVaCuuwEUt2DGPP6UkzZ4imigMy1SLQ
   HEX: 0x3A46B23BCD02A58C97CC6F57E2B332098465B6A1632C1164AF4A4A966A348E1

3. 1GUNPh8nCyU8hSJ6oExWmfvjAnRhnRyTwD
   WIF: p2pkh:Kzdn2itqLSNWistgoewsEefnSyDDFF7BL6pGJM5AA39Hb6wYREpy
   HEX: 0x65E48F3FE9FA12A94C0C4663C7E3A40BF886FA241A1F8E6C543AC4A055597E0E

4. 1GUNPh6kohdwFZbAYLky2rSPiv9eAVBJx9
   WIF: p2pkh:KxfXWpke8zwmZg3ZvzJ6Mirj18NPZbF2T7oz6wsbGvJ95re618ou
   HEX: 0x2B1E3ED81A5973FC475E50CF7B255AB2668518F6955CCCB6BDFAB5CE2D6C4C3B

5. 1GUNPhoEgvcr9psaMGmKwHdxVdaiRq2ack
   WIF: p2pkh:KxradhsHBi9TPQk3qPtheqZvQBwVUcZ7yt4AhTAGCRiz9bWDkM3j
   HEX: 0x30CDFBD9E3F14CD7953C95645B34F72661EEF3663B32BBBF69917FF20268E860
```

*(... and 46,928 more)*

---

## Statistics

- **Total prefixes checked:** 24
- **Prefixes found:** 1 (4.2%)
- **Prefixes not found:** 23 (95.8%)
- **Total matching addresses:** 46,933
- **Source database size:** 140,799 lines (~46,933 addresses)

---

## Analysis

### Why 1GUNPh was found

The `1GUNPh` prefix appears to have been specifically targeted for generation. The entire `found.txt` file contains **46,933 addresses**, and **ALL of them** start with `1GUNPh`. This suggests:

1. **Vanity address generation:** This was a deliberate vanity address search for the `1GUNPh` prefix
2. **Complete capture:** The tool successfully generated and saved all found variations
3. **Dedicated run:** The address generation was focused solely on this pattern

### Prefix characteristics

- **Length:** 6 characters (1 + GUNPh)
- **Difficulty:** ~5.8 billion attempts on average to find each address
- **Pattern:** Gun + Ph (possibly "Gun Phone" or similar meaning)
- **Case sensitivity:** Mixed case (uppercase G, U, N, P, lowercase h)

### Why others weren't found

The other 23 prefixes weren't found because:
1. They were not targeted by the vanity address generation run
2. Different address generation sessions likely focused on different patterns
3. The candidate files checked (8,465 addresses) and other analysis files represent different generation sessions

---

## Files Generated

1. **`1GUNPh_ADDRESSES.txt`** - All 46,933 addresses with their private keys (WIF and HEX format)
2. **`PREFIX_CHECK_RESULTS.md`** - This summary report

---

## Recommendations

To find the other prefixes, you would need to:

1. Check other `found.txt` files from different vanity search sessions
2. Run new vanity address generation targeting those specific prefixes
3. Check if there are additional address databases not yet analyzed

---

**Generated:** 2026-01-26
**Total Addresses in found.txt:** 46,933
**Matching Prefix:** 1GUNPh (100% match rate in this file)
