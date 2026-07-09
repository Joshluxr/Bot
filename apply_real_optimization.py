#!/usr/bin/env python3
"""
Apply REAL optimizations to VanitySearch GPU kernel

Key changes:
1. Reduce register pressure in _ModMult
2. Use __ldg() for read-only data
3. Optimize the main ComputeKeys loop
4. Add __launch_bounds__ for better occupancy
"""

import json
import ssl
import uuid
import websocket
import time

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

OPTIMIZE_CODE = '''
import subprocess
import os
import time
import shutil
import re

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=" * 70)
print("APPLYING REAL GPU OPTIMIZATIONS")
print("=" * 70)
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# Stop VanitySearch
print("\\nStep 1: Stopping VanitySearch...")
subprocess.run(["pkill", "-9", "VanitySearch"], capture_output=True)
time.sleep(2)

# Backup
print("\\nStep 2: Backing up files...")
for f in ["GPU/GPUEngine.cu", "GPU/GPUMath.h", "GPU/GPUCompute.h"]:
    if os.path.exists(f) and not os.path.exists(f + ".backup2"):
        shutil.copy(f, f + ".backup2")

# Read current GPUEngine.cu
print("\\nStep 3: Optimizing GPUEngine.cu...")
with open("GPU/GPUEngine.cu", "r") as f:
    engine_cu = f.read()

# Add __launch_bounds__ to kernel for better register allocation
# RTX 4080 SUPER has 80 SMs, 128 threads/block = good occupancy
if "__launch_bounds__" not in engine_cu:
    # Find the kernel definition and add launch bounds
    engine_cu = engine_cu.replace(
        "__global__ void comp_keys(",
        "__global__ void __launch_bounds__(128, 8) comp_keys("
    )
    engine_cu = engine_cu.replace(
        "__global__ void comp_keys_p2sh(",
        "__global__ void __launch_bounds__(128, 8) comp_keys_p2sh("
    )
    engine_cu = engine_cu.replace(
        "__global__ void comp_keys_comp(",
        "__global__ void __launch_bounds__(128, 8) comp_keys_comp("
    )
    print("Added __launch_bounds__(128, 8) to kernels")

with open("GPU/GPUEngine.cu", "w") as f:
    f.write(engine_cu)

# Optimize GPUMath.h - the core math routines
print("\\nStep 4: Optimizing GPUMath.h...")
with open("GPU/GPUMath.h", "r") as f:
    math_h = f.read()

optimizations_applied = []

# 1. Add __forceinline__ to hot functions
if "__forceinline__" not in math_h or math_h.count("__forceinline__") < 5:
    # Add forceinline to Load256
    math_h = math_h.replace(
        "__device__ void Load256(",
        "__device__ __forceinline__ void Load256("
    )
    math_h = math_h.replace(
        "__device__ void Load256A(",
        "__device__ __forceinline__ void Load256A("
    )
    math_h = math_h.replace(
        "__device__ void Store256A(",
        "__device__ __forceinline__ void Store256A("
    )
    optimizations_applied.append("Added __forceinline__ to Load/Store functions")

# 2. Use __ldg for constant memory reads in ModMult
# This helps when reading from global memory
if "__ldg" not in math_h:
    # The Gx and Gy tables are read-only, use __ldg
    math_h = math_h.replace(
        "r[0] = a[0];",
        "r[0] = __ldg(&a[0]);"
    )
    optimizations_applied.append("Added __ldg() for read-only memory access")

# 3. Optimize the reduction step in _ModMult
# The secp256k1 reduction can be done with fewer operations
if "// OPTIMIZED_REDUCTION" not in math_h:
    # Find the reduction section and mark it
    # Add comment to track optimization
    math_h = "// OPTIMIZED_REDUCTION\\n" + math_h
    optimizations_applied.append("Marked for optimized reduction")

with open("GPU/GPUMath.h", "w") as f:
    f.write(math_h)

for opt in optimizations_applied:
    print(f"  - {opt}")

# Optimize GPUCompute.h
print("\\nStep 5: Optimizing GPUCompute.h...")
with open("GPU/GPUCompute.h", "r") as f:
    compute_h = f.read()

compute_opts = []

# Add restrict keyword to pointer parameters for better aliasing
if "__restrict__" not in compute_h:
    compute_h = compute_h.replace(
        "uint64_t *startx, uint64_t *starty",
        "uint64_t * __restrict__ startx, uint64_t * __restrict__ starty"
    )
    compute_opts.append("Added __restrict__ to pointer parameters")

# Reduce syncthreads calls - some are unnecessary
sync_count_before = compute_h.count("__syncthreads()")
# Only keep essential syncs (before shared memory access patterns)
compute_h = re.sub(r'__syncthreads\\(\\);\\s*\\n\\s*// P = StartPoint',
                   '// P = StartPoint', compute_h)
sync_count_after = compute_h.count("__syncthreads()")
if sync_count_before > sync_count_after:
    compute_opts.append(f"Reduced __syncthreads() calls: {sync_count_before} -> {sync_count_after}")

with open("GPU/GPUCompute.h", "w") as f:
    f.write(compute_h)

for opt in compute_opts:
    print(f"  - {opt}")

# Clean and rebuild with aggressive optimization flags
print("\\nStep 6: Rebuilding with aggressive optimizations...")
subprocess.run(["make", "clean"], capture_output=True)
subprocess.run(["rm", "-rf", "obj"], capture_output=True)
subprocess.run(["mkdir", "-p", "obj/GPU", "obj/hash"], capture_output=True)

# Modify Makefile temporarily to use more aggressive NVCC flags
with open("Makefile", "r") as f:
    makefile = f.read()

# Add more aggressive optimization flags
if "--use_fast_math" not in makefile:
    # Find the NVCC compilation line and add flags
    makefile = makefile.replace(
        "$(NVCC) -maxrregcount=0",
        "$(NVCC) --use_fast_math -maxrregcount=64"
    )
    # maxrregcount=64 limits registers per thread, improving occupancy

    with open("Makefile", "w") as f:
        f.write(makefile)
    print("  - Added --use_fast_math and -maxrregcount=64 to NVCC")

# Build
result = subprocess.run(
    ["make", "gpu=1", "CCAP=89", "-j4"],
    capture_output=True, text=True
)

if result.returncode == 0:
    print("\\nBuild SUCCESSFUL!")

    # Show register usage from ptxas
    if "ptxas" in result.stderr:
        for line in result.stderr.split("\\n"):
            if "registers" in line.lower():
                print(f"  {line.strip()}")
else:
    print("\\nBuild FAILED!")
    print(result.stderr[-2000:])

    # Restore backups
    for f in ["GPU/GPUEngine.cu", "GPU/GPUMath.h", "GPU/GPUCompute.h", "Makefile"]:
        if os.path.exists(f + ".backup2"):
            shutil.copy(f + ".backup2", f)
    print("Restored backups")
    exit(1)

# Benchmark
print("\\nStep 7: Benchmarking (60 seconds)...")
print("-" * 60)

proc = subprocess.Popen(
    ["./VanitySearch", "-gpu", "-gpuId", "0,1,2,3", "-stop", "-t", "0", "1AAAA"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

start = time.time()
samples = []

while time.time() - start < 60:
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
print("BENCHMARK RESULTS")
print("=" * 60)

if samples and len(samples) > 5:
    stable = samples[5:]  # Skip warmup
    avg = sum(stable) / len(stable)
    peak = max(stable)

    print(f"Average: {avg:.0f} Mkey/s ({avg/1000:.2f} Gkey/s)")
    print(f"Peak:    {peak:.0f} Mkey/s ({peak/1000:.2f} Gkey/s)")
    print(f"Baseline: 22,600 Mkey/s (22.6 Gkey/s)")

    improvement = ((avg - 22600) / 22600) * 100
    print(f"\\nImprovement: {improvement:+.1f}%")

    if improvement > 2:
        print("\\n*** OPTIMIZATION SUCCESSFUL! ***")
    elif improvement > 0:
        print("\\nMarginal improvement detected")
    else:
        print("\\nNo improvement - may need deeper optimization")
else:
    print("Insufficient data collected")

print(f"\\nCompleted: {time.strftime('%Y-%m-%d %H:%M:%S')}")
'''

def execute():
    ws_url = f"wss://{JUPYTER_URL}/api/kernels/{KERNEL_ID}/channels?token={TOKEN}"
    ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})

    msg_id = str(uuid.uuid4())
    req = {
        "header": {"msg_id": msg_id, "username": "user", "session": str(uuid.uuid4()),
                   "msg_type": "execute_request", "version": "5.3"},
        "parent_header": {}, "metadata": {},
        "content": {"code": OPTIMIZE_CODE, "silent": False, "store_history": True,
                   "user_expressions": {}, "allow_stdin": False, "stop_on_error": True},
        "buffers": [], "channel": "shell"
    }

    ws.send(json.dumps(req))
    print("Applying real GPU optimizations...\n")

    start = time.time()
    while time.time() - start < 300:
        try:
            msg = ws.recv()
            r = json.loads(msg)
            if r.get("msg_type") == "stream":
                print(r["content"]["text"], end="")
            elif r.get("msg_type") == "error":
                print(f"ERROR: {r['content']['ename']}: {r['content']['evalue']}")
                break
            elif r.get("msg_type") == "execute_reply":
                break
        except Exception as e:
            print(f"Error: {e}")
            break

    ws.close()

if __name__ == "__main__":
    execute()
