# Quick Start: Verify Bitcoin Keypairs

## 🚀 Get Started in 30 Seconds

### 1. Run the demo to see it in action:
```bash
cd /root/repo
./demo_verification.sh
```

### 2. Test with known keypairs:
```bash
./quick_verify.sh test
```

### 3. Verify your candidate file:
```bash
./quick_verify.sh /path/to/your/candidates.csv
```

## 📝 Common Commands

### Local File Verification

```bash
# Quick check (first 10 lines)
./quick_verify.sh candidates.csv

# Check first 100 lines
./quick_verify.sh candidates.csv 100

# Check 1000 lines, sample every 10th
./quick_verify.sh candidates.csv 1000 10
```

### Remote Server Verification

```bash
# Verify candidates on GPU server
./check_remote_candidates.sh verify-remote 195.26.253.243 /root/all_candidates_server1_NEW.csv 100

# Verify all configured servers
./check_remote_candidates.sh verify-all
```

### Single Keypair Verification

```bash
./quick_verify.sh <private_key_hex> <bitcoin_address>

# Example:
./quick_verify.sh 0000000000000000000000000000000000000000000000000000000000000001 1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm
```

## ✅ What to Expect

### Valid Keypairs
```
Line 1: ✓ VALID - Address matches
Line 2: ✓ VALID - Address matches
...
RESULTS:
  Total checked: 100
  Valid: 100 (100.0%)
  Invalid: 0
```

### Invalid Keypairs
```
Line 42: ✗ MISMATCH
  Expected: 1FeexV6bAHfnfB1GKmLiXeBjTJNQyL2nVJ
  Computed: 1DifferentAddress...

RESULTS:
  Total checked: 100
  Valid: 99 (99.0%)
  Invalid: 1
```

## 📚 Full Documentation

- **Quick Reference**: [KEYPAIR_VERIFICATION_README.md](./KEYPAIR_VERIFICATION_README.md)
- **Detailed Guide**: [KEYPAIR_VERIFICATION_GUIDE.md](./KEYPAIR_VERIFICATION_GUIDE.md)

## ⚡ Performance Tips

For large files (millions of entries):
- Use sampling: `./quick_verify.sh file.csv 100000 100`
- This checks every 100th line = 1,000 verifications instead of 100,000
- Still provides excellent validation coverage

## 🔧 Troubleshooting

### "Library missing" error?
```bash
pip install coincurve --break-system-packages
```

### All keypairs showing invalid?
- Check CSV format (should be: address,privkey,hash160)
- Your tool may use custom key derivation (see guide)

### Need help?
```bash
./quick_verify.sh          # Shows usage
./demo_verification.sh      # Interactive demo
```

---

**That's it!** You're ready to verify Bitcoin keypairs. For advanced usage, see the full documentation.
