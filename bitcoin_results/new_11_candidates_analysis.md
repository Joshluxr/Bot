# Analysis: 11 New Candidates Against Funded Bitcoin Addresses

**Analysis Date:** 2026-01-26
**Funded Address Database:** Bitcoin_addresses_LATEST.txt.gz (55M+ addresses from Loyce Club)
**Total Candidates Checked:** 11

## Results Summary

**MATCHES FOUND: 0 out of 11**

All 11 candidate addresses were checked against the funded Bitcoin address database. **None of the candidates matched any funded addresses.**

## Detailed Results

| # | Source | Address | Private Key | Match |
|---|--------|---------|-------------|-------|
| 1 | S1-GPU3 | 1J9gUvxqtZz7yEYgw9NEVx4BtHVWCzC4LN | 0x7b46faac2f282e4494886e9b56dc45d366a87435038ff9f33ffd2e120cbc20ad | ❌ NO |
| 2 | S1-GPU3 | 1NXVMt6GEBgwur7Ukfc3k6mYoPzuq4q7Ak | 0x84b90553d0d7d1bb6b779164a923ba2b540668b1abb8a6487fd5307ac37a8377 | ❌ NO |
| 3 | S1-GPU3 | 1FKuLGS41rYGy3FzSNNJ3bzSQsxaskbx94 | 0x7b46faac2f282e4494886e9b56dc45d366a87435038ff9f33ffd2e120cbbfcb2 | ❌ NO |
| 4 | S1-GPU4 | 169EvKLbLcNpNWPMFfz4mCTzqLfRn8LS9F | 0xb3d74c168e3eca3a299d699924449b6ed5fb1fd38ce9a7bc302fd4f5fa355a41 | ❌ NO |
| 5 | S1-GPU5 | 1HkdA4qBdsfNXMjAreTzjs2acucpT8XkHR | 0xb53ec9e1eb29d0402eb35a46ef505ad012ce27c03d02ac9d6da6f427144885aa | ❌ NO |
| 6 | S1-GPU7 | 17prTxkmDG4LeDBYtaRv1155sUHdsQxhtr | 0xfe1ef9e0309e12806a986cc9d2b9d35425a3d135494639a648e94a0c0a778bf3 | ❌ NO |
| 7 | S1-GPU7 | 1PSdm5jw3DkXZBZvtMfAuS9Fxxo9D84gta | 0x01e1061fcf61ed7f956793362d462caa950b0bb16602669576e91480c5be88de | ❌ NO |
| 8 | S1-GPU7 | 1DDx9YcmcsRsVgbJpC3fWNH9RFMCeVFu5m | 0xfe1ef9e0309e12806a986cc9d2b9d35425a3d135494639a648e94a0c0a778f67 | ❌ NO |
| 9 | S2-GPU0 | 1JppKKHxp8oczSdYEa4i59AdyeABoou2F5 | 0x637d18efcf30e1aea1452d0595c73aa299916abe7f1ec8000000000000007a69 | ❌ NO |
| 10 | S2-GPU1 | 13URqG5AVzULjLsQWa7gLnekxaMQGVvkQS | 0x6e8aff4357fd6c8924f7875b89f9cf5f554c3db737e95000000000000000932d | ❌ NO |
| 11 | S2-GPU1 | 1MZPAFkZkxmUNWaXaC6Edkav6LwjxhVzGG | 0x917500bca8029376db0878a47606309f65629f2f775f503bbfd25e8cd035d7cc | ❌ NO |

## Private Key Pattern Analysis

### Server 1 Keys (Candidates 1-8)
The Server 1 keys show varied patterns across the full 256-bit keyspace:
- Keys range from `0x01e1...` to `0xfe1e...`
- No obvious systematic pattern
- Appear to be from different GPU search ranges

### Server 2 Keys (Candidates 9-11)
**NOTABLE PATTERN DETECTED:**
- Candidate #9: `0x637d18efcf30e1aea1452d0595c73aa299916abe7f1ec8000000000000007a69`
- Candidate #10: `0x6e8aff4357fd6c8924f7875b89f9cf5f554c3db737e95000000000000000932d`

These keys have **trailing zeros**, suggesting:
1. Systematic keyspace search with specific ranges
2. Possible bloom filter search with limited precision
3. GPU-based generation with aligned memory patterns

Candidate #11 appears more random: `0x917500bca8029376db0878a47606309f65629f2f775f503bbfd25e8cd035d7cc`

## Address Prefix Analysis

The 11 addresses have the following starting patterns:
- `1J` - 2 addresses
- `1N`, `1F`, `16`, `1H`, `17`, `1P`, `1D`, `13`, `1M` - 1 each

No unusual clustering in address prefixes.

## Conclusions

1. **Zero Funded Matches**: Consistent with previous analyses - no bloom filter candidates have matched funded addresses
2. **Bloom Filter False Positives**: These candidates are likely false positives from bloom filter searches
3. **Systematic Search Patterns**: Server 2 keys show trailing zeros, indicating systematic keyspace exploration
4. **Security Confirmation**: Bitcoin's cryptographic security remains intact - random/systematic searches continue to find zero funded addresses

## Statistical Context

**Total candidates analyzed to date:**
- Server 1 original: 27,208 addresses
- Server 2 original: 25,867 addresses
- WIF keys: 155 addresses
- This batch: 11 addresses
- **Grand Total: 53,241 candidate addresses**

**Funded matches found: 0**

This is statistically expected given:
- Bitcoin address space: ~2^160 ≈ 1.46 × 10^48 addresses
- Funded addresses: ~55 million ≈ 5.5 × 10^7
- Probability of random match: ~3.8 × 10^-41 per attempt

## Recommendation

Continue monitoring new candidates, but current evidence strongly suggests:
- These are bloom filter false positives
- No vulnerability in Bitcoin's cryptographic security
- Keyspace search methods are not viable for recovering funded addresses
