#!/usr/bin/env python3
"""Continuous monitoring of VanitySearch on GPU server"""

import json
import ssl
import uuid
import websocket
import time
import requests
import sys

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"

def check_status():
    """Check the current status of VanitySearch"""
    # Get existing kernels
    try:
        response = requests.get(
            f"https://{JUPYTER_URL}/api/kernels",
            headers={"Authorization": f"token {TOKEN}"},
            verify=False,
            timeout=10
        )
        kernels = response.json()
        if not kernels:
            print("No kernels available")
            return None
        kernel_id = kernels[0]["id"]
    except Exception as e:
        print(f"Connection error: {e}")
        return None

    CODE = '''
import os
import subprocess
import time

path = "/workspace/Bot/vanitysearch_analysis/found.txt"
count = 0
if os.path.exists(path):
    with open(path, "r") as f:
        count = sum(1 for _ in f)

# Check if running
proc = subprocess.run(["pgrep", "-c", "VanitySearch"], capture_output=True, text=True)
running = proc.stdout.strip()

# Get file size
size = os.path.getsize(path) if os.path.exists(path) else 0

print(f"TIME: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"ADDRESSES FOUND: {count:,}")
print(f"FILE SIZE: {size:,} bytes")
print(f"PROCESSES RUNNING: {running}")
'''

    try:
        ws_url = f"wss://{JUPYTER_URL}/api/kernels/{kernel_id}/channels?token={TOKEN}"
        ws = websocket.create_connection(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE}, timeout=15)

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

        output = ""
        start_time = time.time()
        while time.time() - start_time < 20:
            try:
                msg = ws.recv()
                response = json.loads(msg)
                msg_type = response.get("msg_type", "")
                content = response.get("content", {})

                if msg_type == "stream":
                    output += content.get("text", "")
                elif msg_type == "execute_reply":
                    break
            except:
                break

        ws.close()
        return output
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print("=" * 60)
    print("VanitySearch Continuous Monitor")
    print("=" * 60)
    print("Checking status every 60 seconds...")
    print("Press Ctrl+C to stop monitoring\n")
    
    check_num = 0
    while True:
        check_num += 1
        print(f"\n--- Check #{check_num} ---")
        result = check_status()
        if result:
            print(result)
        else:
            print("Failed to get status")
        
        print("-" * 40)
        time.sleep(60)
