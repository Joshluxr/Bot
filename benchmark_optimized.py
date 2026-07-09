#!/usr/bin/env python3
"""Run a proper benchmark with harder prefix"""

import json
import ssl
import uuid
import websocket
import time
import re

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

BENCHMARK_CODE = '''
import subprocess
import os
import time
import re

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=" * 60)
print("BENCHMARK: OPTIMIZED vs BASELINE")
print("=" * 60)

# Use a prefix that won't be found quickly but allows speed measurement
# 1GUNP is 5 chars - hard enough to not find immediately
prefix = "1GUNPhjyk"  # 9 chars - very hard

print(f"Test prefix: {prefix} ({len(prefix)} chars)")
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("")

proc = subprocess.Popen(
    ["./VanitySearch", "-gpu", "-gpuId", "0,1,2,3", "-t", "0", prefix],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

start = time.time()
samples = []
duration = 90  # 90 seconds

print(f"Running for {duration} seconds...")
print("-" * 60)

try:
    while time.time() - start < duration:
        line = proc.stdout.readline()
        if line:
            print(line, end='', flush=True)
            match = re.search(r"\\[([\\d.]+)\\s*([MG])key/s\\]", line)
            if match:
                val = float(match.group(1))
                if match.group(2) == 'G':
                    val *= 1000
                samples.append(val)
        if proc.poll() is not None:
            break
except:
    pass

proc.terminate()
time.sleep(1)

print("")
print("=" * 60)
print("RESULTS")
print("=" * 60)

if samples:
    # Skip first 5 warmup samples
    stable = samples[5:] if len(samples) > 5 else samples

    if stable:
        avg = sum(stable) / len(stable)
        peak = max(stable)
        low = min(stable)

        print(f"Samples: {len(stable)}")
        print(f"Average: {avg:,.0f} Mkey/s ({avg/1000:.2f} Gkey/s)")
        print(f"Peak:    {peak:,.0f} Mkey/s ({peak/1000:.2f} Gkey/s)")
        print(f"Low:     {low:,.0f} Mkey/s ({low/1000:.2f} Gkey/s)")
        print("")
        print(f"Baseline: 22,600 Mkey/s (22.6 Gkey/s)")

        improvement = ((avg - 22600) / 22600) * 100
        print(f"Change:  {improvement:+.2f}%")

        if improvement > 5:
            print("\\n*** SIGNIFICANT IMPROVEMENT! ***")
        elif improvement > 1:
            print("\\n* Modest improvement *")
        elif improvement > -1:
            print("\\nNo significant change")
        else:
            print("\\nPerformance regression detected")
else:
    print("No samples collected!")

# Now restart with the hard prefix
print("")
print("=" * 60)
print("Restarting search for 1GUNPhjykrBdET...")
print("=" * 60)

proc = subprocess.Popen(
    ["./VanitySearch", "-gpu", "-gpuId", "0,1,2,3", "-o", "found_hard.txt", "-t", "0", "1GUNPhjykrBdET"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Monitor for 30 seconds
for _ in range(30):
    line = proc.stdout.readline()
    if line:
        print(line, end='', flush=True)

print("\\n... VanitySearch continues in background")
'''

def execute():
    ws_url = f"wss://{JUPYTER_URL}/api/kernels/{KERNEL_ID}/channels?token={TOKEN}"
    ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})

    msg_id = str(uuid.uuid4())
    req = {
        "header": {"msg_id": msg_id, "username": "user", "session": str(uuid.uuid4()),
                   "msg_type": "execute_request", "version": "5.3"},
        "parent_header": {}, "metadata": {},
        "content": {"code": BENCHMARK_CODE, "silent": False, "store_history": True,
                   "user_expressions": {}, "allow_stdin": False, "stop_on_error": True},
        "buffers": [], "channel": "shell"
    }

    ws.send(json.dumps(req))
    print("Running benchmark...\n")

    start = time.time()
    while time.time() - start < 180:  # 3 min timeout
        try:
            msg = ws.recv()
            r = json.loads(msg)
            if r.get("msg_type") == "stream":
                print(r["content"]["text"], end="")
            elif r.get("msg_type") == "error":
                print(f"ERROR: {r['content']['ename']}")
                break
            elif r.get("msg_type") == "execute_reply":
                break
        except Exception as e:
            print(f"Error: {e}")
            break

    ws.close()

if __name__ == "__main__":
    execute()
