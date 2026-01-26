# New Bitcoin Bloom Filter Candidates
**Date:** 2026-01-26  
**New Candidates:** 130,774 verified address-private key pairs

## Summary

These are NEW candidates found since the previous extraction (1,223,334 pairs).
All candidates have been cryptographically verified with correct Bitcoin addresses.

## Server Breakdown

**Current Unique Counts:**
- Server 1: 556,033 unique (was 485,773) → +70,260 growth
- Server 2: 304,685 unique (was 272,351) → +32,334 growth  
- Server 4: 94,644 unique (was 49,570) → +45,074 growth
- Server 3: 440,754 unique (no change - cycling through same range)

**New Candidates After Deduplication:** 130,774

## Why Server 3 Shows No New Candidates

Server 3 is still running but finding the same candidates repeatedly. This is expected:
- The GPU search continuously loops through key ranges
- Bloom filters have false positives that get re-discovered
- Server 3 has likely scanned its entire assigned range multiple times
- It shows 19M+ total candidates but only ~440K unique (44x duplication)

## Download Link

**NEW Candidates (130,774 entries):**
https://tmpfiles.org/dl/21349235/new_candidates_130k.zip

**Previous Complete Set (1,223,334 entries):**
https://tmpfiles.org/dl/21346897/candidates_final_verified.zip

## File Format

Plain text, one entry per line:
```
[BITCOIN_ADDRESS] [PRIVATE_KEY_HEX]
```

Example:
```
1BsXQTh8ofTbbDnokxy8movXstvb1hmQCW fe1ef9e0309e12806a986cc9d2b9d35425a3d135494639a648e94a0c123fbc57
```

## File Details

- **Compressed Size:** 4.2 MB
- **Uncompressed Size:** 13 MB
- **Total Entries:** 130,774
- **Success Rate:** 100% (0 errors)
- **Verification:** All cryptographically verified

## Total Candidates Now Available

- Previous extraction: 1,223,334
- New candidates: +130,774
- **Grand Total:** 1,354,108 unique verified pairs

## Verification

✓ All 130,774 pairs cryptographically verified  
✓ 100% success rate (0 errors)  
✓ Proper ECDSA secp256k1 conversion  
✓ Uncompressed public key format  
✓ SHA256 + RIPEMD160 hashing  
✓ Base58Check encoding  

⚠️ **Note:** These are bloom filter candidates. Compare addresses against your target list to find actual matches.
