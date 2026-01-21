#!/usr/bin/env python3
"""
Real-time candidate verification against hash160 database.
Monitors K3 log files and verifies candidates against the sorted h160db.
"""
import os
import sys
import struct
import time
import re
from datetime import datetime

H160DB_PATH = "/root/bloom_opt.h160db"
LOG_DIR = "/tmp"
FOUND_FILE = "/root/FOUND_KEYS.txt"

def load_h160db(path):
    """Load sorted hash160 database into memory for binary search"""
    size = os.path.getsize(path)
    count = size // 20
    print(f"Loading {count:,} hash160s from {path}...")

    with open(path, "rb") as f:
        data = f.read()

    # Create set of 20-byte hash160s
    h160_set = set()
    for i in range(count):
        h160_set.add(data[i*20:(i+1)*20])

    print(f"Loaded {len(h160_set):,} unique hash160s into memory")
    return h160_set

def parse_candidate_line(line):
    """Parse K3 candidate log line and extract hash160"""
    # Format: [K3 CANDIDATE COMP] tid=37082 meta=02008000 hash160=5723370b0197bfd6fc74b8a626314061d3bda538
    match = re.search(r'hash160=([0-9a-f]{40})', line)
    if match:
        return bytes.fromhex(match.group(1))
    return None

def monitor_logs(h160_set):
    """Monitor K3 log files for candidates and verify them"""
    print(f"\nMonitoring {LOG_DIR}/k3_gpu*.log for candidates...")
    print(f"Verified matches will be saved to {FOUND_FILE}\n")

    # Track file positions
    file_positions = {}
    total_candidates = 0
    verified_matches = 0

    # Open found file for appending
    found_f = open(FOUND_FILE, "a")
    found_f.write(f"\n=== Verification started at {datetime.now()} ===\n")
    found_f.flush()

    try:
        while True:
            for gpu_id in range(8):
                log_path = f"{LOG_DIR}/k3_gpu{gpu_id}.log"

                if not os.path.exists(log_path):
                    continue

                # Get current file size
                current_size = os.path.getsize(log_path)
                last_pos = file_positions.get(log_path, 0)

                if current_size > last_pos:
                    with open(log_path, "r") as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        file_positions[log_path] = f.tell()

                    for line in new_lines:
                        if "CANDIDATE" in line:
                            h160 = parse_candidate_line(line)
                            if h160:
                                total_candidates += 1

                                # VERIFY against database
                                if h160 in h160_set:
                                    verified_matches += 1
                                    msg = f"[VERIFIED MATCH #{verified_matches}] GPU{gpu_id}: {h160.hex()}"
                                    print(f"\n{'='*60}")
                                    print(msg)
                                    print(f"{'='*60}\n")
                                    found_f.write(f"{datetime.now()} {msg}\n")
                                    found_f.write(f"  Full line: {line.strip()}\n")
                                    found_f.flush()

            # Status update every second
            print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Checked {total_candidates:,} candidates, {verified_matches} verified matches", end="", flush=True)
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n\nStopped. Total: {total_candidates:,} candidates, {verified_matches} verified matches")
    finally:
        found_f.close()

if __name__ == "__main__":
    h160_set = load_h160db(H160DB_PATH)
    monitor_logs(h160_set)
