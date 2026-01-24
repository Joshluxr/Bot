# Bitcoin Address Comparison Results

## Executive Summary

Successfully compared 12.1M candidate Bitcoin addresses against 55.3M funded Bitcoin addresses from the Loyce Club database.

**Result: 0 matches found**

## Process Overview

### 1. Data Download
- **VPS**: 65.75.200.133
- **Working Directory**: /root/bitcoin_address_check
- **Available Space**: 59GB

### 2. Candidate Addresses
Downloaded 6 parts from catbox.moe:
- part_aa.gz (46M) - 180M uncompressed
- part_ab.gz (46M) - 180M uncompressed
- part_ac.gz (46M) - 180M uncompressed
- part_ad.gz (46M) - 180M uncompressed
- part_ae.gz (46M) - 180M uncompressed
- part_af.gz (43M) - 169M uncompressed

**Combined Total**: 14,991,007 addresses (1.1GB)
**Unique Addresses**: 12,147,704 (after deduplication)

### 3. Funded Addresses
Downloaded from: http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz
- **Compressed Size**: 1.4GB
- **Uncompressed Size**: 2.2GB
- **Total Addresses**: 55,354,799
- **Unique Addresses**: 55,354,799 (no duplicates)

### 4. Comparison Method
- Both files were sorted using `sort -u` for efficient comparison
- Used `comm -12` to find common addresses between sorted files
- Total processing time: ~4 minutes

## Results

### Matches Found: 0

No Bitcoin addresses from the candidate list matched any funded addresses in the Loyce Club database.

## Interpretation

The lack of matches indicates that:
1. The candidate addresses have never received Bitcoin transactions, OR
2. The addresses in the candidate list use different address formats than those in the funded database, OR
3. The addresses may have been active but are not included in the Loyce Club snapshot

## Files on VPS

All files are located in `/root/bitcoin_address_check/`:

### Downloaded Files
- `part_aa.gz` through `part_af.gz` - Original compressed parts
- `part_aa` through `part_af` - Decompressed parts
- `Bitcoin_addresses_LATEST.txt.gz` - Compressed funded addresses
- `Bitcoin_addresses_LATEST.txt` - Decompressed funded addresses

### Generated Files
- `all_candidates_full.txt` - Combined candidate addresses (1.1GB)
- `all_candidates_sorted.txt` - Sorted unique candidate addresses
- `Bitcoin_addresses_sorted.txt` - Sorted funded addresses
- `matches.txt` - Empty file (0 matches)
- `comparison.log` - Detailed execution log
- `summary_report.txt` - Summary report

## Script Location

The comparison script is available at:
- Local: `/root/repo/scripts/download_and_compare_addresses.sh`

## Execution Timeline

```
[02:53:03] Script started
[02:53:03] Started downloading candidate parts
[02:53:42] Finished downloading candidate parts (39 seconds)
[02:53:42] Started downloading funded addresses
[02:54:02] Finished downloading funded addresses (20 seconds)
[02:54:02] Started decompressing files
[02:54:09] Finished decompressing candidate parts (7 seconds)
[02:54:11] Combined all parts
[02:54:11] Started decompressing funded addresses
[02:54:30] Finished decompressing funded addresses (19 seconds)
[02:54:30] Started sorting candidate addresses
[02:55:53] Finished sorting candidates (83 seconds)
[02:55:53] Started sorting funded addresses
[02:56:44] Finished sorting funded addresses (51 seconds)
[02:56:44] Started comparison
[02:57:07] Comparison complete (23 seconds)
```

**Total Execution Time**: ~4 minutes

## Next Steps

If you want to investigate further:
1. Verify address format compatibility
2. Check if addresses need to be converted between formats (P2PKH, P2SH, Bech32, etc.)
3. Consider using a different funded address database
4. Verify the source and generation method of candidate addresses

## Access VPS

To access the VPS and review files:
```bash
ssh root@65.75.200.133
cd /root/bitcoin_address_check
ls -lh
```

Password: S910BtnGoh45RuE
