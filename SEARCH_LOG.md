# SearchK4 Search Log

## Summary

All searches have been conducted on 8× NVIDIA RTX 5080 GPUs via vast.ai, achieving ~13.2 GKey/s combined throughput.

**Total keys searched across all ranges: ~40+ quadrillion (4 × 10^16)**
**Total matches found: 0**

---

## Range 4 (Completed)
- **From:** ~61.79 × 10^72
- **To:** ~61.80 × 10^72
- **Result:** No matches found
- **Status:** COMPLETED

---

## Range 5 (Completed)
- **From:** 90,249,899,529,415,616,346,188,046,094,668,845,621,511,272,653,822,246,032,194,562,587,016,979,379,107
- **To:** 90,310,704,385,268,831,039,622,650,419,970,111,827,024,811,508,981,061,528,731,048,716,778,495,645,775
- **Total Range:** ~6.08 × 10^73 keys
- **Keys Checked:** ~19.5 quadrillion (infinitesimal fraction of range)
- **Duration:** ~14 days
- **Combined Speed:** ~13.8 GKey/s
- **Result:** No matches found
- **Status:** STOPPED (server restart), not fully exhausted

---

## Range 6 (Completed - Fully Exhausted)
- **From:** 82,988,190,356,384,517,260,073,324,955,726,623,558,128,682,318,812,983,971,013,120,423,526,066,342,990
- **To:** 82,988,190,356,384,517,260,073,324,955,726,623,558,128,682,318,812,983,971,013,120,923,526,066,342,990
- **Total Range:** 500,000,000,000,000 keys (500 trillion)
- **Keys Checked:** 500 trillion (100%)
- **Duration:** ~10 hours
- **Combined Speed:** ~13.2 GKey/s
- **Result:** No matches found
- **Status:** COMPLETED - FULLY EXHAUSTED

---

## Range 7 (Last Active)
- **From:** 82,988,190,356,384,517,260,073,324,955,726,623,558,128,682,318,812,983,971,013,110,423,526,066,342,990
- **To:** 82,988,190,356,384,517,260,073,324,955,726,623,558,128,682,318,812,983,971,013,120,423,526,066,342,990
- **Total Range:** 10,000,000,000,000,000 keys (10 quadrillion)
- **Keys Checked:** ~9.21 quadrillion (92.1% at last check)
- **Duration:** ~8+ days
- **Combined Speed:** ~13.2 GKey/s
- **Result:** No matches found (as of last check)
- **Status:** 92.1% complete at last connection; server connection lost before confirmation of completion

### Range 7 Per-GPU Status (Last Check)
| GPU | Keys Checked (B) | Speed (GKey/s) |
|-----|------------------|----------------|
| 0 | 1,163,976 | 1.66 |
| 1 | 1,122,349 | 1.61 |
| 2 | 1,137,448 | 1.65 |
| 3 | 1,150,528 | 1.65 |
| 4 | 1,145,991 | 1.65 |
| 5 | 1,161,661 | 1.66 |
| 6 | 1,170,358 | 1.68 |
| 7 | 1,162,346 | 1.66 |

---

## Performance Notes

- RTX 5080 achieves ~1.65-1.77 GKey/s per GPU for secp256k1 key iteration
- 8× RTX 5080 system costs ~$1.186/hr on vast.ai
- Cost efficiency: ~$0.085/GKey/s/hr (best among tested GPUs)
- State files (~40MB each) enable seamless resume after crashes
- Processes occasionally die due to server restarts; always resume from state files
