# Bitcoin Keypair Verification Toolkit

Complete toolkit for verifying Bitcoin public addresses match their corresponding private keys.

## 🚀 Quick Start

```bash
# Run demo with sample data
python3 create_sample_and_verify.py

# Verify your GPU server candidates
./verify_my_candidates.sh both
```

## 📚 Documentation

- **[VERIFY_CANDIDATES_NOW.md](./VERIFY_CANDIDATES_NOW.md)** - Start here for your specific setup
- **[QUICK_START_VERIFICATION.md](./QUICK_START_VERIFICATION.md)** - 30-second quick start guide
- **[KEYPAIR_VERIFICATION_README.md](./KEYPAIR_VERIFICATION_README.md)** - Complete reference
- **[KEYPAIR_VERIFICATION_GUIDE.md](./KEYPAIR_VERIFICATION_GUIDE.md)** - Technical guide

## 🛠️ Tools Included

- `verify_keypairs.py` - Core verification engine (secp256k1 ECDSA)
- `quick_verify.sh` - Easy CLI wrapper
- `verify_my_candidates.sh` - GPU server verification (pre-configured)
- `test_verify.py` - Test suite with known Bitcoin keypairs
- `demo_verification.sh` - Interactive demonstration

## ✅ What It Does

Verifies that private keys correctly generate Bitcoin addresses using:
1. secp256k1 elliptic curve cryptography
2. Proper hash160 (SHA256 + RIPEMD160)
3. Standard Bitcoin Base58 address encoding

## 🎯 Use Cases

- Validate GPU mining/search candidate data
- Verify extracted Bitcoin keypairs
- Check data integrity across multiple servers
- Detect custom key derivation algorithms

## ⚡ Performance

- Speed: ~10,000-50,000 verifications/second (with coincurve)
- Supports CSV batch verification with sampling
- Statistical validation for large datasets (millions of entries)

## 📊 Your Candidate Files

**Server 1** (195.26.253.243): 3.2M candidates (437MB)
**Server 2** (195.26.253.245): 5.5M candidates (739MB)

Configured and ready to verify.

---

This repository was initialized by Terragon.