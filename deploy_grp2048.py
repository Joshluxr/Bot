#!/usr/bin/env python3
"""
Deploy VanitySearch with GRP_SIZE=2048 optimization

This doubles the batch inversion size for ~10-15% speedup
"""

import json
import ssl
import uuid
import websocket
import time

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

DEPLOY_CODE = '''
import subprocess
import os
import time
import signal
import shutil
import re

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=" * 70)
print("DEPLOYING GRP_SIZE=2048 OPTIMIZATION")
print("=" * 70)
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("")

# Stop VanitySearch
print("Step 1: Stopping VanitySearch...")
subprocess.run(["pkill", "-9", "VanitySearch"], capture_output=True)
time.sleep(2)
print("Done")

# Backup
print("\\nStep 2: Creating backups...")
if os.path.exists("VanitySearch") and not os.path.exists("VanitySearch.baseline"):
    shutil.copy("VanitySearch", "VanitySearch.baseline")
    print("Created VanitySearch.baseline")

if os.path.exists("GPU/GPUGroup.h") and not os.path.exists("GPU/GPUGroup.h.orig"):
    shutil.copy("GPU/GPUGroup.h", "GPU/GPUGroup.h.orig")
    print("Created GPU/GPUGroup.h.orig")

# Build GPUGenerate tool
print("\\nStep 3: Building GPUGenerate tool...")
os.chdir("GPU")

# Check what files exist
print("Files in GPU directory:")
for f in os.listdir("."):
    if f.endswith(".cpp") or f.endswith(".h"):
        print(f"  {f}")

# Build GPUGenerate
build_cmd = [
    "g++", "-O2", "-o", "GPUGenerate",
    "GPUGenerate.cpp",
    "../Int.cpp", "../IntMod.cpp", "../Point.cpp",
    "../SECP256K1.cpp", "../Random.cpp",
    "-I..",
    "-lpthread"
]

result = subprocess.run(build_cmd, capture_output=True, text=True)
if result.returncode != 0:
    print(f"Build failed: {result.stderr}")
    print("Trying alternative approach...")

    # Manual GRP_SIZE update without regenerating the full table
    os.chdir("..")

    with open("GPU/GPUGroup.h", "r") as f:
        content = f.read()

    # Check current GRP_SIZE
    match = re.search(r"#define GRP_SIZE (\\d+)", content)
    current_grp = int(match.group(1)) if match else 1024
    print(f"Current GRP_SIZE: {current_grp}")

    # For GRP_SIZE=2048, we need 1024 generator points (GRP_SIZE/2)
    # The existing table has 512 points (for GRP_SIZE=1024)
    # We can still use the optimization by keeping the table size
    # and using the batch inversion more efficiently

    # Actually, the proper approach is to understand that:
    # - The generator table Gx/Gy contains multiples of G
    # - For GRP_SIZE=2048, we need points 1G through 1024G
    # - The current table for GRP_SIZE=1024 has 512 points

    # The doubling requires regenerating the table
    # Since GPUGenerate won't build, let's try a different optimization:
    # Keep GRP_SIZE=1024 but optimize the loop unrolling

    print("\\nApplying loop unrolling optimization instead...")

    with open("GPU/GPUMath.h", "r") as f:
        math_content = f.read()

    if "#pragma unroll 16" not in math_content:
        # Add more aggressive unrolling
        math_content = math_content.replace(
            "for (uint32_t i = 1; i < (GRP_SIZE / 2 + 1); i++) {",
            "#pragma unroll 16\\n  for (uint32_t i = 1; i < (GRP_SIZE / 2 + 1); i++) {"
        )
        math_content = math_content.replace(
            "for (uint32_t i = (GRP_SIZE / 2 + 1) - 1; i > 0; i--) {",
            "#pragma unroll 16\\n  for (uint32_t i = (GRP_SIZE / 2 + 1) - 1; i > 0; i--) {"
        )

        with open("GPU/GPUMath.h", "w") as f:
            f.write(math_content)
        print("Added #pragma unroll 16 to batch inversion loops")

else:
    print("GPUGenerate built successfully!")
    os.chdir("..")

    # Generate new table with GRP_SIZE=2048
    print("\\nStep 4: Generating new GPU tables for GRP_SIZE=2048...")
    result = subprocess.run(
        ["./GPU/GPUGenerate", "2048"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print("Generated new GPUGroup.h with 1024 generator points")
    else:
        print(f"Generation failed: {result.stderr}")

# Clean and rebuild
print("\\nStep 5: Cleaning build artifacts...")
subprocess.run(["make", "clean"], capture_output=True)
subprocess.run(["rm", "-f", "obj/GPU/GPUEngine.o"], capture_output=True)

print("\\nStep 6: Rebuilding VanitySearch...")
result = subprocess.run(
    ["make", "gpu=1", "CCAP=89", "-j4"],
    capture_output=True, text=True
)

if result.returncode == 0:
    print("Build SUCCESSFUL!")
    stat = os.stat("VanitySearch")
    print(f"Binary size: {stat.st_size} bytes")
else:
    print("Build FAILED!")
    print(result.stderr[-1500:])

# Benchmark
print("\\nStep 7: Running benchmark (40 seconds)...")
print("-" * 60)

proc = subprocess.Popen(
    ["./VanitySearch", "-gpu", "-gpuId", "0,1,2,3", "-stop", "-t", "0", "1AAAA"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

start = time.time()
samples = []

while time.time() - start < 40:
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

proc.terminate()

print("")
print("=" * 60)
print("RESULTS")
print("=" * 60)

if samples and len(samples) > 5:
    avg = sum(samples[5:]) / len(samples[5:])
    print(f"Average performance: {avg:.0f} Mkey/s ({avg/1000:.2f} Gkey/s)")
    print(f"Baseline: 22,600 Mkey/s")
    improvement = ((avg - 22600) / 22600) * 100
    print(f"Change: {improvement:+.1f}%")
else:
    print("Not enough samples collected")

print(f"\\nCompleted at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
'''

def execute():
    ws_url = f"wss://{JUPYTER_URL}/api/kernels/{KERNEL_ID}/channels?token={TOKEN}"
    ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})

    msg_id = str(uuid.uuid4())
    execute_request = {
        "header": {"msg_id": msg_id, "username": "user", "session": str(uuid.uuid4()),
                   "msg_type": "execute_request", "version": "5.3"},
        "parent_header": {}, "metadata": {},
        "content": {"code": DEPLOY_CODE, "silent": False, "store_history": True,
                   "user_expressions": {}, "allow_stdin": False, "stop_on_error": True},
        "buffers": [], "channel": "shell"
    }

    ws.send(json.dumps(execute_request))
    print("Deploying optimization...\n")

    start = time.time()
    while time.time() - start < 300:
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
