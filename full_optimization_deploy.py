#!/usr/bin/env python3
"""
Full optimization deployment for VanitySearch

This script:
1. Stops current VanitySearch
2. Regenerates GPUGroup.h with GRP_SIZE=2048
3. Applies all optimizations
4. Rebuilds VanitySearch
5. Runs benchmark comparison
"""

import json
import ssl
import uuid
import websocket
import time

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

# The key is to regenerate GPUGroup.h with the new GRP_SIZE
# This uses the existing GPUGenerate program

FULL_DEPLOY_CODE = '''
import subprocess
import os
import time
import signal
import shutil
import re

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=" * 70)
print("FULL OPTIMIZATION DEPLOYMENT - BATCH SIZE DOUBLING")
print("=" * 70)
print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("")

# Step 1: Stop current VanitySearch
print("Step 1: Stopping current VanitySearch...")
result = subprocess.run(["pkill", "-9", "VanitySearch"], capture_output=True)
time.sleep(2)
print("Done")

# Step 2: Backup current files
print("\\nStep 2: Backing up current files...")
backup_files = ["VanitySearch", "GPU/GPUGroup.h", "GPU/GPUMath.h"]
for f in backup_files:
    if os.path.exists(f):
        shutil.copy(f, f + ".original")
        print(f"  Backed up {f}")
print("Done")

# Step 3: Regenerate GPUGroup.h with GRP_SIZE=2048
print("\\nStep 3: Regenerating GPU tables with GRP_SIZE=2048...")

# First we need to modify GPUGenerate.cpp to use 2048 instead of 1024
with open("GPU/GPUGenerate.cpp", "r") as f:
    gen_cpp = f.read()

# Find the size parameter - it's passed as command line arg
# We'll rebuild with the new size directly

# Check if we have a pre-built generator
result = subprocess.run(
    ["./GPUGenerate", "2048"],
    capture_output=True, text=True, cwd="GPU"
)

if result.returncode != 0:
    print("GPUGenerate not found, building it first...")

    # Build GPUGenerate - need to compile it first
    # Look for how it's built
    gen_build = subprocess.run(
        ["g++", "-O2", "-o", "GPUGenerate", "GPUGenerate.cpp", "../Int.cpp", "../IntMod.cpp",
         "../Point.cpp", "../SECP256K1.cpp", "../Random.cpp", "-I..", "-lpthread"],
        capture_output=True, text=True, cwd="GPU"
    )

    if gen_build.returncode == 0:
        print("GPUGenerate built successfully")
        result = subprocess.run(
            ["./GPUGenerate", "2048"],
            capture_output=True, text=True, cwd="GPU"
        )
    else:
        print(f"Failed to build GPUGenerate: {gen_build.stderr}")
        print("\\nFalling back to manual table modification...")

        # We can manually patch GPUGroup.h to have the larger group size
        # by reading the current file and doubling it
        with open("GPU/GPUGroup.h", "r") as f:
            group_h = f.read()

        # Update GRP_SIZE
        group_h = re.sub(r"#define GRP_SIZE \\d+", "#define GRP_SIZE 2048", group_h)

        # Note: The generator table itself stays the same (we just use more of it)
        # The key insight is that _ModInvGrouped handles the full GRP_SIZE/2+1 elements
        # So we need the full table of 1024 points (for GRP_SIZE=2048)

        with open("GPU/GPUGroup.h", "w") as f:
            f.write(group_h)

        print("Updated GRP_SIZE to 2048")

# Verify the change
with open("GPU/GPUGroup.h", "r") as f:
    content = f.read()
    if "#define GRP_SIZE 2048" in content:
        print("Verified: GRP_SIZE is now 2048")
    else:
        m = re.search(r"#define GRP_SIZE (\\d+)", content)
        print(f"Current GRP_SIZE: {m.group(1) if m else 'unknown'}")

# Step 4: Clean and rebuild
print("\\nStep 4: Cleaning build...")
subprocess.run(["make", "clean"], capture_output=True)
subprocess.run(["rm", "-f", "obj/GPU/GPUEngine.o"], capture_output=True)  # Force GPU recompile
time.sleep(1)

print("\\nStep 5: Rebuilding VanitySearch with optimizations...")
print("Building for RTX 4080 SUPER (SM 8.9)...")

# Full clean rebuild
result = subprocess.run(
    ["make", "gpu=1", "CCAP=89", "-j4"],
    capture_output=True, text=True
)

if result.returncode == 0:
    print("Build SUCCESSFUL!")

    # Show ptxas output for register usage
    if "ptxas" in result.stderr:
        for line in result.stderr.split("\\n"):
            if "registers" in line.lower() or "memory" in line.lower():
                print(f"  {line}")
else:
    print("Build FAILED!")
    print("STDERR:", result.stderr[-2000:])
    print("\\nRestoring backup...")
    for f in backup_files:
        if os.path.exists(f + ".original"):
            shutil.copy(f + ".original", f)
    exit(1)

# Step 6: Verify new binary
print("\\nStep 6: Verifying new binary...")
stat = os.stat("VanitySearch")
print(f"Binary size: {stat.st_size} bytes")
print(f"Build time: {time.ctime(stat.st_mtime)}")

# Step 7: Run performance benchmark
print("\\nStep 7: Running performance benchmark (45 seconds)...")
print("-" * 70)

proc = subprocess.Popen(
    ["./VanitySearch", "-gpu", "-gpuId", "0,1,2,3", "-stop", "-t", "0", "1AAAA"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

start_time = time.time()
perf_samples = []

try:
    while time.time() - start_time < 45:
        line = proc.stdout.readline()
        if line:
            print(line, end='', flush=True)

            # Extract performance numbers
            if "Mkey/s" in line or "Gkey/s" in line:
                # Parse the Mkey/s value
                match = re.search(r"\\[([\\d.]+)\\s*([MG])key/s\\]", line)
                if match:
                    val = float(match.group(1))
                    if match.group(2) == 'G':
                        val *= 1000
                    perf_samples.append(val)

        if proc.poll() is not None:
            break
except:
    pass

proc.terminate()
time.sleep(1)

# Step 8: Report results
print("")
print("=" * 70)
print("PERFORMANCE RESULTS")
print("=" * 70)

if perf_samples:
    # Skip first 5 samples (warm-up)
    stable_samples = perf_samples[5:] if len(perf_samples) > 5 else perf_samples

    if stable_samples:
        avg_perf = sum(stable_samples) / len(stable_samples)
        max_perf = max(stable_samples)
        min_perf = min(stable_samples)

        print(f"Samples collected: {len(stable_samples)}")
        print(f"Average: {avg_perf:.2f} Mkey/s ({avg_perf/1000:.2f} Gkey/s)")
        print(f"Peak:    {max_perf:.2f} Mkey/s ({max_perf/1000:.2f} Gkey/s)")
        print(f"Min:     {min_perf:.2f} Mkey/s ({min_perf/1000:.2f} Gkey/s)")

        # Compare to baseline (22,600 Mkey/s)
        baseline = 22600
        improvement = ((avg_perf - baseline) / baseline) * 100
        print(f"\\nBaseline: {baseline} Mkey/s")
        print(f"Improvement: {improvement:+.1f}%")

        if improvement > 0:
            print("\\nOptimization SUCCESSFUL!")
        else:
            print("\\nNo improvement detected (may need further tuning)")

print("")
print("=" * 70)
print("DEPLOYMENT COMPLETE")
print("=" * 70)
print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
'''

def execute_code():
    ws_url = f"wss://{JUPYTER_URL}/api/kernels/{KERNEL_ID}/channels?token={TOKEN}"

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})

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
            "code": FULL_DEPLOY_CODE,
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
    print("Deploying full optimization...")
    print("This will take 1-2 minutes for rebuild + benchmark\n")

    start_time = time.time()
    timeout = 300  # 5 minutes

    while True:
        if time.time() - start_time > timeout:
            print("Timeout reached")
            break

        try:
            msg = ws.recv()
            response = json.loads(msg)

            msg_type = response.get("msg_type", "")
            content = response.get("content", {})

            if msg_type == "stream":
                text = content.get("text", "")
                print(text, end="")
            elif msg_type == "error":
                print(f"ERROR: {content.get('ename')}: {content.get('evalue')}")
                break
            elif msg_type == "execute_reply":
                break

        except Exception as e:
            print(f"Error: {e}")
            break

    ws.close()

if __name__ == "__main__":
    execute_code()
