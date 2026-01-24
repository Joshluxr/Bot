# Bitcoin Address Comparison Report

## Summary

**Date:** January 23, 2026  
**Comparison Type:** Candidate addresses vs Known Bitcoin addresses database

## Data Sources

### Source 1: Candidate Addresses
- **File:** `server2_candidates_compressed.txt`
- **Source URL:** https://tmpfiles.org/dl/20978576/server2_candidates_compressed.txt
- **Total Addresses:** 2,649
- **Format:** WIF private key + Bitcoin address (tab-separated)
- **Address Type:** P2PKH compressed Bitcoin addresses

### Source 2: Bitcoin Addresses Database
- **File:** `Bitcoin_addresses_LATEST.txt.gz`
- **Source URL:** http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz
- **Database Size:** 1.4 GB compressed, ~2.2 GB uncompressed
- **Format:** Plain text, one address per line
- **Description:** Comprehensive database of Bitcoin addresses that have appeared on the blockchain

## Comparison Results

### Matches Found: **0 out of 2,649**

**Match Rate:** 0.00%

### Interpretation

✅ **No matches found** - This means:

1. **None of the 2,649 candidate addresses have ever appeared on the Bitcoin blockchain**
2. **No transactions** have been sent to or from these addresses
3. **Zero balance** on all addresses (never used)
4. These are **virgin addresses** with no blockchain history

### What This Means

**For Security:**
- ✅ Keys are not from known compromised sets
- ✅ Addresses haven't been publicly exposed in transactions
- ✅ No historical usage to analyze

**For Value:**
- ❌ No Bitcoin ever received at these addresses
- ❌ Current balance: 0 BTC on all addresses
- ❌ No transaction history to recover

## Technical Details

### Comparison Method
```bash
# Extracted addresses from candidate file
awk '{print $2}' server2_candidates_compressed.txt > candidate_addresses_only.txt

# Compared against full Bitcoin addresses database
gunzip -c Bitcoin_addresses_LATEST.txt.gz | grep -Fxf candidate_addresses_only.txt
```

### Sample Candidate Addresses Checked
```
1Bnj4wWLMwUbLmEGmq2MPEBMiCTjykE7ij
1AGH8Htb77fY5CKcu7DPiiSMAQaVWsv5WG
19BmXN8kAsXPQUguvfgeSY1ryM9nJGkDuw
12AxfJR8ewTkN919bNbp2wezRwWJhet8TX
1E5Ut4zpBT7hBUdGBH21XNaq4VPWw5Hdsd
```

### Database Coverage

The Loyce.club Bitcoin addresses database includes:
- All addresses that have ever received Bitcoin
- All addresses that have ever sent Bitcoin
- Updated regularly from blockchain data
- Covers addresses from 2009 to present

## Conclusion

**Result:** None of the 2,649 candidate addresses have any blockchain activity or history.

**Recommendation:** 
- These addresses have never been used on the Bitcoin network
- No funds are associated with these addresses
- The private keys, while valid, control empty wallets

---

*Report generated on January 23, 2026*
