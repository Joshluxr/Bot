# Full Keyspace Storage System Design

## Overview
Store EVERY key checked during the search, not just bloom filter candidates. This creates a complete audit trail of the entire keyspace searched.

## What We're Storing

For every single key checked:
```
1. Private Key (decimal)    - The actual key number
2. Hash160                  - RIPEMD160(SHA256(pubkey))
3. Compressed Public Key    - 33 bytes (02/03 + x coordinate)
4. Bitcoin Address          - Base58Check encoded address
5. Metadata                 - server_id, gpu_id, timestamp
```

## Data Volume Reality Check

This is MASSIVE - let's calculate:

```
Current Speed: 36 GKey/s (will be ~100 GKey/s)
Keys per second: 36,000,000,000

Storage per key:
- Private key:       32 bytes (or ~78 bytes as decimal string)
- Hash160:          20 bytes
- Compressed pubkey: 33 bytes
- BTC address:      34 bytes (average)
- Metadata:         12 bytes (server, gpu, timestamp)
- Total per key:    ~131 bytes (binary) or ~209 bytes (with decimal string)

Let's use 150 bytes average per key with compression
```

### Storage Requirements

```
Per second:   36,000,000,000 keys × 150 bytes = 5,400 GB/s = 5.4 TB/second
Per minute:   5.4 TB × 60 = 324 TB/minute
Per hour:     324 TB × 60 = 19,440 TB/hour = 19.4 PB/hour
Per day:      19.4 PB × 24 = 466 PB/day
Per week:     466 PB × 7 = 3,262 PB/week = 3.2 Exabytes/week
```

**⚠️ THIS IS IMPOSSIBLY LARGE**

Even at the current 36 GKey/s, you need to write **5.4 TB per second**.

## The Fundamental Problem

**No storage system can write 5.4 TB/second continuously.**

For reference:
- Fastest NVMe SSD: ~7 GB/s sequential write
- You need: 5,400 GB/s (771x faster than best SSD)
- Even with 1000 SSDs in parallel: Still not enough

## Realistic Solutions

### Solution 1: Range-Based Storage (RECOMMENDED)

Instead of storing every key, store **ranges** of keys checked:

```sql
CREATE TABLE keyspace_ranges (
    range_id BIGSERIAL PRIMARY KEY,
    start_key NUMERIC(78,0),  -- First key in range
    end_key NUMERIC(78,0),    -- Last key in range
    keys_count BIGINT,        -- Number of keys (usually 1 trillion)
    server_id SMALLINT,
    gpu_id SMALLINT,
    checked_at TIMESTAMPTZ,
    -- Store start/end addresses for reference
    start_address VARCHAR(35),
    end_address VARCHAR(35),
    start_hash160 BYTEA,
    end_hash160 BYTEA
);

-- Storage per range (1 trillion keys):
-- ~200 bytes per range
-- 1 trillion keys = 1 record

-- At 36 GKey/s:
-- 36,000,000,000 keys/sec = 0.036 ranges/sec = 129 ranges/hour
-- Storage: 129 ranges × 200 bytes = 25.8 KB/hour
-- Per day: 3,110 ranges × 200 bytes = 622 KB/day
-- Per year: ~227 MB/year
```

**This is 99.9999999% smaller and actually feasible!**

### Solution 2: Probabilistic Sampling

Store a random sample (e.g., 1 in 1 million keys):

```python
# In K3 search loop
if random.random() < 0.000001:  # 1 in 1 million
    store_full_key_data(key)

# Storage with sampling:
# 36 billion keys/sec × 0.000001 = 36,000 samples/sec
# 36,000 × 150 bytes = 5.4 MB/sec = 466 GB/day
```

Still very large but technically possible.

### Solution 3: Hierarchical Storage

Store different granularities:

```sql
-- Level 1: Coarse ranges (every 1 trillion keys)
CREATE TABLE keyspace_coarse (
    start_key NUMERIC(78,0),
    end_key NUMERIC(78,0),
    checked_at TIMESTAMPTZ
);

-- Level 2: Medium ranges (every 1 billion keys) - for important areas
CREATE TABLE keyspace_medium (
    start_key NUMERIC(78,0),
    end_key NUMERIC(78,0),
    start_hash160 BYTEA,
    end_hash160 BYTEA,
    checked_at TIMESTAMPTZ
);

-- Level 3: Individual keys - ONLY for candidates/matches
CREATE TABLE keyspace_keys (
    privkey NUMERIC(78,0),
    hash160 BYTEA,
    compressed_pubkey BYTEA,
    btc_address VARCHAR(35),
    is_match BOOLEAN,
    checked_at TIMESTAMPTZ
);
```

### Solution 4: Compressed Delta Encoding

Store sequential keys with delta compression:

```python
# Instead of storing:
# Key 1000000000000000
# Key 1000000000000001
# Key 1000000000000002

# Store:
# Base: 1000000000000000
# Deltas: +1, +1, +1

# With run-length encoding:
# Base: 1000000000000000
# Count: 1000000 consecutive keys

# Compression ratio: ~1,000,000:1
```

## Practical Hybrid Approach

Combine the best of all solutions:

```sql
-- 1. Store ranges checked (very compact)
CREATE TABLE checked_ranges (
    id BIGSERIAL PRIMARY KEY,
    start_privkey NUMERIC(78,0),
    end_privkey NUMERIC(78,0),
    keys_count BIGINT,
    server_id SMALLINT,
    gpu_id SMALLINT,
    checked_at TIMESTAMPTZ,
    INDEX idx_range_lookup btree(start_privkey, end_privkey)
);

-- 2. Store boundary keys for each range
CREATE TABLE range_boundaries (
    range_id BIGINT REFERENCES checked_ranges(id),
    position VARCHAR(10),  -- 'start' or 'end'
    privkey NUMERIC(78,0),
    hash160 BYTEA,
    pubkey BYTEA,
    address VARCHAR(35)
);

-- 3. Store ALL bloom filter candidates
CREATE TABLE candidates (
    id BIGSERIAL PRIMARY KEY,
    privkey NUMERIC(78,0),
    hash160 BYTEA,
    pubkey BYTEA,
    address VARCHAR(35),
    server_id SMALLINT,
    gpu_id SMALLINT,
    found_at TIMESTAMPTZ,
    is_verified BOOLEAN DEFAULT FALSE,
    is_match BOOLEAN DEFAULT FALSE
);

-- 4. Store statistical samples (1 in 1M)
CREATE TABLE key_samples (
    privkey NUMERIC(78,0),
    hash160 BYTEA,
    address VARCHAR(35),
    sampled_at TIMESTAMPTZ
) PARTITION BY RANGE (sampled_at);
```

## Storage Requirements - Hybrid Approach

```
1. Checked Ranges:
   - 129 ranges/hour × 200 bytes = 25.8 KB/hour
   - ~227 MB/year

2. Boundary Keys:
   - 129 ranges × 2 boundaries × 150 bytes = 38.7 KB/hour
   - ~340 MB/year

3. Candidates:
   - ~3.3M candidates currently
   - At 36 GKey/s: ~36,000 candidates/sec × 150 bytes = 5.4 MB/sec
   - ~466 GB/day
   - With verification filter: ~5 GB/day (99% filtered out)

4. Statistical Samples (1 in 1M):
   - 36,000 samples/sec × 150 bytes = 5.4 MB/sec
   - ~466 GB/day

Total: ~500 GB/day with sampling
       ~5 GB/day without sampling (just ranges + candidates)
```

## Implementation: Modified K3 Binary

```cpp
// Global counters
uint64_t keys_in_current_range = 0;
uint64_t range_start_key = 0;
bool range_started = false;

// In search loop
void process_key(uint8_t *privkey, uint8_t *pubkey, uint8_t *hash160) {

    // Start new range tracking
    if (!range_started) {
        range_start_key = *(uint64_t*)privkey;  // Simplified
        range_started = true;
    }

    keys_in_current_range++;

    // Check bloom filter
    bool is_candidate = check_bloom_filter(hash160);

    if (is_candidate) {
        // Send full candidate data
        send_candidate_to_server(privkey, pubkey, hash160);
    }

    // Optional: Statistical sampling (1 in 1M)
    if (keys_in_current_range % 1000000 == 0) {
        send_sample_to_server(privkey, pubkey, hash160);
    }

    // Report range every 1 trillion keys
    if (keys_in_current_range >= 1000000000000ULL) {
        send_range_report(range_start_key, privkey, keys_in_current_range);
        keys_in_current_range = 0;
        range_started = false;
    }
}

struct RangeReport {
    uint8_t start_privkey[32];
    uint8_t end_privkey[32];
    uint64_t keys_checked;
    uint16_t server_id;
    uint16_t gpu_id;
    uint64_t timestamp;
} __attribute__((packed));

struct CandidateReport {
    uint8_t privkey[32];
    uint8_t hash160[20];
    uint8_t compressed_pubkey[33];
    uint16_t server_id;
    uint16_t gpu_id;
    uint64_t timestamp;
} __attribute__((packed));
```

## Collection Server Implementation

```python
import asyncio
import asyncpg
from dataclasses import dataclass
import hashlib
import base58

class KeyspaceCollector:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.candidate_batch = []
        self.sample_batch = []
        self.batch_size = 1000

    async def handle_range_report(self, data: bytes):
        """Store range checked"""
        start_key = int.from_bytes(data[0:32], 'big')
        end_key = int.from_bytes(data[32:64], 'big')
        keys_checked = int.from_bytes(data[64:72], 'big')
        server_id = int.from_bytes(data[72:74], 'big')
        gpu_id = int.from_bytes(data[74:76], 'big')
        timestamp = int.from_bytes(data[76:84], 'big')

        # Compute addresses for boundaries
        start_address = self.privkey_to_address(start_key)
        end_address = self.privkey_to_address(end_key)
        start_hash160 = self.privkey_to_hash160(start_key)
        end_hash160 = self.privkey_to_hash160(end_key)

        async with self.db_pool.acquire() as conn:
            range_id = await conn.fetchval(
                '''
                INSERT INTO checked_ranges
                (start_privkey, end_privkey, keys_count, server_id, gpu_id, checked_at)
                VALUES ($1, $2, $3, $4, $5, to_timestamp($6))
                RETURNING id
                ''',
                start_key, end_key, keys_checked, server_id, gpu_id, timestamp
            )

            # Store boundaries
            await conn.execute(
                '''
                INSERT INTO range_boundaries
                (range_id, position, privkey, hash160, address)
                VALUES
                    ($1, 'start', $2, $3, $4),
                    ($1, 'end', $5, $6, $7)
                ''',
                range_id, start_key, start_hash160, start_address,
                end_key, end_hash160, end_address
            )

        print(f"Range stored: {start_key} to {end_key} ({keys_checked:,} keys)")

    async def handle_candidate(self, data: bytes):
        """Store candidate key"""
        privkey = int.from_bytes(data[0:32], 'big')
        hash160 = data[32:52]
        pubkey = data[52:85]
        server_id = int.from_bytes(data[85:87], 'big')
        gpu_id = int.from_bytes(data[87:89], 'big')
        timestamp = int.from_bytes(data[89:97], 'big')

        # Generate Bitcoin address
        address = self.pubkey_to_address(pubkey)

        self.candidate_batch.append((
            privkey, hash160, pubkey, address, server_id, gpu_id, timestamp
        ))

        if len(self.candidate_batch) >= self.batch_size:
            await self.flush_candidates()

    async def flush_candidates(self):
        """Batch insert candidates"""
        if not self.candidate_batch:
            return

        async with self.db_pool.acquire() as conn:
            await conn.executemany(
                '''
                INSERT INTO candidates
                (privkey, hash160, pubkey, address, server_id, gpu_id, found_at)
                VALUES ($1, $2, $3, $4, $5, $6, to_timestamp($7))
                ''',
                self.candidate_batch
            )

        print(f"Stored {len(self.candidate_batch)} candidates")
        self.candidate_batch.clear()

    def privkey_to_address(self, privkey: int) -> str:
        """Compute Bitcoin address from private key"""
        # This is simplified - you'd use proper secp256k1
        import ecdsa

        sk = ecdsa.SigningKey.from_string(
            privkey.to_bytes(32, 'big'),
            curve=ecdsa.SECP256k1
        )
        vk = sk.get_verifying_key()

        # Compressed public key
        x = vk.pubkey.point.x()
        y = vk.pubkey.point.y()
        prefix = b'\x02' if y % 2 == 0 else b'\x03'
        pubkey = prefix + x.to_bytes(32, 'big')

        return self.pubkey_to_address(pubkey)

    def pubkey_to_address(self, pubkey: bytes) -> str:
        """Convert public key to Bitcoin address"""
        # SHA256
        sha = hashlib.sha256(pubkey).digest()
        # RIPEMD160
        ripe = hashlib.new('ripemd160')
        ripe.update(sha)
        hash160 = ripe.digest()

        # Add version byte
        versioned = b'\x00' + hash160

        # Checksum
        checksum = hashlib.sha256(
            hashlib.sha256(versioned).digest()
        ).digest()[:4]

        # Base58 encode
        return base58.b58encode(versioned + checksum).decode('ascii')

    def privkey_to_hash160(self, privkey: int) -> bytes:
        """Compute hash160 from private key"""
        address = self.privkey_to_address(privkey)
        # Decode and extract hash160
        decoded = base58.b58decode(address)
        return decoded[1:21]  # Skip version byte, take 20 bytes
```

## Query Capabilities

With this system, you can:

```sql
-- Check if a specific key range was searched
SELECT * FROM checked_ranges
WHERE $1 >= start_privkey AND $1 <= end_privkey;

-- Get all candidates in a range
SELECT * FROM candidates
WHERE privkey >= $1 AND privkey <= $2;

-- Find matches
SELECT * FROM candidates WHERE is_match = TRUE;

-- Statistics
SELECT
    server_id,
    COUNT(*) as ranges_checked,
    SUM(keys_count) as total_keys
FROM checked_ranges
GROUP BY server_id;

-- Coverage analysis
SELECT
    MIN(start_privkey) as first_key,
    MAX(end_privkey) as last_key,
    SUM(keys_count) as total_coverage
FROM checked_ranges;
```

## Recommended Deployment

**Minimum viable system:**
1. Store ranges checked (< 1 GB/year)
2. Store all candidates (5-50 GB/day depending on filtering)
3. Query to verify coverage and find matches

**Enhanced system:**
1. Add statistical sampling (1 in 1M) for spot checks
2. Add verification against real address list
3. Partition tables by time for management
4. Set up archival to cold storage after 30 days

**Storage cost:**
- Basic: 2TB SSD (~$200) good for months
- Enhanced: 10TB HDD (~$200) good for longer term

This is actually feasible! The key insight is you DON'T need to store every single key - storing ranges gives you complete coverage proof at 0.0000001% of the storage cost.

Would you like me to create the database setup scripts and full implementation?
