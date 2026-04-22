#!/usr/bin/env python3
"""
Direct deployment via websocket with retry logic
"""

import json
import time
import sys

try:
    import websocket
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "websocket-client", "-q"])
    import websocket

GPU_SERVER = "100.66.143.247"
JUPYTER_PORT = 8888
JUPYTER_TOKEN = "vanitysearch"

def execute_code(code, timeout=600):
    """Execute code on GPU server"""
    import urllib.request

    # Get kernel ID
    try:
        url = f"http://{GPU_SERVER}:{JUPYTER_PORT}/api/kernels?token={JUPYTER_TOKEN}"
        req = urllib.request.Request(url, headers={"Authorization": f"token {JUPYTER_TOKEN}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            kernels = json.loads(resp.read())
            if kernels:
                kernel_id = kernels[0]['id']
            else:
                # Create new kernel
                req = urllib.request.Request(
                    f"http://{GPU_SERVER}:{JUPYTER_PORT}/api/kernels",
                    data=json.dumps({"name": "python3"}).encode(),
                    headers={"Authorization": f"token {JUPYTER_TOKEN}", "Content-Type": "application/json"},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    kernel_id = json.loads(resp.read())['id']
        print(f"Using kernel: {kernel_id}")
    except Exception as e:
        print(f"Failed to get kernel: {e}")
        return None

    # Connect via WebSocket
    ws_url = f"ws://{GPU_SERVER}:{JUPYTER_PORT}/api/kernels/{kernel_id}/channels?token={JUPYTER_TOKEN}"

    try:
        ws = websocket.create_connection(ws_url, timeout=timeout)
    except Exception as e:
        print(f"WebSocket connection failed: {e}")
        return None

    # Send execute request
    msg_id = f"exec_{time.time()}"
    msg = {
        "header": {
            "msg_id": msg_id,
            "msg_type": "execute_request",
            "username": "",
            "session": msg_id,
            "version": "5.3"
        },
        "parent_header": {},
        "metadata": {},
        "content": {
            "code": code,
            "silent": False,
            "store_history": False,
            "user_expressions": {},
            "allow_stdin": False
        }
    }

    ws.send(json.dumps(msg))
    print("Code sent, waiting for response...")

    # Collect output
    output = []
    start = time.time()

    while time.time() - start < timeout:
        try:
            ws.settimeout(10)
            data = json.loads(ws.recv())
            msg_type = data.get("msg_type", "")

            if msg_type == "stream":
                text = data["content"].get("text", "")
                output.append(text)
                print(text, end="", flush=True)
            elif msg_type == "execute_result":
                text = data["content"].get("data", {}).get("text/plain", "")
                output.append(text)
                print(text)
            elif msg_type == "error":
                tb = "\n".join(data["content"].get("traceback", []))
                print(f"\nERROR:\n{tb}")
                output.append(tb)
            elif msg_type == "execute_reply":
                status = data["content"].get("status")
                print(f"\n[Execution {status}]")
                break

        except websocket.WebSocketTimeoutException:
            print(".", end="", flush=True)
            continue
        except Exception as e:
            print(f"\nError receiving: {e}")
            break

    ws.close()
    return "".join(output)

def main():
    print("=" * 60)
    print("BloomSearch Deployment")
    print("=" * 60)

    # Step 1: Test connection and check status
    print("\n[1] Checking server status...")

    status_code = '''
import os
os.chdir('/root/VanitySearch')
print(f"Working directory: {os.getcwd()}")

# Check existing files
files = ['targets.bloom', 'targets.sorted', 'Bitcoin_addresses_LATEST.txt']
for f in files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  {f}: {size/1024/1024:.1f} MB")
    else:
        print(f"  {f}: NOT FOUND")

# Check GPU
import subprocess
result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                       capture_output=True, text=True)
print(f"\\nGPUs:\\n{result.stdout}")
'''

    result = execute_code(status_code, timeout=60)
    if result is None:
        print("Failed to connect to server")
        return

    # Step 2: Build bloom filter if needed
    print("\n[2] Checking/building bloom filter...")

    build_code = '''
import os
os.chdir('/root/VanitySearch')

# Check if bloom filter exists
if os.path.exists('targets.bloom') and os.path.getsize('targets.bloom') > 100000000:
    import struct
    with open('targets.bloom', 'rb') as f:
        num_bits = struct.unpack('<Q', f.read(8))[0]
        num_bytes = struct.unpack('<Q', f.read(8))[0]
        num_hashes = struct.unpack('<I', f.read(4))[0]
        item_count = struct.unpack('<I', f.read(4))[0]
    print("Bloom filter exists:")
    print(f"  Items: {item_count:,}")
    print(f"  Size: {num_bytes/1024/1024:.1f} MB")
    print(f"  Hash functions: {num_hashes}")
else:
    print("Bloom filter not found - needs to be built")
    print("Run: python3 build_bloom.py")
'''

    execute_code(build_code, timeout=60)

    print("\n" + "=" * 60)
    print("Deployment check complete!")
    print("=" * 60)
    print("""
Next steps:

1. If bloom filter doesn't exist, upload build_bloom.py and run it:
   scp DEPLOY_PACKAGE/build_bloom.py root@100.66.143.247:/root/VanitySearch/
   ssh root@100.66.143.247 'cd /root/VanitySearch && python3 build_bloom.py'

2. Upload GPU kernel header:
   scp DEPLOY_PACKAGE/GPUComputeBloom.h root@100.66.143.247:/root/VanitySearch/GPU/

3. Integrate and test (see README.txt for details)
""")

if __name__ == "__main__":
    main()
