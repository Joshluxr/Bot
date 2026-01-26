# Addresses Starting with "1feex" - Keyspace Analysis

## Summary

Out of **12,147,704 unique addresses**, there are **7 addresses** starting with "1feex" (case-insensitive).

**Note:** There are **0 addresses** with the exact prefix "1feexv" - the 6th character varies across the 7 addresses.

## Complete List with Private Keys

### [1] 1FEexfuNrhPaSs8exwezpstvarC3MSDN7j
- **Type:** Compressed
- **Private Key (Hex):** `b53ec9e1eb29d0402eb35a46ef505ad012ce27c03d02ac9d6da6f4271877f201`
- **Private Key (Dec):** `81979563453356770746037359084754162925559246477171714229961496311613070242305`
- **WIF:** `L3J2aSRpSWLPkZSDEDVqpHbMZDqZx4GGyU8w9Ka4DTJWDrYJKsRY`

### [2] 1FeeXx39mrWJXU1wJ4Xdu4xyi6E8URXERS
- **Type:** Compressed
- **Private Key (Hex):** `fe1ef9e0309e12806a986cc9d2b9d35425a3d135494639a648e94a0c0dd3a101`
- **Private Key (Dec):** `114942193531081435629910684111945095323508319876805002546292215567443056369921`
- **WIF:** `L5jgui5JDDTyodiDVMf6923iDCHTMyhMCax6fQvTMt3XjqUCpG9x`

### [3] 1FEexaWFK4Z7qBuNCqjqdksLa76NnGfNrp
- **Type:** Uncompressed
- **Private Key (Hex):** `b77c205a702dec47dfdbaebbf2dd0850c6791bb5a48bb0ab8042f5817568ac00`
- **Private Key (Dec):** `82992563620862434352475351947757081565902246292157501334072464625845047700480`
- **WIF:** `5KD6TQy1noTU4rMqqzCXVW8rhRCeB49QYrqXzPVmCwhUEjSi8et`

### [4] 1FEexmCcUj695svca6n7FPwzndQtGMgCYp
- **Type:** Uncompressed
- **Private Key (Hex):** `fe1ef9e0309e12806a986cc9d2b9d35425a3d135494639a648e94a0c0dcd2902`
- **Private Key (Dec):** `114942193531081435629910684111945095323508319876805002546292215567443055945986`
- **WIF:** `5KkCm7b3zbYVH1ALbX4C8i24u9uDKM6WxBs6MwMimcVXxYjyGuY`

### [5] 1FeExKGmgQawDb4dJGbEgHJD51G3k1rSbh
- **Type:** Uncompressed
- **Private Key (Hex):** `b783f271f9bddaf195c24bd390358e2331d2f658c441fe9f095e0e06beed03ff`
- **Private Key (Dec):** `83006381551614476668704001704925337411013586345448656596844062026379096294399`
- **WIF:** `5KD7Eg3sWXrUhAGKcYwiHNRTrMWC9v6MZMsPSuth5wE7wWuQvQm`

### [6] 1FeExMdMnRAvgsARU1oMS6utLUcSNwu8Jn
- **Type:** Uncompressed
- **Private Key (Hex):** `7b46faac2f282e4494886e9b56dc45d366a87435038ff9f33ffd2e1212a375ff`
- **Private Key (Dec):** `55759889748939984167476976690990381959594369969782570707259939409534099092991`
- **WIF:** `5JkaXuhTZddPf3xFeGgP9gTdwABxkW62N19t2NPth1DPJH9Yzvo`

### [7] 1FeeXtuP3tEJpELtFJaF19QtRzpJge1RKD
- **Type:** Uncompressed
- **Private Key (Hex):** `117a80fc9f3ea396e75da8633583519d999682043c6d89b2f267988df782bcff`
- **Private Key (Dec):** `7905764002027863378760312975829580808151779176516965379126368541744006610175`
- **WIF:** `5Hwz3gkin3i8P5kkoLiBD72qV4gfnCZ1Y4hsTPEtN3gpZYNAisi`

## Keyspace Analysis

### Hexadecimal Ranges

Looking at the hex values, the keys span different ranges:

- **Lowest:**  `117a80fc...` (Address #7)
- **Highest:** `fe1ef9e0...` (Address #2 & #4)

The keys are distributed across the Bitcoin keyspace (0 to 2^256-1).

### Decimal Ranges

Sorted by decimal value (smallest to largest):

1. **7,905,764,002,027,863,378,760,312,975,829,580,808,151,779,176,516,965,379,126,368,541,744,006,610,175** (1FeeXtuP...)
2. **55,759,889,748,939,984,167,476,976,690,990,381,959,594,369,969,782,570,707,259,939,409,534,099,092,991** (1FeExMdM...)
3. **81,979,563,453,356,770,746,037,359,084,754,162,925,559,246,477,171,714,229,961,496,311,613,070,242,305** (1FEexfuN...)
4. **82,992,563,620,862434,352,475,351,947,757,081,565,902,246,292,157,501,334,072,464,625,845,047,700,480** (1FEexaWF...)
5. **83,006,381,551,614,476,668,704,001,704,925,337,411,013,586,345,448,656,596,844,062,026,379,096,294,399** (1FeExKGm...)
6. **114,942,193,531,081,435,629,910,684,111,945,095,323,508,319,876,805,002,546,292,215,567,443,055,945,986** (1FEexmCc...)
7. **114,942,193,531,081,435,629,910,684,111,945,095,323,508,319,876,805,002,546,292,215,567,443,056,369,921** (1FeeXx39...)

### Distribution

The keys span approximately:
- **Range:** From ~7.9 × 10^75 to ~1.15 × 10^77
- **Max Bitcoin Key:** 2^256 - 1 ≈ 1.16 × 10^77

These keys are spread across different portions of the Bitcoin keyspace, with addresses #6 and #7 being very close to each other (only differ by 423,935).

## Bit Length Analysis

All keys are 256-bit (or very close):

```
Hex length: 64 characters = 256 bits
```

## Address Format

- **Type:** Legacy Bitcoin addresses (P2PKH)
- **Prefix:** All start with "1"
- **Address Type:** Some are compressed, some are uncompressed public key derivations

## Notes

1. These addresses were found in a bloom filter candidate search
2. None of these addresses matched any funded Bitcoin addresses in the Loyce Club database
3. The 6th character after "1feex" varies: f, x, a, m, K, M, t
4. No addresses with "1feexv" prefix exist in the dataset

## Security Notice

**IMPORTANT:** These private keys are published here for analysis purposes only. Never use these keys for actual Bitcoin storage as they are publicly known and any funds sent to these addresses could be immediately stolen.
