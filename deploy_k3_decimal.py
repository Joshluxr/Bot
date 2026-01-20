#!/usr/bin/env python3
"""Deploy and launch K3 on GPU server with decimal starting ranges"""

import json
import ssl
import uuid
import websocket
import time
import base64
import subprocess
import sys

# GPU Server connection info
JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

# Decimal starting ranges for each GPU
DECIMAL_STARTS = [
    "82992563620862434352475351947757081565902246292157501334072464625845000000000",
    "83006381551614476668704001704925337411013586345448656596844062026379000000000",
    "56250958961391727996141955054393623146377586413781665198566261449216000000000",
    "55759889748939984167476976690990381959594369969782570707259939409534000000000",
    "81344397156153394613998188530327581501124344310299587598256439929703000000000",
    "81979563453356770746037359084754162925559246477171714229961496311613000000000",
    "7905764002027863378760312975829580808151779176516965379126368541744000000000",
    "114942193531081435629910684111945095323508319876805002546292215567443000000000",
]

def get_tarball_base64():
    """Get base64-encoded K3 tarball"""
    result = subprocess.run(['base64', 'k3_updated.tar.gz'], capture_output=True, text=True)
    return result.stdout.strip()

def execute_code(code, timeout=600):
    """Execute code on Jupyter kernel and return output"""
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
                for line in content.get("traceback", []):
                    print(line)
                break
            elif msg_type == "execute_reply":
                status = content.get("status", "")
                if status == "ok":
                    print("\n=== Command completed ===\n")
                elif status == "error":
                    print(f"\n=== Failed: {content.get('ename')} ===\n")
                break
        except websocket.WebSocketTimeoutException:
            continue
        except Exception as e:
            print(f"Error: {e}")
            break

    ws.close()
    return "".join(output_lines)


def main():
    print("="*60)
    print("K3 Deployment with Decimal Starting Ranges")
    print("="*60)

    # Step 1: Upload K3 tarball
    print("\n[1/4] Uploading K3 code to GPU server...")
    tarball_b64 = get_tarball_base64()

    upload_code = f'''
import base64
import os

os.chdir("/workspace")

# Decode and save tarball
tarball_data = base64.b64decode("""{tarball_b64}""")
with open("k3_updated.tar.gz", "wb") as f:
    f.write(tarball_data)

# Extract
import subprocess
result = subprocess.run(["tar", "-xzvf", "k3_updated.tar.gz"], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("Error:", result.stderr)
else:
    print("K3 code uploaded and extracted successfully!")
'''
    execute_code(upload_code, timeout=60)

    # Step 2: Build K3
    print("\n[2/4] Building K3 with CUDA...")
    build_code = '''
import subprocess
import os

os.chdir("/workspace/k3")

# Clean and build
print("Cleaning...")
subprocess.run(["make", "clean"], capture_output=True)

print("Building K3 with CUDA 13.0, compute capability 89 (RTX 4080)...")
result = subprocess.run(["make", "-j8"], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print("Build error:", result.stderr)
else:
    print("Build successful!")

# Verify binary exists
import os
if os.path.exists("BloomSearch32K3"):
    print("Binary created: BloomSearch32K3")
    result = subprocess.run(["ls", "-la", "BloomSearch32K3"], capture_output=True, text=True)
    print(result.stdout)
else:
    print("ERROR: Binary not found!")
'''
    execute_code(build_code, timeout=300)

    # Step 3: Stop any existing K3 processes
    print("\n[3/4] Stopping any existing K3 processes...")
    stop_code = '''
import subprocess
import os

# Kill existing K3 processes
result = subprocess.run(["pkill", "-f", "BloomSearch32K3"], capture_output=True)
print("Stopped existing K3 processes")

# Check GPU status
print("\\nGPU Status:")
result = subprocess.run(["nvidia-smi", "--query-gpu=index,name,utilization.gpu,memory.used", "--format=csv"],
                       capture_output=True, text=True)
print(result.stdout)

# Check data files exist
print("\\nChecking data files...")
for f in ["/data/prefix32.bin", "/data/bloom_filter.bin", "/data/bloom_seeds.bin"]:
    if os.path.exists(f):
        size = os.path.getsize(f) / (1024*1024)
        print(f"  {f}: {size:.1f} MB")
    else:
        print(f"  {f}: NOT FOUND")
'''
    execute_code(stop_code, timeout=60)

    # Step 4: Launch K3 on all 8 GPUs with decimal starting ranges
    print("\n[4/4] Launching K3 on all 8 GPUs with decimal starting ranges...")

    # Build the launch commands
    launch_commands = []
    for gpu_id, start in enumerate(DECIMAL_STARTS):
        cmd = f'''nohup /workspace/k3/BloomSearch32K3 \\
    -gpu {gpu_id} \\
    -prefix /data/prefix32.bin \\
    -bloom /data/bloom_filter.bin \\
    -seeds /data/bloom_seeds.bin \\
    -bits 8589934592 \\
    -start "{start}" \\
    -state /tmp/gpu{gpu_id}_k3_decimal.state \\
    -both \\
    > /tmp/k3_gpu{gpu_id}.log 2>&1 &'''
        launch_commands.append(cmd)

    launch_script = "\n".join(launch_commands)

    launch_code = f'''
import subprocess
import time
import os

os.chdir("/workspace/k3")

# Launch all GPUs
print("Launching K3 on 8 GPUs with decimal starting ranges...")
print("")

{chr(10).join([f'print("GPU {i}: {DECIMAL_STARTS[i][:30]}...")' for i in range(8)])}
print("")

# Launch script
launch_script = """
{launch_script}
"""

result = subprocess.run(["bash", "-c", launch_script], capture_output=True, text=True)
if result.stdout:
    print(result.stdout)
if result.stderr:
    print(result.stderr)

time.sleep(3)

# Verify processes are running
print("\\nVerifying processes...")
result = subprocess.run(["pgrep", "-af", "BloomSearch32K3"], capture_output=True, text=True)
print(result.stdout)

# Check GPU utilization
print("\\nGPU Utilization:")
result = subprocess.run(["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used", "--format=csv"],
                       capture_output=True, text=True)
print(result.stdout)

# Show initial log output
print("\\nInitial log output (GPU 0):")
time.sleep(5)
result = subprocess.run(["tail", "-20", "/tmp/k3_gpu0.log"], capture_output=True, text=True)
print(result.stdout)
'''
    execute_code(launch_code, timeout=120)

    print("="*60)
    print("DEPLOYMENT COMPLETE")
    print("="*60)
    print("\nK3 is now running on all 8 GPUs with your decimal starting ranges.")
    print("\nMonitor with:")
    print("  tail -f /tmp/k3_gpu*.log")
    print("\nCheck GPU usage:")
    print("  nvidia-smi")
    print("\nStop all:")
    print("  pkill -f BloomSearch32K3")


if __name__ == "__main__":
    main()
