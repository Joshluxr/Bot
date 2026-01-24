# Bitcoin Address Comparison Results

This directory contains the results of comparing candidate Bitcoin addresses against the comprehensive Loyce Club database of funded Bitcoin addresses.

## Quick Summary

- **Comparison Date**: January 24, 2026
- **Candidate Addresses**: 12,147,704 unique addresses
- **Funded Addresses Checked**: 55,354,799 addresses
- **Matches Found**: **0**
- **Processing Time**: ~4 minutes

## Files in this Directory

- `RESULTS_SUMMARY.md` - Comprehensive analysis and detailed results
- `summary_report.txt` - Quick summary from VPS execution
- `comparison.log` - Full execution log with timestamps
- `matches.txt` - List of matching addresses (empty, 0 matches)

## Scripts

Located in `/root/repo/scripts/`:

### download_and_compare_addresses.sh
Main script that performs the entire comparison process:
- Downloads 6 candidate address parts from catbox.moe
- Downloads Bitcoin funded addresses from Loyce Club
- Decompresses and combines all files
- Sorts and deduplicates addresses
- Performs efficient comparison using `comm -12`
- Generates comprehensive reports

**Usage:**
```bash
./scripts/download_and_compare_addresses.sh
```

This script runs directly on the VPS via SSH automation.

### check_bitcoin_results.sh
Helper script to check the current status on the VPS:
- Shows disk usage
- Lists all files with sizes
- Displays comparison summary
- Shows first 20 matches (if any)

**Usage:**
```bash
./scripts/check_bitcoin_results.sh
```

## VPS Information

All data is stored on the VPS at:
- **IP Address**: 65.75.200.133
- **Working Directory**: `/root/bitcoin_address_check`
- **Total Disk Usage**: 8.8GB

### Access VPS

```bash
ssh root@65.75.200.133
cd /root/bitcoin_address_check
```

### Files on VPS

**Downloaded Files:**
- `part_aa.gz` through `part_af.gz` - Compressed candidate parts
- `part_aa` through `part_af` - Decompressed candidate parts
- `Bitcoin_addresses_LATEST.txt.gz` - Compressed funded addresses (1.4GB)
- `Bitcoin_addresses_LATEST.txt` - Decompressed funded addresses (2.2GB)

**Generated Files:**
- `all_candidates_full.txt` - Combined candidates (1.1GB, 14.9M addresses)
- `all_candidates_sorted.txt` - Sorted unique candidates (852MB, 12.1M addresses)
- `Bitcoin_addresses_sorted.txt` - Sorted funded addresses (2.2GB)
- `matches.txt` - Matching addresses (0 bytes, 0 matches)
- `comparison.log` - Execution log
- `summary_report.txt` - Summary report

## Understanding the Results

### Why 0 Matches?

The comparison found no matches between the candidate addresses and funded addresses. This could mean:

1. **No Transactions**: The candidate addresses have never received any Bitcoin transactions
2. **Format Mismatch**: Different address formats (P2PKH, P2SH, Bech32, etc.) may not be comparable
3. **Database Coverage**: Addresses may exist outside the Loyce Club database snapshot
4. **Address Generation**: The candidate addresses may be from a different derivation path or seed

### Address Formats

Bitcoin has multiple address formats:
- **Legacy (P2PKH)**: Starts with '1' (e.g., 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa)
- **Script (P2SH)**: Starts with '3' (e.g., 3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy)
- **SegWit (Bech32)**: Starts with 'bc1' (e.g., bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq)

If the candidate and funded addresses use different formats, they won't match even if they control the same private key.

## Next Steps

To investigate further:

1. **Check Address Formats**: Examine sample addresses from both files to verify format compatibility
   ```bash
   ssh root@65.75.200.133 "head -10 /root/bitcoin_address_check/all_candidates_sorted.txt"
   ssh root@65.75.200.133 "head -10 /root/bitcoin_address_check/Bitcoin_addresses_sorted.txt"
   ```

2. **Convert Formats**: If formats differ, convert addresses to matching format before comparison

3. **Verify Sources**: Confirm the origin and generation method of candidate addresses

4. **Alternative Databases**: Try comparing against other Bitcoin address databases

5. **Sample Check**: Manually verify a few candidate addresses using blockchain explorers

## Blockchain Explorers

To manually check if specific addresses have transactions:
- https://blockchain.info/address/[ADDRESS]
- https://blockchair.com/bitcoin/address/[ADDRESS]
- https://www.blockchain.com/explorer/addresses/btc/[ADDRESS]

## Performance Notes

The comparison was highly efficient:
- Download time: ~1 minute
- Decompression: ~30 seconds
- Sorting: ~2.5 minutes
- Comparison: ~23 seconds
- **Total**: ~4 minutes

This is achieved through:
- Parallel downloads where possible
- Efficient sorting with `sort -u`
- Fast comparison with `comm -12` on sorted files
- All operations on VPS with good bandwidth and disk I/O

## Backup Results Locally

To download all results from VPS to your local machine:

```bash
sshpass -p 'S910BtnGoh45RuE' scp -r root@65.75.200.133:/root/bitcoin_address_check ./bitcoin_vps_backup
```

This will create a local backup of all files in `./bitcoin_vps_backup/`.

## Re-running the Comparison

To re-run with fresh data or new candidate addresses:

1. Update the download URLs in `scripts/download_and_compare_addresses.sh`
2. Run the script: `./scripts/download_and_compare_addresses.sh`
3. Check results: `./scripts/check_bitcoin_results.sh`

The script is idempotent - it will skip downloads and processing steps for files that already exist.

## Contact

For questions about this comparison or to request new analyses, please refer to the main repository documentation.
