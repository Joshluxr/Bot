# Bitcoin Keypair Verification Guide

## Overview

This guide explains how to verify that Bitcoin public addresses match their corresponding private keys using the provided verification tools.

## Tools

### 1. verify_keypairs.py
Main verification script that can:
- Verify keypairs from CSV files
- Verify individual keypairs
- Sample large datasets
- Detect mismatches between private keys and addresses

### 2. test_verify.py
Test script that validates the verification tool using known Bitcoin keypairs.

## Installation

The verification requires the `coincurve` library (libsecp256k1 wrapper):

```bash
pip install coincurve --break-system-packages
```

Or if you prefer using ecdsa (fallback):
```bash
pip install ecdsa --break-system-packages
```

## Usage

### Verify CSV File (All Lines)

```bash
python3 /root/repo/verify_keypairs.py /path/to/candidates.csv
```

Expected CSV format:
```
address,privkey,hash160
1FeexV6bAH...,a1b2c3d4...,e5f6g7h8...
```

### Verify CSV File (First N Lines)

```bash
python3 /root/repo/verify_keypairs.py /path/to/candidates.csv 100
```

This checks only the first 100 lines.

### Verify CSV File (Sample Every Nth Line)

```bash
python3 /root/repo/verify_keypairs.py /path/to/candidates.csv 1000 10
```

This checks 1000 lines, sampling every 10th line (checks lines 10, 20, 30, ..., 10000).

### Verify Single Keypair

```bash
python3 /root/repo/verify_keypairs.py <privkey_hex> <address>
```

Example:
```bash
python3 /root/repo/verify_keypairs.py \
  0000000000000000000000000000000000000000000000000000000000000001 \
  1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm
```

## How It Works

The verification process:

1. **Private Key → Public Key**: Uses secp256k1 elliptic curve multiplication
2. **Public Key → Hash160**: Applies SHA256 then RIPEMD160
3. **Hash160 → Address**: Adds version byte, computes checksum, encodes in Base58

```
Private Key (32 bytes hex)
    ↓ [secp256k1 point multiplication]
Public Key (65 bytes uncompressed: 0x04 + X + Y)
    ↓ [SHA256 then RIPEMD160]
Hash160 (20 bytes)
    ↓ [Add 0x00 version + checksum + Base58 encode]
Bitcoin Address (Base58 string starting with '1')
```

## Output

### Valid Keypair
```
Line 1: ✓ VALID - Address matches
Line 2: ✓ VALID - Address matches
...
================================================================================
RESULTS:
  Total checked: 100
  Valid: 100 (100.0%)
  Invalid: 0
  Errors: 0
```

### Invalid Keypair
```
Line 42: ✗ MISMATCH
  Expected: 1FeexV6bAHfnfB1GKmLiXeBjTJNQyL2nVJ
  Computed: 1DifferentAddressHere123456789ABC
  Expected hash160: e5a42ba9384952a98e7e6a1e99e94f3f3a1e5f2d
  Computed hash160: 1234567890abcdef1234567890abcdef12345678
  Address: 1FeexV6bAHfnfB1GKmLiXeBjTJNQyL2nVJ
  PrivKey: a1b2c3d4e5f6...
```

## Common Issues

### Issue: "Library missing" error

**Solution**: Install coincurve or ecdsa library:
```bash
pip install coincurve --break-system-packages
```

### Issue: Private keys don't match addresses

This could happen if:
1. The private key uses a custom derivation algorithm (like BloomSearch K3)
2. The keys are compressed vs uncompressed format mismatch
3. The data is corrupted

**For custom algorithms**: You need to understand the specific key derivation used by your tool.

### Issue: Large file takes too long

**Solution**: Use sampling:
```bash
# Check every 100th line from first million lines
python3 verify_keypairs.py candidates.csv 1000000 100
```

## Integration with BloomSearch K3

According to your previous work, the BloomSearch K3 tool may use a custom key derivation algorithm. The logged private keys may not directly correspond to standard Bitcoin ECDSA key generation.

If you encounter mismatches:

1. **First verify hash160 values are correct** - these should match between your data and what the verification script computes
2. **Check if addresses are correct** - hash160 to address conversion is standard
3. **If only private keys don't match** - K3 may be logging intermediate values, not final private keys

You may need to:
- Examine the K3 source code for key derivation
- Look for additional processing steps (BIP32, BIP39, custom derivation)
- Create a custom verification script that matches K3's algorithm

## Testing

Run the test suite to verify the tool is working:

```bash
python3 /root/repo/test_verify.py
```

This tests with known Bitcoin keypairs (privkey=1, privkey=2).

## Quick Check Commands

```bash
# Check if you have candidate files
find /root -name "*candidate*.csv" 2>/dev/null

# Preview first few lines of a candidate file
head -10 /root/all_candidates_server1_NEW.csv

# Count lines in candidate file
wc -l /root/all_candidates_server1_NEW.csv

# Quick verification of first 10 lines
python3 /root/repo/verify_keypairs.py /root/all_candidates_server1_NEW.csv 10

# Sampled verification (every 1000th line)
python3 /root/repo/verify_keypairs.py /root/all_candidates_server1_NEW.csv 10000 1000
```

## Performance

- **coincurve**: ~10,000-50,000 verifications/second (uses libsecp256k1)
- **ecdsa**: ~100-500 verifications/second (pure Python)

For large datasets (millions of entries), use sampling or run verification in batches.

## Security Notes

⚠️ **IMPORTANT**:
- Never share private keys publicly
- Store verification results securely
- The verification script only reads data, it doesn't modify files
- Private keys are processed in memory only, not saved to disk

## Example Workflow

```bash
# 1. Test the verification tool
python3 /root/repo/test_verify.py

# 2. Check first 100 entries from your candidate file
python3 /root/repo/verify_keypairs.py /root/all_candidates_server1_NEW.csv 100

# 3. If all looks good, verify a larger sample
python3 /root/repo/verify_keypairs.py /root/all_candidates_server1_NEW.csv 10000 10

# 4. If issues found, verify a specific keypair
python3 /root/repo/verify_keypairs.py <suspicious_privkey> <suspicious_address>
```
