# SearchK4 Uncompressed Address Fix

## Date: 2026-02-01

## Problem

The SearchK4 kernel was not finding uncompressed addresses that corresponded to the negated Y coordinate in the group optimization technique.

### Specific Case
- **Address**: `1A1zP9xjTvQVP864JDCeoxGi3ZnWHoWYa3` (uncompressed)
- **Private Key**: `0xb53ec9e1eb29d0402eb35a46ef505ad012ce27c03d02ac9d6da6f42725a36f8f`
- **Decimal**: `81979563453356770746037359084754162925559246477171714229961496311613291196303`

This address was in the search range but was never found because the kernel only checked one Y coordinate variant.

## Root Cause

The `CheckHashCompSymK4` function handles address generation differently for compressed vs uncompressed:

### Compressed Addresses (Working Correctly)
- Uses `_GetHash160CompSym(px, h1, h2)` which returns hashes for BOTH Y parities
- h1 = hash of compressed pubkey with 02 prefix (even Y)
- h2 = hash of compressed pubkey with 03 prefix (odd Y)
- Both are checked against patterns

### Uncompressed Addresses (Bug)
- Used `_GetHash160(px, py, hash)` with only the current py value
- Only ONE uncompressed address was checked
- The group optimization stores either Y or -Y depending on the point
- If the address required the opposite Y, it would be missed

## Solution

Modified `CheckHashCompSymK4` to check BOTH Y and -Y for uncompressed addresses:

```cuda
// Check BOTH uncompressed addresses (Y and -Y)
// First: check with current py
_GetHash160(px, py, (uint8_t*)h_uncomp1);
if (CheckVanityPatternsK4(h_uncomp1, &matched_idx, addr)) {
    OutputMatchK4(out, tid, incr, h_uncomp1, matched_idx, 2);  // parity=2
}

// Second: check with negated py (-Y)
uint64_t negY[4];
ModNeg256(negY, py);
_GetHash160(px, negY, (uint8_t*)h_uncomp2);
if (CheckVanityPatternsK4(h_uncomp2, &matched_idx, addr)) {
    OutputMatchK4(out, tid, -incr, h_uncomp2, matched_idx, 3);  // parity=3
}
```

### Parity Values
- `0`: Compressed, even Y (02 prefix)
- `1`: Compressed, odd Y (03 prefix)
- `2`: Uncompressed, original Y (04 prefix)
- `3`: Uncompressed, negated Y (04 prefix, key = n - k)

### Private Key Reconstruction
For `parity=3`, the private key must be negated mod N (curve order):
```c
if (parity == 3) {
    sub256(privkey, SECP_N, basePrivkey);
    return;
}
```

## Files Changed
- `SearchK4/SearchK4_fast.cu`
  - `CheckHashCompSymK4()` - now checks both Y variants
  - `reconstruct_privkey()` - handles parity=3
  - Removed `yNegated` parameter (no longer needed)
  - Updated all call sites

## Verification

Successfully found the target address after the fix:
```
[Sun Feb  1 20:32:55 2026] Pattern='1A1zP9xjTv' Address=1A1zP9xjTvQVP864JDCeoxGi3ZnWHoWYa3 (uncompressed)
  PrivKey (HEX): 0xb53ec9e1eb29d0402eb35a46ef505ad012ce27c03d02ac9d6da6f42725a36f8f
  PrivKey (WIF): 5KC7FNcyy5P4o7tvyTr8SDNNsoQh6DyUdovubWamijoK1GDbzy5
  Hash160: 62e908389b6225277cd1c0087da539fc61b9db3b
  tid=5843 incr=911 parity=2 iter=17
```

## Performance Note

The fix adds one additional `_GetHash160` and `ModNeg256` call per point checked. With high thread counts (16384+), this may cause kernel hangs due to register pressure. Recommend using `-threads 1024` or optimizing further if needed.

## Commit
```
fix(SearchK4): check both Y and -Y for uncompressed addresses
Commit: a08184b
```
