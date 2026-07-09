#!/usr/bin/env python3
"""Execute commands on GPU server via Jupyter kernel"""

import json
import ssl
import uuid
import websocket
import time

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

# Code to execute
CODE = """
import subprocess
import os
import threading
import time

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=== Starting VanitySearch on all 4 GPUs ===")
print("Target prefix: 1GUNPh")
print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("")

# Start VanitySearch as a background process
proc = subprocess.Popen(
    ["./VanitySearch", "-gpu", "-gpuId", "0,1,2,3", "-o", "found.txt", "-t", "0", "1GUNPh"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Read and print output in real-time for 5 minutes, then let it continue
start_time = time.time()
monitor_duration = 300  # 5 minutes of monitoring

try:
    while True:
        line = proc.stdout.readline()
        if line:
            print(line, end='', flush=True)

        # Check if we've monitored long enough
        if time.time() - start_time > monitor_duration:
            print("\\n=== Monitoring complete (5 min). Process continues in background ===")
            print(f"Check found.txt for results: cat /workspace/Bot/vanitysearch_analysis/found.txt")
            break

        # Check if process ended
        if proc.poll() is not None:
            # Read remaining output
            remaining = proc.stdout.read()
            if remaining:
                print(remaining)
            break
except KeyboardInterrupt:
    print("\\nMonitoring interrupted")
"""

def execute_code():
    ws_url = f"wss://{JUPYTER_URL}/api/kernels/{KERNEL_ID}/channels?token={TOKEN}"

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})

    msg_id = str(uuid.uuid4())

    # Send execute request
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
            "code": CODE,
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
    print("Sent execution request...")
    print("Waiting for results (this may take a few minutes)...\n")

    # Collect output
    output_lines = []
    start_time = time.time()
    timeout = 600  # 10 minutes

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
                    print("\n=== Execution completed successfully ===")
                elif status == "error":
                    print(f"\n=== Execution failed: {content.get('ename')} ===")
                break

        except websocket.WebSocketTimeoutException:
            continue
        except Exception as e:
            print(f"Error: {e}")
            break

    ws.close()
    return "".join(output_lines)

if __name__ == "__main__":
    execute_code()
