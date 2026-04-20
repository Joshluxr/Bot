#!/usr/bin/env python3
"""Check found addresses and monitor VanitySearch on GPU server"""

import json
import ssl
import uuid
import websocket
import time
import sys

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

# Code to check found addresses
CODE = """
import subprocess
import os
import time

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=" * 60)
print("FOUND ADDRESSES FILE CONTENTS")
print("=" * 60)

# Check if file exists and show contents
if os.path.exists("found.txt"):
    with open("found.txt", "r") as f:
        content = f.read()
    
    lines = content.strip().split("\\n") if content.strip() else []
    print(f"Total addresses found: {len(lines)}")
    print("")
    
    # Show first 20 addresses
    print("First 20 addresses:")
    print("-" * 60)
    for i, line in enumerate(lines[:20]):
        print(f"{i+1}. {line}")
    
    if len(lines) > 20:
        print(f"\\n... and {len(lines) - 20} more addresses")
        print("\\nLast 5 addresses:")
        print("-" * 60)
        for line in lines[-5:]:
            print(line)
else:
    print("No found.txt file yet")

print("")
print("=" * 60)
print("CHECKING IF VANITYSEARCH IS STILL RUNNING")
print("=" * 60)

result = subprocess.run(["pgrep", "-a", "VanitySearch"], capture_output=True, text=True)
if result.stdout:
    print("VanitySearch is RUNNING:")
    print(result.stdout)
else:
    print("VanitySearch is NOT running")

# Show current file size and modification time
if os.path.exists("found.txt"):
    stat = os.stat("found.txt")
    print(f"\\nFile size: {stat.st_size} bytes")
    print(f"Last modified: {time.ctime(stat.st_mtime)}")

print(f"\\nCurrent time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
"""

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
    print("Checking GPU server status...\n")

    start_time = time.time()
    timeout = 60

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
            elif msg_type == "execute_result":
                data = content.get("data", {})
                text = data.get("text/plain", "")
                print(text)
            elif msg_type == "error":
                print(f"ERROR: {content.get('ename')}: {content.get('evalue')}")
                break
            elif msg_type == "execute_reply":
                status = content.get("status", "")
                if status == "ok":
                    print("\n=== Check completed ===")
                break

        except Exception as e:
            print(f"Error: {e}")
            break

    ws.close()

if __name__ == "__main__":
    execute_code()
