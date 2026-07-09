#!/usr/bin/env python3
"""Read found.txt using a new kernel session"""

import json
import ssl
import uuid
import websocket
import time
import requests

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"

# Create a new kernel
print("Creating new kernel...")
response = requests.post(
    f"https://{JUPYTER_URL}/api/kernels",
    headers={"Authorization": f"token {TOKEN}"},
    verify=False
)

if response.status_code == 201:
    kernel_info = response.json()
    kernel_id = kernel_info["id"]
    print(f"Created kernel: {kernel_id}")
else:
    print(f"Failed to create kernel: {response.status_code}")
    print("Using existing kernel...")
    # List kernels
    response = requests.get(
        f"https://{JUPYTER_URL}/api/kernels",
        headers={"Authorization": f"token {TOKEN}"},
        verify=False
    )
    kernels = response.json()
    if kernels:
        kernel_id = kernels[0]["id"]
        print(f"Using kernel: {kernel_id}")
    else:
        exit(1)

CODE = '''
import os

# Read the found.txt file
path = "/workspace/Bot/vanitysearch_analysis/found.txt"
if os.path.exists(path):
    with open(path, "r") as f:
        content = f.read()
    
    lines = content.strip().split("\\n") if content.strip() else []
    print(f"TOTAL FOUND: {len(lines)} addresses")
    print("")
    print("=" * 100)
    print("SAMPLE ADDRESSES (showing format)")
    print("=" * 100)
    for i, line in enumerate(lines[:15]):
        print(line)
    if len(lines) > 15:
        print(f"\\n... {len(lines) - 15} more addresses ...")
        print("\\nLAST 5:")
        for line in lines[-5:]:
            print(line)
else:
    print("File not found")

import subprocess
proc = subprocess.run(["pgrep", "-c", "VanitySearch"], capture_output=True, text=True)
print(f"\\nVanitySearch processes running: {proc.stdout.strip()}")
'''

ws_url = f"wss://{JUPYTER_URL}/api/kernels/{kernel_id}/channels?token={TOKEN}"
ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})

# Wait for kernel to be ready
time.sleep(2)

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
print("Reading file...\n")

start_time = time.time()
while time.time() - start_time < 30:
    try:
        msg = ws.recv()
        response = json.loads(msg)
        msg_type = response.get("msg_type", "")
        content = response.get("content", {})

        if msg_type == "stream":
            print(content.get("text", ""), end="")
        elif msg_type == "execute_reply":
            break
    except Exception as e:
        print(f"Error: {e}")
        break

ws.close()
