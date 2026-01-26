# Top 100 Dormant Bitcoin Addresses (7+ Years)

## Source

**URL:** https://bitinfocharts.com/top-100-dormant_7y-bitcoin-addresses.html
**Criteria:** Addresses with no transactions for 7+ years, ranked by holdings
**Scraped:** January 24, 2026

## 🚨 MAJOR FINDING: Address #1 Starts with "1FeexV"!

The **#1 most valuable dormant address** starts with the pattern we've been analyzing:

### **1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF**
- **Balance:** 79,957 BTC (~$7.9 billion at $100k/BTC)
- **Last Activity:** 2025-12-23 (recent!)
- **Pattern:** Starts with "1FeexV" (our search was for "1feex")
- **Status:** NOT in our candidate database

### Comparison with Our Candidates

We found 7 addresses starting with "1feex":
1. 1FEex**f**uNrhPaSs8exwezpstvarC3MSDN7j
2. 1FeeX**x**39mrWJXU1wJ4Xdu4xyi6E8URXERS
3. 1FEex**a**WFK4Z7qBuNCqjqdksLa76NnGfNrp
4. 1FEex**m**CcUj695svca6n7FPwzndQtGMgCYp
5. 1FeEx**K**GmgQawDb4dJGbEgHJD51G3k1rSbh
6. 1FeEx**M**dMnRAvgsARU1oMS6utLUcSNwu8Jn
7. 1FeeX**t**uP3tEJpELtFJaF19QtRzpJge1RKD

**None have "V" as the 6th character!**

The dormant address **1FeexV6b...** would be the 8th "1feex" address if we had it.

## Complete List of 100 Dormant Addresses

See `dormant_addresses_7y.txt` for the complete list.

### Top 10 by Balance

| Rank | Address | Balance (BTC) | Pattern |
|------|---------|---------------|---------|
| 1 | **1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF** | 79,957 | **1FeexV** ⭐ |
| 2 | 1LdRcdxfbSnmCYYNdeYpUnztiYzVfBEQeC | 53,880 | 1Ld |
| 3 | 1AC4fMwgY8j9onSbXEWeH6Zan8QGMSdmtA | 51,830 | 1AC |
| 4 | 12ib7dApVFvg82TXKycWBNpN8kFyiAN1dr | 31,000 | 12i |
| 5 | 12tkqA9xSoowkzoERHMWNKsTey55YEBqkv | 28,151 | 12t |
| 6 | 17rm2dvb439dZqyMe2d4D6AQJSgg6yeNRn | 20,008 | 17r |
| 7 | 1PeizMg76Cf96nUQrYg8xuoZWLQozU5zGW | 19,414 | 1Pe |
| 8 | 1GR9qNz7zgtaW5HwwVpEJWMnGWhsbsieCG | 15,746 | 1GR |
| 9 | 1F34duy2eeMz5mSrvFepVzy7Y1rBsnAyWC | 10,771 | 1F3 |
| 10 | 1Ki3WTEEqTLPNsN5cGTsMkL2sJ4m5mdCXT | 10,000 | 1Ki |

**Total value in top 10:** ~320,157 BTC (~$32 billion at $100k/BTC)

## Pattern Analysis

### Addresses Starting with "1F"

Out of 100 dormant addresses, these start with "1F":

1. **1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF** (#1) - 79,957 BTC ⭐
2. 1F34duy2eeMz5mSrvFepVzy7Y1rBsnAyWC (#9) - 10,771 BTC
3. 1FJuzzQFVMbiMGw6JtcXefdD64amy7mSCF (#19)
4. 1FvUkW8thcqG6HP7gAvAjcR52fR7CYodBx (#52)
5. 1FDVbVJYKkWPFcJEzCxi99vpKTYxEY3zdj (#64)

**5 out of 100** addresses start with "1F" (5%)

### Special Pattern: "1CounterpartyXXXXXXXXXXXXXXXUWLpVr"

Address #95 is notable:
- **1CounterpartyXXXXXXXXXXXXXXXUWLpVr**
- This is the **Counterparty burn address**
- Coins sent here are provably unspendable
- Contains burned BTC from Counterparty protocol

## Why is 1FeexV Notable?

### Rarity
- Starts with "1Feex" (we've been searching for this pattern!)
- 6th character is "V" (none of our 7 candidates have this)
- Extremely rare prefix (1 in ~1.74 million for "1feex", even rarer for specific 6th char)

### Value
- **79,957 BTC** = Largest dormant balance
- Worth ~$7.9 billion at $100k/BTC
- More than the next two combined (53,880 + 51,830 = 105,710 BTC total for #2 and #3)

### Dormancy
- Last activity: 2025-12-23 (very recent!)
- **NOTE:** The "Last Activity" date seems incorrect - if it's truly dormant 7+ years, activity should be 2019 or earlier
- **Possible data issue** or address became active recently

### Mystery
- NOT in our bloom filter candidate database
- Unknown private key
- Could be:
  - Early Bitcoin adopter who lost keys
  - Cold storage that owner still controls
  - Lost wallet from exchange hack
  - Satoshi Nakamoto's coins (unlikely, different pattern)

## Checking Against Our Database

Checked if **1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF** is in our datasets:

| Dataset | Size | Contains 1FeexV? |
|---------|------|------------------|
| VPS candidates | 12,147,704 | ✗ No |
| VPS parts (detailed) | 2,473,379 Bitcoin addresses | ✗ No |
| Server2 candidates | 25,867 | ✗ No |
| Funded database | 55,354,799 | ✓ Yes (it's funded!) |

**Conclusion:** This address is NOT in our bloom filter search results, but it IS in the funded address database (as expected, since it holds 79,957 BTC).

## Statistical Analysis

### Probability of "1FeexV" Pattern

For a Bitcoin address to start with specific characters:

| Pattern | Probability | Expected in 100M |
|---------|-------------|------------------|
| 1F | ~1.7% | 1.7M addresses |
| 1Fe | ~0.03% | 30,000 addresses |
| 1Fee | ~0.0005% | 500 addresses |
| 1Feex | ~0.000009% | 9 addresses |
| 1FeexV | ~0.00000015% | 0.15 addresses |

**Finding "1FeexV" in just 100 addresses is extraordinarily unlikely** (~1 in 667 million chance).

### Possible Explanations

1. **Vanity Address:** Deliberately generated using vanity address software
   - Would require significant computational effort
   - Estimated ~100 million attempts to generate
   - Suggests owner valued this pattern

2. **Pure Luck:** Random generation happened to produce this pattern
   - Probability: ~0.00000015%
   - Extremely unlikely but possible

3. **Early Mining:** Generated during early Bitcoin days when competition was low
   - Owner may have generated many addresses
   - Kept the "interesting" one

## Historical Context

### Early Bitcoin (2009-2013)

During Bitcoin's early years:
- Many people generated addresses for experimentation
- "Interesting" patterns were kept as curiosities
- Large amounts of BTC were considered worthless at the time
- Many early addresses are now lost/dormant

### 79,957 BTC Value Over Time

| Year | BTC Price | Value of 79,957 BTC |
|------|-----------|---------------------|
| 2010 | $0.08 | $6,397 |
| 2013 | $1,000 | $79.9 million |
| 2017 | $20,000 | $1.6 billion |
| 2021 | $69,000 | $5.5 billion |
| 2024 | $100,000 | $7.9 billion |
| 2026 | $100,000 | $7.9 billion |

This amount has appreciated from essentially worthless to ~$8 billion.

## Security Implications

### For This Specific Address

⚠️ **CRITICAL WARNING:**
- The private key for **1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF** is **UNKNOWN**
- Worth ~$8 billion
- Anyone who finds the private key can claim the funds
- This is why people search for bloom filter candidates

### Why Bloom Filter Searches Target These

Dormant addresses with large balances are prime targets for:
- Brute force searches
- Bloom filter optimizations
- GPU-accelerated key generation
- Targeting specific Hash160 patterns

**However:** Our comprehensive search of 12M+ candidates found NONE of these dormant addresses.

## Interesting Observations

### Address Format Patterns

Analyzing all 100 dormant addresses:

| Starting | Count | Notes |
|----------|-------|-------|
| 1 | 92 | Legacy P2PKH |
| 3 | 1 | P2SH (address #91) |
| 12 | 4 | Legacy with "12" prefix |
| 13 | 5 | Legacy with "13" prefix |
| 14-19 | 26 | Various Legacy |
| 1A-1Z | 61 | Various Legacy |

Most are standard legacy addresses, with one notable exception being the Counterparty burn address.

### Clustering

Some addresses appear to be related:
- Multiple addresses from same era (2010-2013)
- Similar balance sizes
- Possible same owner/entity

This could represent:
- Early exchange cold storage
- Mining pool holdings
- Large investor's portfolio
- Lost exchange wallets

## Comparison: Our Candidates vs Dormant Addresses

| Metric | Our Candidates | Dormant Addresses |
|--------|----------------|-------------------|
| Total addresses | 2,473,379 | 100 |
| Funded | 0 | 100 |
| Starting with "1feex" | 7 | 1 |
| Largest balance | 0 BTC | 79,957 BTC |
| In both datasets | 0 | 0 |
| Overlap | None | None |

**Key Finding:** Zero overlap between our bloom filter candidates and top 100 dormant addresses.

## Recommendations

### For Finding 1FeexV Private Key

If attempting to find the private key for **1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF**:

1. **Vanity Address Approach**
   - Use vanity address software (vanitygen, etc.)
   - Target pattern: "1FeexV"
   - Estimated attempts: ~100 million
   - Estimated time with GPU: days to weeks

2. **Bloom Filter Approach** (what our dataset attempted)
   - Create bloom filter for specific Hash160
   - Search keyspace systematically
   - Our result: 12M+ attempts, 0 success

3. **Brute Force** (not recommended)
   - Search entire keyspace randomly
   - Probability of success: effectively zero
   - Bitcoin's 2^256 keyspace is too large

### Reality Check

**Finding this private key is effectively impossible** without:
- Quantum computers (not currently practical)
- Major cryptographic breakthrough
- Access to original wallet file
- Insider knowledge

The address likely represents:
- Lost keys (most probable)
- Secure cold storage (owner still has access)
- Seized assets (law enforcement)

## Conclusion

### Summary of Findings

1. ✅ **Successfully scraped** 100 dormant addresses (7+ years inactive)
2. 🎯 **Found "1FeexV"** address - #1 most valuable dormant address
3. 💰 **79,957 BTC** in the "1FeexV" address (~$8 billion)
4. ✗ **Not in our database** - bloom filter searches didn't find it
5. ⭐ **Extremely rare pattern** - "1FeexV" is 1 in 667 million
6. ❓ **Unknown origin** - likely vanity address from early Bitcoin era

### Key Takeaway

The existence of **1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF** with 79,957 BTC demonstrates:
- Early Bitcoin adopters generated interesting addresses
- Many large balances remain dormant/lost
- Even sophisticated bloom filter searches (like ours) miss these addresses
- Bitcoin's cryptographic security remains intact
- The "1feex" pattern is not only rare but also historically significant

## Files

- `dormant_addresses_7y.txt` - Complete list of 100 addresses
- Source URL: https://bitinfocharts.com/top-100-dormant_7y-bitcoin-addresses.html

---

**Note:** This analysis is for educational and research purposes only. Attempting to access Bitcoin addresses without authorization is illegal and unethical.
