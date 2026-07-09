#!/usr/bin/env python3
"""Run VanitySearch on GPU server and monitor output"""

import json
import ssl
import uuid
import websocket
import time
import sys

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

# Code to start VanitySearch
CODE = """
import subprocess
import os
import sys
import select
import time

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=" * 60)
print("VanitySearch - GPU Vanity Address Generator")
print("=" * 60)
print(f"Target: 1GUNPh")
print(f"GPUs: 4x RTX 4080 SUPER")
print(f"Start: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print("")

# Start VanitySearch
proc = subprocess.Popen(
    ["./VanitySearch", "-gpu", "-gpuId", "0,1,2,3", "-o", "found_1GUNPh.txt", "-t", "0", "1GUNPh"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Stream output
start = time.time()
found_count = 0

while proc.poll() is None:
    line = proc.stdout.readline()
    if line:
        print(line, end='', flush=True)
        if "Pub Addr" in line or "found" in line.lower():
            found_count += 1

# Get any remaining output
out, _ = proc.communicate()
if out:
    print(out)

print("")
print("=" * 60)
print(f"Completed. Found {found_count} addresses.")
print(f"Results saved to: found_1GUNPh.txt")
print("=" * 60)
"""

def execute():
    ws_url = f"wss://{JUPYTER_URL}/api/kernels/{KERNEL_ID}/channels?token={TOKEN}"

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
    print("VanitySearch started on GPU server...")
    print("Streaming output (Ctrl+C to stop monitoring):\n")

    try:
        while True:
            msg = ws.recv()
            response = json.loads(msg)

            msg_type = response.get("msg_type", "")
            content = response.get("content", {})

            if msg_type == "stream":
                text = content.get("text", "")
                print(text, end="", flush=True)
            elif msg_type == "execute_result":
                data = content.get("data", {})
                text = data.get("text/plain", "")
                print(text)
            elif msg_type == "error":
                print(f"ERROR: {content.get('ename')}: {content.get('evalue')}")
                break
            elif msg_type == "execute_reply":
                status = content.get("status", "")
                if status == "error":
                    print(f"Execution failed")
                break

    except KeyboardInterrupt:
        print("\nMonitoring stopped. VanitySearch continues on server.")
    finally:
        ws.close()

if __name__ == "__main__":
    execute()
