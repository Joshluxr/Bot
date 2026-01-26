# Address Format Analysis

## Issue Identified

The candidate files contain **address,private_key pairs**, not just addresses. The matching script needs to extract only the address portion (before the comma).

## Format Comparison

### Candidate Files Format
```
address,private_key
```

**Examples:**
```
Server 1: 1111fZkz4nR5KDw1CFjMYH42YkJ5NaBn,5JVEX39jWPEnVcC7PouMETALAPkFarpRtRX1MyZcruue8h2f59o
Server 2: 115re9tpb57fWQso8EPDKmHMY8E3CJEgk,5KBVNusnnAyijeJu76GSYUDbfmRruXGhJmoBUhzmnLvKiAkhTnB
Server 4: 1115QmPagyfbyvxupi1MHQ12i2sBQkZSY,5KkCm7b3zbYVH1ALbX4C8i24u9uDKM6WxBs4qqekW6irgFvHMMB
```

### Funded Database Format
```
address_only
```

**Examples:**
```
1111111111111111111114oLvT2
111111111111111111112BEH2ro
111111111111111111112czxoHN
```

## Problem

The matching script was comparing:
- **Candidates:** `"1111fZkz4nR5KDw1CFjMYH42YkJ5NaBn,5JVEX39j..."` (full line with comma and key)
- **Funded DB:** `"1111111111111111111114oLvT2"` (address only)

These will never match because of the format difference!

## Solution

Need to re-run the matching with address extraction:
1. Split each candidate line by comma
2. Take only the first part (the address)
3. Then compare against funded database

## Fixed Script Coming

Creating corrected matching script that properly extracts addresses from the CSV format...
