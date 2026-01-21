#!/usr/bin/env python3
"""Check K3 status on GPU server"""

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

def execute_code(code, timeout=60):
    """Execute code on Jupyter kernel and return output"""
    ws_url = f"wss://{JUPYTER_URL}/api/kernels/{KERNEL_ID}/channels?token={TOKEN}"

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE}, timeout=10)
    except Exception as e:
        print(f"Connection failed: {e}")
        return ""

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
            ws.settimeout(5)
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
                    print("\n=== Command completed ===")
                elif status == "error":
                    print(f"\n=== Failed: {content.get('ename')} ===")
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
    print("Checking GPU Server Status")
    print("="*60)

    # Check K3 processes
    print("\n[1] Checking K3 processes...")
    execute_code('''
import subprocess

# Check running K3 processes
result = subprocess.run(["pgrep", "-af", "BloomSearch32K3"], capture_output=True, text=True)
if result.stdout:
    print("Running K3 processes:")
    print(result.stdout)
else:
    print("No K3 processes running")

# Check GPU status
print("\\nGPU Status:")
result = subprocess.run(["nvidia-smi", "--query-gpu=index,name,utilization.gpu,memory.used", "--format=csv"],
                       capture_output=True, text=True)
print(result.stdout)
''', timeout=30)

    # Check data files
    print("\n[2] Checking data files...")
    execute_code('''
import os

print("Data files:")
for f in ["/data/prefix32.bin", "/data/bloom_filter.bin", "/data/bloom_seeds.bin", "/data/bloom_opt.h160db"]:
    if os.path.exists(f):
        size = os.path.getsize(f) / (1024*1024)
        print(f"  {f}: {size:.2f} MB")
    else:
        print(f"  {f}: NOT FOUND")
''', timeout=30)

    # Check latest K3 logs
    print("\n[3] Checking K3 logs...")
    execute_code('''
import subprocess
import os
import glob

# Find log files
log_files = glob.glob("/tmp/k3_gpu*.log") + glob.glob("/tmp/gpu*_k3*.log") + glob.glob("/root/gpu*_k3*.log")
print(f"Found log files: {log_files}")

for log in sorted(log_files)[:3]:
    if os.path.exists(log):
        print(f"\\n=== Last 30 lines of {log} ===")
        result = subprocess.run(["tail", "-30", log], capture_output=True, text=True)
        print(result.stdout)
''', timeout=30)

if __name__ == "__main__":
    main()
