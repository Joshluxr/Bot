# Server2 Candidates Analysis

## Overview

Analyzed file: `server2_candidates_backup.zip` from http://tmpfiles.org/dl/21081888/

This archive contains Bitcoin puzzle candidates generated from bloom filter searches.

**IMPORTANT WARNING:** According to the file header, **ALL candidates are bloom filter FALSE POSITIVES**. These are not actual puzzle keys.

## File Contents

The zip archive contains 2 files:

### 1. candidates_complete.txt (9.3M)
- **Total Addresses:** 25,867
- **Unique Addresses:** 25,082
- **Duplicate Addresses:** 785 (same address from different private keys)
- **Unique Hash160 Values:** 404

### 2. candidates_with_keys.txt (3.4M)
- Contains private keys without computed addresses (requires secp256k1 for EC calculation)
- Marked as reconstructed approximations based on thread ID

## Data Structure

Each candidate in `candidates_complete.txt` includes:
- Source (Range/GPU identifier)
- Private Key (hexadecimal)
- Public Key (uncompressed, 65 bytes)
- Bitcoin Address (P2PKH format)
- Hash160 (RIPEMD160(SHA256(pubkey)))

### Example Entry:
```
Candidate #1
  Source:      Range1_GPU0
  Private Key: 44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b21eb4d40b32a00
  Public Key:  04525b89ca2e703359a25510795986dae420d012090ea7da78c4592f4edb97ad9c...
  Address:     1MynV3QziBPRyQ3J2WpffdjZ4M4c1KfTTA
  Hash160:     9f7369ba2e549b0b3cde20700d8d2453edc2b42f
```

## Analysis: Addresses Starting with "1feex"

### Results:
- **Addresses starting with "1feex":** 0
- **Addresses starting with "1feexv":** 0

This dataset does **NOT** contain any addresses with the "1feex" prefix.

## Hash160 Distribution

The 25,867 addresses map to only **404 unique Hash160 values**, meaning:
- Average ~64 different private keys produce the same Hash160
- This is **HIGHLY UNUSUAL** for random key generation
- Confirms these are bloom filter matches targeting specific Hash160 values

### Sample Hash160 Values:
```
006654442241c5cc443c7648dece52a77370e0e5
021260eb1256a655768ed3e4eb77f10a61c06fe8
02537aff809ce512faabaaa50c1909381edecc7f
031cc216d0151c41412cf66e85a73b52c6dd82b3
06da1af4de7ef1f22692e00b9d6339c001ec4b36
...
```

## Address Prefix Distribution (First 5 Characters)

Top prefixes starting with "1fe":
```
1feik: 2 addresses
1fesh: 1 address
1fezt: 1 address
1fexm: 1 address
1fepv: 1 address
1fe39: 1 address
1feih: 1 address
1fekg: 1 address
1fe69: 1 address
1fesa: 1 address
```

All "1fe" prefixes appear only 1-2 times, showing wide distribution with no concentration on "1feex".

## Comparison with Previous Dataset

### Previous Analysis (from VPS):
- **Source:** catbox.moe parts (part_aa through part_af)
- **Total Addresses:** 12,147,704 unique
- **Addresses with "1feex":** 7
- **Addresses with "1feexv":** 0

### Server2 Candidates:
- **Source:** tmpfiles.org server2_candidates_backup.zip
- **Total Addresses:** 25,082 unique
- **Addresses with "1feex":** 0
- **Addresses with "1feexv":** 0

## Key Differences

| Aspect | VPS Dataset | Server2 Dataset |
|--------|-------------|-----------------|
| Size | 12.1M addresses | 25K addresses |
| Format | Bloom filter candidates | Bloom filter FALSE POSITIVES |
| Hash160 Diversity | High (millions) | Low (404 unique) |
| "1feex" count | 7 | 0 |
| File Source | catbox.moe | tmpfiles.org |
| Purpose | Candidate search | False positive collection |

## Technical Notes

### Why 404 Unique Hash160 Values?

The low number of unique Hash160s (404 for 25,867 addresses) indicates:

1. **Targeted Search:** These keys were generated specifically to produce Hash160 values matching a target set
2. **Bloom Filter Matches:** The bloom filter flagged these as potential matches
3. **False Positives:** All turned out to be false positives (not the actual puzzle keys)
4. **Birthday Paradox:** Multiple private keys can produce the same Hash160 (though extremely rare in random generation)

### Private Key Format

All private keys are 256-bit (64 hex characters):
```
44199b92fdbf3a29a38a7ed650968cdeb3fdb8d09f6e84f47b21eb4d40b32a00
```

## Conclusion

The server2 candidates backup contains a **completely different dataset** from the VPS bloom filter candidates.

Key findings:
- No addresses starting with "1feex" or "1feexv"
- Highly concentrated Hash160 values (404 unique)
- All marked as confirmed false positives
- Much smaller dataset (25K vs 12M addresses)
- Different source and purpose

## Recommendations

If searching for "1feex" or "1feexv" addresses:
1. **Use the VPS dataset** (catbox.moe parts) which contains 7 "1feex" addresses
2. The server2 backup does not contain relevant addresses
3. Consider expanding search to other bloom filter candidate sets

## Files Location

Downloaded to: `/root/repo/root/`
- `candidates_complete.txt` - Full candidate details
- `candidates_with_keys.txt` - Keys without addresses

Original source: http://tmpfiles.org/dl/21081888/server2_candidates_backup.zip
