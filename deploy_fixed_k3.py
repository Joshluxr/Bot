#!/usr/bin/env python3
"""
Deploy Fixed K3 to GPU Server
==============================

This script:
1. Builds a K3-compatible bloom filter on the GPU server
2. Restarts K3 with the fixed bloom filter
3. Verifies the target hash160 is detected

ROOT CAUSE: The original bloom filter was built with MODULO (h % bits)
but K3 uses AND mask (h & (bits-1)) for speed. This caused mismatches.

SOLUTION: Rebuild bloom filter using AND mask method.
"""

import json
import ssl
import uuid
import websocket
import time
import sys

# GPU Server connection info
JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

# Target for verification
TARGET_HASH160 = "abeddf6b115157b704de34c50d22beefbeb59c98"
TARGET_START = "74120947517767895891355266452452269842804955139343486161984562552406380000000"

def execute_code(code, timeout=600):
    """Execute code on Jupyter kernel and return output"""
    ws_url = f"wss://{JUPYTER_URL}/api/kernels/{KERNEL_ID}/channels?token={TOKEN}"

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE}, timeout=30)
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

    msg_id = str(uuid.uuid4())

    execute_request = {
        "header": {
            "msg_id": msg_id,
            "username": "user",
            "session": str(uuid.uuid4()),
            "msg_type": "execute_request",
            "version": "5.3"
        },
        "parent_header": {},
        "metadata": {},
        "content": {
            "code": code,
            "silent": False,
            "store_history": True,
            "user_expressions": {},
            "allow_stdin": False,
            "stop_on_error": True
        },
        "buffers": [],
        "channel": "shell"
    }

    ws.send(json.dumps(execute_request))

    output_lines = []
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            print("Timeout reached")
            break

        try:
            ws.settimeout(10)
            msg = ws.recv()
            response = json.loads(msg)

            msg_type = response.get("msg_type", "")
            content = response.get("content", {})

            if msg_type == "stream":
                text = content.get("text", "")
                print(text, end="")
                output_lines.append(text)
            elif msg_type == "execute_result":
                data = content.get("data", {})
                text = data.get("text/plain", "")
                print(text)
                output_lines.append(text)
            elif msg_type == "error":
                print(f"ERROR: {content.get('ename')}: {content.get('evalue')}")
                break
            elif msg_type == "execute_reply":
                status = content.get("status", "")
                if status == "ok":
                    print("\n=== Command completed ===\n")
                break
        except websocket.WebSocketTimeoutException:
            continue
        except Exception as e:
            print(f"Error: {e}")
            break

    ws.close()
    return "".join(output_lines)

def main():
    print("="*70)
    print("DEPLOY FIXED K3 WITH K3-COMPATIBLE BLOOM FILTER")
    print("="*70)
    print(f"\nRoot cause: Bloom filter was built with MODULO, K3 uses AND mask")
    print(f"Solution: Rebuild bloom filter using AND mask method")
    print(f"\nTarget hash160: {TARGET_HASH160}")

    # Step 1: Stop any running K3 processes
    print("\n[1/5] Stopping existing K3 processes...")
    execute_code('''
import subprocess
subprocess.run(["pkill", "-f", "BloomSearch32K3"], capture_output=True)
print("Stopped K3 processes")
''', timeout=30)

    # Step 2: Build K3-compatible bloom filter
    print("\n[2/5] Building K3-compatible bloom filter...")
    # Embed the build_k3_bloom.py code and run it
    build_code = '''
import struct
import os

def murmur3_32(key, seed):
    c1 = 0xcc9e2d51
    c2 = 0x1b873593
    h1 = seed & 0xFFFFFFFF

    nblocks = len(key) // 4
    for i in range(nblocks):
        k1 = struct.unpack('<I', key[i*4:(i+1)*4])[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF
        h1 = ((h1 * 5) + 0xe6546b64) & 0xFFFFFFFF

    tail = key[nblocks * 4:]
    k1 = 0
    if len(tail) >= 3:
        k1 ^= tail[2] << 16
    if len(tail) >= 2:
        k1 ^= tail[1] << 8
    if len(tail) >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1

    h1 ^= len(key)
    h1 ^= (h1 >> 16)
    h1 = (h1 * 0x85ebca6b) & 0xFFFFFFFF
    h1 ^= (h1 >> 13)
    h1 = (h1 * 0xc2b2ae35) & 0xFFFFFFFF
    h1 ^= (h1 >> 16)
    return h1

# Check for h160db file
h160db_paths = ["/data/bloom_opt.h160db", "/workspace/bloom_opt.h160db", "/root/bloom_opt.h160db"]
h160db_path = None
for p in h160db_paths:
    if os.path.exists(p):
        h160db_path = p
        break

if not h160db_path:
    print("ERROR: h160db file not found!")
    print("Checked paths:", h160db_paths)
else:
    file_size = os.path.getsize(h160db_path)
    num_entries = file_size // 20
    print(f"Found h160db: {h160db_path}")
    print(f"  Entries: {num_entries:,}")

    # Use power of 2 size: 2^30 bits = 128 MB
    BLOOM_BITS = 1 << 30  # 1073741824
    BLOOM_MASK = BLOOM_BITS - 1
    BLOOM_BYTES = BLOOM_BITS // 8
    NUM_HASHES = 12

    # Fixed seeds for reproducibility
    seeds = [0xa3b1799d, 0x46685257, 0x392456de, 0xbc8960a9,
             0x6c031199, 0x07a0ca6e, 0x37f8a88b, 0x8b8148f6,
             0x12345678, 0x87654321, 0xdeadbeef, 0xcafebabe][:NUM_HASHES]

    print(f"\\nBuilding K3-compatible bloom filter...")
    print(f"  Bits: {BLOOM_BITS:,} (2^30)")
    print(f"  Bytes: {BLOOM_BYTES:,} ({BLOOM_BYTES/(1024*1024):.0f} MB)")
    print(f"  Mask: 0x{BLOOM_MASK:x}")
    print(f"  Hashes: {NUM_HASHES}")

    # Allocate bloom filter
    bloom = bytearray(BLOOM_BYTES)

    # Process h160db
    with open(h160db_path, 'rb') as f:
        for i in range(num_entries):
            h160 = f.read(20)
            if len(h160) != 20:
                break

            # K3 method: AND mask
            for seed in seeds:
                h = murmur3_32(h160, seed)
                bit_pos = h & BLOOM_MASK
                byte_pos = bit_pos >> 3
                bit_in_byte = bit_pos & 7
                bloom[byte_pos] |= (1 << bit_in_byte)

            if (i + 1) % 1000000 == 0:
                print(f"  Processed {i+1:,} / {num_entries:,} ({100*(i+1)/num_entries:.1f}%)")

    print(f"  Done! Processed {num_entries:,} entries")

    # Save bloom filter
    out_bloom = "/data/k3_bloom.bloom"
    out_seeds = "/data/k3_bloom.seeds"

    with open(out_bloom, 'wb') as f:
        f.write(bloom)
    print(f"Saved: {out_bloom} ({os.path.getsize(out_bloom):,} bytes)")

    with open(out_seeds, 'wb') as f:
        for seed in seeds:
            f.write(struct.pack('<I', seed))
    print(f"Saved: {out_seeds} ({os.path.getsize(out_seeds):,} bytes)")
'''
    result = execute_code(build_code, timeout=1800)  # 30 min timeout for large db

    # Step 3: Verify target hash160 passes the new bloom filter
    print("\n[3/5] Verifying target hash160 in new bloom filter...")
    verify_code = f'''
import struct
import os

def murmur3_32(key, seed):
    c1 = 0xcc9e2d51
    c2 = 0x1b873593
    h1 = seed & 0xFFFFFFFF
    nblocks = len(key) // 4
    for i in range(nblocks):
        k1 = struct.unpack('<I', key[i*4:(i+1)*4])[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF
        h1 = ((h1 * 5) + 0xe6546b64) & 0xFFFFFFFF
    tail = key[nblocks * 4:]
    k1 = 0
    if len(tail) >= 3: k1 ^= tail[2] << 16
    if len(tail) >= 2: k1 ^= tail[1] << 8
    if len(tail) >= 1:
        k1 ^= tail[0]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
    h1 ^= len(key)
    h1 ^= (h1 >> 16)
    h1 = (h1 * 0x85ebca6b) & 0xFFFFFFFF
    h1 ^= (h1 >> 13)
    h1 = (h1 * 0xc2b2ae35) & 0xFFFFFFFF
    h1 ^= (h1 >> 16)
    return h1

target = bytes.fromhex("{TARGET_HASH160}")
bloom_path = "/data/k3_bloom.bloom"
seeds_path = "/data/k3_bloom.seeds"

if not os.path.exists(bloom_path):
    print("ERROR: New bloom filter not found!")
else:
    with open(bloom_path, 'rb') as f:
        bloom = f.read()
    with open(seeds_path, 'rb') as f:
        seeds_data = f.read()

    num_seeds = len(seeds_data) // 4
    seeds = [struct.unpack('<I', seeds_data[i*4:(i+1)*4])[0] for i in range(num_seeds)]
    bloom_mask = len(bloom) * 8 - 1

    print(f"Testing target: {TARGET_HASH160}")
    all_pass = True
    for seed in seeds:
        h = murmur3_32(target, seed)
        bit_pos = h & bloom_mask
        byte_pos = bit_pos >> 3
        bit_in_byte = bit_pos & 7
        is_set = bool(bloom[byte_pos] & (1 << bit_in_byte))
        status = "PASS" if is_set else "FAIL"
        print(f"  Seed {{seed:08x}}: bitPos={{bit_pos:,}} -> {{status}}")
        if not is_set:
            all_pass = False

    print(f"\\nOVERALL: {{'PASS - Target will be detected!' if all_pass else 'FAIL - Something wrong!'}}")
'''
    execute_code(verify_code, timeout=60)

    # Step 4: Launch K3 with new bloom filter
    print("\n[4/5] Launching K3 with K3-compatible bloom filter...")
    launch_code = f'''
import subprocess
import os
import time

os.chdir("/workspace/k3")

# Launch on GPU 0 only for testing
cmd = f"""nohup /workspace/k3/BloomSearch32K3 \\
    -gpu 0 \\
    -prefix /data/prefix32.bin \\
    -bloom /data/k3_bloom.bloom \\
    -seeds /data/k3_bloom.seeds \\
    -bits 1073741824 \\
    -hashes 12 \\
    -start "{TARGET_START}" \\
    -state /tmp/gpu0_k3_test.state \\
    -both \\
    > /tmp/k3_gpu0_test.log 2>&1 &"""

print("Launching K3 with fixed bloom filter...")
print(f"Start: {TARGET_START[:50]}...")
result = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)

time.sleep(5)

# Check if running
result = subprocess.run(["pgrep", "-af", "BloomSearch32K3"], capture_output=True, text=True)
print("\\nRunning processes:")
print(result.stdout)

# Show initial log
time.sleep(5)
result = subprocess.run(["tail", "-30", "/tmp/k3_gpu0_test.log"], capture_output=True, text=True)
print("\\nInitial log output:")
print(result.stdout)
'''
    execute_code(launch_code, timeout=120)

    # Step 5: Monitor for target detection
    print("\n[5/5] Monitoring for target detection (iteration 205)...")
    monitor_code = '''
import subprocess
import time

print("Monitoring for candidates...")
print("Target should be found at thread=256, iteration=205")
print("")

for i in range(30):  # Monitor for 30 iterations
    time.sleep(10)

    # Check log for candidates
    result = subprocess.run(["grep", "CANDIDATE", "/tmp/k3_gpu0_test.log"], capture_output=True, text=True)
    if result.stdout:
        print(f"\\n=== CANDIDATES FOUND ===")
        print(result.stdout[-2000:])  # Last 2000 chars

    # Check progress
    result = subprocess.run(["tail", "-1", "/tmp/k3_gpu0_test.log"], capture_output=True, text=True)
    print(f"\\r[{i+1}/30] {result.stdout.strip()[:80]}", end="", flush=True)

    # Check if target hash found
    result = subprocess.run(["grep", "abeddf6b", "/tmp/k3_gpu0_test.log"], capture_output=True, text=True)
    if result.stdout:
        print(f"\\n\\n{'='*60}")
        print("TARGET HASH160 FOUND!")
        print("='*60")
        print(result.stdout)
        break

print("\\n\\nMonitoring complete.")
'''
    execute_code(monitor_code, timeout=600)

    print("\n" + "="*70)
    print("DEPLOYMENT COMPLETE")
    print("="*70)
    print("\nTo monitor manually:")
    print("  tail -f /tmp/k3_gpu0_test.log | grep -i candidate")
    print("\nTo search for target:")
    print(f"  grep {TARGET_HASH160[:8]} /tmp/k3_gpu0_test.log")

if __name__ == "__main__":
    main()
