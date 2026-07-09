#!/usr/bin/env python3
"""Read found.txt directly from GPU server"""

import json
import ssl
import uuid
import websocket
import time

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

CODE = """
import os

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=" * 80)
print("SAMPLE FOUND ADDRESSES (first 30 lines)")
print("=" * 80)

if os.path.exists("found.txt"):
    with open("found.txt", "r") as f:
        lines = f.readlines()
    
    print(f"\\nTotal addresses found: {len(lines)}")
    print("")
    
    # Show first 30 entries
    for i, line in enumerate(lines[:30]):
        print(line.rstrip())
    
    if len(lines) > 30:
        print(f"\\n... ({len(lines) - 30} more addresses in file)")
        
        print("\\n" + "=" * 80)
        print("LAST 10 ADDRESSES (most recent)")
        print("=" * 80)
        for line in lines[-10:]:
            print(line.rstrip())
else:
    print("found.txt not found!")
"""

def execute_code():
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

    start_time = time.time()
    timeout = 30

    while True:
        if time.time() - start_time > timeout:
            break

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

if __name__ == "__main__":
    execute_code()
