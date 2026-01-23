# Keyspace Tracking System Design

## Overview
System to track every key checked during the BTC K3 search, storing batches in a fast database for audit trail and preventing duplicate searches.

## Architecture

### Components

```
┌─────────────────┐
│  GPU Servers    │  (Servers 1, 2, 3)
│  8-20 GPUs      │
│  ~36-100 GKey/s │
└────────┬────────┘
         │ Batch reports every 1T keys
         │ (UDP/TCP stream)
         ▼
┌─────────────────────────┐
│  Collection Server      │
│  - Receives key ranges  │
│  - Validates & batches  │
│  - Writes to database   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Fast Database          │
│  Options:               │
│  - ScyllaDB/Cassandra   │
│  - Redis + persistence  │
│  - TimescaleDB          │
│  - ClickHouse           │
└─────────────────────────┘
```

## Data Volume Calculations

```
Current total speed: 36 GKey/s (will be ~100 GKey/s with all servers)

Keys per second:     36,000,000,000 keys/s
Keys per hour:       129,600,000,000,000 keys/hour (129.6 trillion)
Keys per day:        3,110,400,000,000,000 keys/day (3.1 quadrillion)

Batch size:          1,000,000,000,000 keys (1 trillion)
Batches per hour:    ~130 batches/hour
Batches per day:     ~3,110 batches/day
```

## Storage Requirements

### Per Batch Record
```
Batch ID:          8 bytes (uint64)
GPU ID:            2 bytes (uint16)
Server ID:         2 bytes (uint16)
Start Key:         32 bytes (256-bit key)
End Key:           32 bytes (256-bit key)
Keys Checked:      8 bytes (uint64)
Candidates Found:  4 bytes (uint32)
Timestamp:         8 bytes (unix timestamp)
Checksum:          32 bytes (SHA256 of batch data)
─────────────────────────────────────
Total per batch:   128 bytes
```

### Storage Estimates
```
Per hour:   130 batches × 128 bytes = 16.64 KB/hour
Per day:    3,110 batches × 128 bytes = 398 KB/day
Per month:  93,300 batches × 128 bytes = 11.9 MB/month
Per year:   1,135,650 batches × 128 bytes = 145 MB/year
```

## Database Options

### Option 1: ScyllaDB/Cassandra (RECOMMENDED)
**Pros:**
- Extremely fast writes (millions/sec)
- Horizontal scaling
- Time-series optimized
- Built-in compression
- No single point of failure

**Schema:**
```sql
CREATE TABLE keyspace_batches (
    server_id int,
    gpu_id int,
    batch_timestamp bigint,
    batch_id bigint,
    start_key blob,
    end_key blob,
    keys_checked bigint,
    candidates_found int,
    checksum blob,
    PRIMARY KEY ((server_id, gpu_id), batch_timestamp, batch_id)
) WITH CLUSTERING ORDER BY (batch_timestamp DESC);

-- Query by server/gpu
SELECT * FROM keyspace_batches WHERE server_id = 1 AND gpu_id = 0;

-- Query by time range
SELECT * FROM keyspace_batches
WHERE server_id = 1 AND gpu_id = 0
AND batch_timestamp > 1706000000
AND batch_timestamp < 1706100000;
```

### Option 2: Redis with RDB/AOF Persistence
**Pros:**
- Ultra-fast in-memory writes
- Simple setup
- Good for recent data queries
- Can use Redis Streams for real-time monitoring

**Structure:**
```
Key pattern: batch:{server_id}:{gpu_id}:{batch_id}
Value: JSON or MessagePack encoded batch data

# Time series with sorted sets
ZADD batches:server1:gpu0 {timestamp} {batch_id}

# Batch data
HSET batch:1:0:12345
  start_key {hex_key}
  end_key {hex_key}
  keys_checked 1000000000000
  candidates_found 1234
  timestamp 1706000000
```

### Option 3: ClickHouse (Best for Analytics)
**Pros:**
- Columnar storage (extreme compression)
- Lightning fast analytical queries
- Excellent for aggregations
- Can handle petabytes

**Schema:**
```sql
CREATE TABLE keyspace_batches (
    batch_timestamp DateTime,
    server_id UInt8,
    gpu_id UInt8,
    batch_id UInt64,
    start_key FixedString(32),
    end_key FixedString(32),
    keys_checked UInt64,
    candidates_found UInt32,
    checksum FixedString(32)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(batch_timestamp)
ORDER BY (server_id, gpu_id, batch_timestamp);

-- Ultra-fast aggregation queries
SELECT server_id, sum(keys_checked) as total_keys
FROM keyspace_batches
GROUP BY server_id;
```

### Option 4: TimescaleDB (PostgreSQL Extension)
**Pros:**
- Full SQL support
- Time-series optimized
- Automatic partitioning
- Familiar PostgreSQL ecosystem

**Schema:**
```sql
CREATE TABLE keyspace_batches (
    batch_timestamp TIMESTAMPTZ NOT NULL,
    server_id SMALLINT,
    gpu_id SMALLINT,
    batch_id BIGINT,
    start_key BYTEA,
    end_key BYTEA,
    keys_checked BIGINT,
    candidates_found INTEGER,
    checksum BYTEA
);

SELECT create_hypertable('keyspace_batches', 'batch_timestamp');

CREATE INDEX ON keyspace_batches (server_id, gpu_id, batch_timestamp DESC);
```

## Implementation

### 1. Modify K3 Binary (C++ Code Changes)

Add batch reporting functionality:

```cpp
// In bloom_search.cu or main search loop
struct BatchReport {
    uint64_t batch_id;
    uint16_t server_id;
    uint16_t gpu_id;
    uint8_t start_key[32];
    uint8_t end_key[32];
    uint64_t keys_checked;
    uint32_t candidates_found;
    uint64_t timestamp;
    uint8_t checksum[32];
};

void report_batch(BatchReport &batch) {
    // Send via UDP for fire-and-forget
    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(9999);
    inet_pton(AF_INET, "COLLECTOR_SERVER_IP", &server_addr.sin_addr);

    sendto(sockfd, &batch, sizeof(batch), 0,
           (struct sockaddr*)&server_addr, sizeof(server_addr));
    close(sockfd);
}

// In main search loop
uint64_t keys_since_last_report = 0;
uint64_t batch_id = 0;

while (searching) {
    // ... existing search code ...

    keys_since_last_report += keys_processed;

    if (keys_since_last_report >= 1000000000000ULL) { // 1 trillion
        BatchReport batch;
        batch.batch_id = batch_id++;
        batch.server_id = SERVER_ID;
        batch.gpu_id = gpu_id;
        memcpy(batch.start_key, &start_key, 32);
        memcpy(batch.end_key, &current_key, 32);
        batch.keys_checked = keys_since_last_report;
        batch.candidates_found = candidates_found_this_batch;
        batch.timestamp = time(NULL);
        // Calculate checksum
        sha256(&batch, sizeof(batch) - 32, batch.checksum);

        report_batch(batch);

        keys_since_last_report = 0;
        candidates_found_this_batch = 0;
    }
}
```

### 2. Collection Server (Python/Go)

**Python Example (asyncio UDP server):**

```python
import asyncio
import struct
import hashlib
import scylladb  # or psycopg2, redis, clickhouse_driver

class BatchCollector:
    def __init__(self, db):
        self.db = db

    async def handle_batch(self, data, addr):
        # Unpack batch data
        batch = struct.unpack('!QHHH32s32sQI32s', data)
        batch_id, server_id, gpu_id, _, start_key, end_key, \
            keys_checked, candidates, checksum = batch

        # Verify checksum
        calc_checksum = hashlib.sha256(data[:-32]).digest()
        if calc_checksum != checksum:
            print(f"Checksum mismatch from {addr}")
            return

        # Store in database
        await self.db.insert_batch(
            batch_id, server_id, gpu_id,
            start_key, end_key, keys_checked, candidates
        )

        print(f"Batch {batch_id} from server {server_id} GPU {gpu_id}: "
              f"{keys_checked:,} keys checked")

async def main():
    db = ScyllaDBClient()  # Initialize your chosen DB
    collector = BatchCollector(db)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 9999))

    while True:
        data, addr = sock.recvfrom(4096)
        asyncio.create_task(collector.handle_batch(data, addr))

if __name__ == '__main__':
    asyncio.run(main())
```

### 3. Monitoring Dashboard

```python
# Real-time monitoring queries

# Total keys checked per server
SELECT server_id, SUM(keys_checked) as total_keys
FROM keyspace_batches
GROUP BY server_id;

# Keys per hour
SELECT
    date_trunc('hour', batch_timestamp) as hour,
    SUM(keys_checked) as keys_per_hour
FROM keyspace_batches
WHERE batch_timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;

# GPU performance comparison
SELECT
    server_id,
    gpu_id,
    AVG(keys_checked) as avg_keys_per_batch,
    COUNT(*) as batch_count
FROM keyspace_batches
GROUP BY server_id, gpu_id;

# Candidates per trillion keys
SELECT
    server_id,
    SUM(candidates_found) * 1000000000000.0 / SUM(keys_checked)
        as candidates_per_trillion
FROM keyspace_batches
GROUP BY server_id;
```

## Deployment Steps

### Quick Setup (ScyllaDB Recommended)

1. **Install ScyllaDB on collection server:**
```bash
# Ubuntu/Debian
sudo apt-get install apt-transport-https
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5e08fbd8b5d6ec9c
sudo curl -L --output /etc/apt/sources.list.d/scylla.list http://downloads.scylladb.com/deb/ubuntu/scylla-5.2.list
sudo apt-get update
sudo apt-get install scylla
```

2. **Create table:**
```bash
cqlsh -f create_keyspace_table.cql
```

3. **Deploy collection server:**
```bash
python3 batch_collector.py
```

4. **Modify K3 binary:**
- Add batch reporting code
- Recompile for each GPU architecture
- Set COLLECTOR_SERVER_IP environment variable

5. **Deploy modified binaries to GPU servers**

## Alternative: File-Based System (Simpler)

If you want to avoid database complexity initially:

```bash
# Each GPU writes to local file
/root/keyspace_log/server{id}_gpu{id}.log

# Format: CSV or binary
timestamp,batch_id,start_key,end_key,keys_checked,candidates

# Periodic rsync to central server
*/5 * * * * rsync -az /root/keyspace_log/ collector:/data/keyspace_logs/

# Central server imports to database
*/10 * * * * python3 /root/import_logs_to_db.py
```

## Benefits

1. **Audit Trail**: Complete record of every key checked
2. **Resume Capability**: Know exactly what's been searched
3. **Duplicate Prevention**: Query before starting new ranges
4. **Analytics**: Performance analysis, progress tracking
5. **Proof of Work**: Demonstrate thoroughness to stakeholders
6. **Distribution Coordination**: Multiple teams can query what's done

## Estimated Cost

- **ScyllaDB Server**: $50-100/month (dedicated server)
- **Storage**: <150 MB/year (negligible)
- **Bandwidth**: <1 KB/s per GPU (negligible)
- **Performance Impact**: <0.1% (UDP fire-and-forget)

## Next Steps

1. Choose database (recommend ScyllaDB for this use case)
2. Set up collection server
3. Modify K3 binary to add batch reporting
4. Test with single GPU first
5. Deploy to all servers
6. Build monitoring dashboard
