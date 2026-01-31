# Bitcoin Keypair Verification Toolkit

Complete toolkit for verifying that Bitcoin public addresses match their corresponding private keys. Essential for validating candidate data from GPU Bitcoin mining/search operations.

## 📋 Quick Start

### 1. Run the test suite to verify everything works:
```bash
./quick_verify.sh test
```

### 2. Verify a CSV file (quick check):
```bash
./quick_verify.sh candidates.csv
```

### 3. Verify specific keypair:
```bash
./quick_verify.sh <privkey_hex> <address>
```

## 🛠️ Toolkit Components

### Core Scripts

| File | Purpose |
|------|---------|
| `verify_keypairs.py` | Main verification engine - handles CSV files and individual keypairs |
| `test_verify.py` | Test suite with known Bitcoin keypairs |
| `quick_verify.sh` | User-friendly wrapper for common verification tasks |
| `check_remote_candidates.sh` | Verify candidates on remote GPU servers |

### Documentation

| File | Content |
|------|---------|
| `KEYPAIR_VERIFICATION_GUIDE.md` | Detailed usage guide and troubleshooting |
| `KEYPAIR_VERIFICATION_README.md` | This file - quick reference |

## 🚀 Common Use Cases

### Verify Local CSV File

**Quick check (first 10 lines):**
```bash
./quick_verify.sh /path/to/candidates.csv
```

**Check first 100 lines:**
```bash
./quick_verify.sh /path/to/candidates.csv 100
```

**Sample large file (check 1000 lines, every 10th):**
```bash
./quick_verify.sh /path/to/candidates.csv 1000 10
```

**Full verification (all lines):**
```bash
python3 verify_keypairs.py /path/to/candidates.csv
```

### Verify Single Keypair

```bash
./quick_verify.sh 0000000000000000000000000000000000000000000000000000000000000001 1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm
```

Or directly:
```bash
python3 verify_keypairs.py <privkey_hex> <address>
```

### Verify Remote Server Candidates

**Connect to GPU server and verify candidates:**
```bash
./check_remote_candidates.sh verify-remote 195.26.253.243 /root/all_candidates_server1_NEW.csv 100
```

**Download and verify locally:**
```bash
./check_remote_candidates.sh download 195.26.253.243 /root/all_candidates_server1_NEW.csv
```

**Verify all configured servers:**
```bash
./check_remote_candidates.sh verify-all
```

## 📊 CSV File Format

Expected format:
```csv
address,privkey,hash160
1FeexV6bAHfnfB1GKmLiXeBjTJNQyL2nVJ,a1b2c3d4e5f6...,e5a42ba9384952a98e7e6a1e99e94f3f3a1e5f2d
1AnotherBitcoinAddress123456789ABC,1234567890ab...,1234567890abcdef1234567890abcdef12345678
```

The script will:
- Skip header lines (detected automatically)
- Handle any order of columns (as long as address and privkey are present)
- Report line numbers for any mismatches

## ✅ Expected Output

### All Valid
```
Verifying keypairs from: candidates.csv
================================================================================
Line 2: ✓ VALID - Address matches
Line 3: ✓ VALID - Address matches
...
Line 100: ✓ VALID - Address matches

================================================================================
RESULTS:
  Total checked: 100
  Valid: 100 (100.0%)
  Invalid: 0
  Errors: 0
```

### Mismatch Detected
```
Line 42: ✗ MISMATCH
  Expected: 1FeexV6bAHfnfB1GKmLiXeBjTJNQyL2nVJ
  Computed: 1DifferentAddressHere123456789ABC
  Expected hash160: e5a42ba9384952a98e7e6a1e99e94f3f3a1e5f2d
  Computed hash160: 1234567890abcdef1234567890abcdef12345678
  Address: 1FeexV6bAHfnfB1GKmLiXeBjTJNQyL2nVJ
  PrivKey: a1b2c3d4e5f6...
```

## 🔧 Installation & Dependencies

### Required: secp256k1 Library

Install coincurve (recommended - fast):
```bash
pip install coincurve --break-system-packages
```

Or ecdsa (fallback - slower):
```bash
pip install ecdsa --break-system-packages
```

The script will automatically use coincurve if available, otherwise fall back to ecdsa.

### Verification Process
```
Private Key (hex)
    ↓ [secp256k1 multiplication]
Public Key (uncompressed)
    ↓ [SHA256 + RIPEMD160]
Hash160
    ↓ [Version byte + Checksum + Base58]
Bitcoin Address
```

## ⚡ Performance

| Library | Speed | Notes |
|---------|-------|-------|
| coincurve | ~10,000-50,000 keys/sec | Uses libsecp256k1 (C library) |
| ecdsa | ~100-500 keys/sec | Pure Python implementation |

For large datasets (millions of entries):
- Use sampling: `verify_keypairs.py file.csv 10000 100` (check every 100th line)
- Run in batches
- Use coincurve for best performance

## 🎯 Real-World Examples

### Example 1: Quick Validation
You just generated 10,000 candidates on a GPU server and want to verify them:

```bash
# Download candidates from server
scp root@195.26.253.243:/root/candidates.csv ./

# Quick verification (sample 100 random entries)
./quick_verify.sh candidates.csv 100

# If all good, verify more thoroughly
./quick_verify.sh candidates.csv 1000 10
```

### Example 2: Verify Without Downloading
Your candidate file is 10GB and you don't want to download it:

```bash
# Verify directly on remote server
./check_remote_candidates.sh verify-remote 195.26.253.243 /root/huge_candidates.csv 1000 10
```

### Example 3: Found a Match!
You found a matching address and want to verify the keypair is correct:

```bash
./quick_verify.sh <private_key_from_log> <bitcoin_address_that_matched>
```

### Example 4: Comparing Two Servers
You ran searches on multiple servers and want to verify both:

```bash
./check_remote_candidates.sh verify-all
```

## 🔐 Security Notes

⚠️ **CRITICAL SECURITY WARNINGS**:

1. **Never share private keys** - The CSV files contain sensitive cryptographic material
2. **Secure file permissions** - Use `chmod 600 candidates.csv`
3. **Encrypted storage** - Store candidate files on encrypted volumes
4. **Secure deletion** - Use `shred -vfz` instead of `rm` for sensitive files
5. **Network security** - Use SSH keys, not passwords, for remote operations
6. **Air-gapped verification** - For high-value keys, verify on offline systems

## 🐛 Troubleshooting

### Problem: "Library missing" error
**Solution:**
```bash
pip install coincurve --break-system-packages
```

### Problem: All keypairs show as invalid
**Possible causes:**
1. CSV format issue (wrong column order)
2. Custom key derivation algorithm (e.g., BloomSearch K3)
3. Compressed vs uncompressed key mismatch
4. Data corruption

**Debug steps:**
```bash
# Check CSV format
head -3 candidates.csv

# Verify with known good keypair
./quick_verify.sh test

# Check a single entry manually
python3 -c "
from verify_keypairs import verify_keypair
print(verify_keypair('0000000000000000000000000000000000000000000000000000000000000001',
                      '1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm'))
"
```

### Problem: Private keys don't match but addresses do
This indicates the logged "private key" isn't the final ECDSA private key. Common with:
- BIP32/BIP39 derivation
- Custom algorithms (e.g., BloomSearch K3)
- Intermediate computation values being logged

**Solution:** Research the specific tool's key derivation algorithm.

## 📚 Additional Resources

- [KEYPAIR_VERIFICATION_GUIDE.md](./KEYPAIR_VERIFICATION_GUIDE.md) - Detailed technical guide
- Bitcoin address format: https://en.bitcoin.it/wiki/Technical_background_of_version_1_Bitcoin_addresses
- secp256k1 curve: https://en.bitcoin.it/wiki/Secp256k1

## 🤝 Integration with Your Workflow

### With BloomSearch GPU Mining
```bash
# 1. Extract candidates from logs
python3 extract_candidates.py

# 2. Verify extracted data
./quick_verify.sh extracted_candidates.csv 100

# 3. If valid, continue monitoring
python3 monitor_loop.py
```

### With Multiple GPU Servers
```bash
# Verify all servers in parallel
./check_remote_candidates.sh verify-all > verification_report.txt
```

### Automated Verification
Add to your monitoring scripts:
```bash
# In your cron job or monitoring script
if ./quick_verify.sh /path/to/new_candidates.csv 50; then
    echo "✓ Candidates verified - $(date)" >> validation.log
else
    echo "✗ VERIFICATION FAILED - $(date)" >> validation.log
    # Send alert
fi
```

## 📝 Summary

This toolkit provides everything needed to verify Bitcoin keypairs:

✅ **Core verification engine** - Handles all Bitcoin address validation
✅ **Multiple interfaces** - Python API, CLI, shell scripts
✅ **Remote verification** - Check candidates on GPU servers without downloading
✅ **Sampling support** - Efficiently verify large datasets
✅ **Test suite** - Validate the tools are working correctly
✅ **Comprehensive docs** - Guides, examples, troubleshooting

For questions or issues, refer to the detailed guide: `KEYPAIR_VERIFICATION_GUIDE.md`
