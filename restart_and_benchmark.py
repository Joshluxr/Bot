#!/usr/bin/env python3
"""
Restart VanitySearch with harder prefix and monitor performance
"""

import json
import ssl
import uuid
import websocket
import time

JUPYTER_URL = "74.48.140.178:25349"
TOKEN = "afebbf7c1170dd3aeecb6dd1e1bf3930efa6420680734908e23cc38dc3ef63f7"
KERNEL_ID = "572a883c-5fbf-429a-b569-e3073acde909"

RESTART_CODE = '''
import subprocess
import os
import time

os.chdir("/workspace/Bot/vanitysearch_analysis")

print("=" * 60)
print("RESTARTING VANITYSEARCH WITH HARD PREFIX")
print("=" * 60)
print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("")

# Start VanitySearch searching for the hard prefix
print("Starting VanitySearch with prefix: 1GUNPhjykrBdET")
print("This is a 14-character prefix - extremely difficult!")
print("")

proc = subprocess.Popen(
    ["./VanitySearch", "-gpu", "-gpuId", "0,1,2,3", "-o", "found_hard.txt", "-t", "0", "1GUNPhjykrBdET"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Monitor output for 60 seconds to capture performance stats
start_time = time.time()
monitor_duration = 60

performance_lines = []
try:
    while True:
        line = proc.stdout.readline()
        if line:
            print(line, end='', flush=True)
            if "key/s" in line.lower() or "Mkey" in line or "Gkey" in line:
                performance_lines.append(line.strip())

        if time.time() - start_time > monitor_duration:
            print("\\n" + "=" * 60)
            print("MONITORING COMPLETE - VanitySearch continues in background")
            print("=" * 60)
            break

        if proc.poll() is not None:
            remaining = proc.stdout.read()
            if remaining:
                print(remaining)
            break
except KeyboardInterrupt:
    print("\\nMonitoring interrupted")

# Summary
print("")
print("Performance Summary:")
print("-" * 40)
for line in performance_lines[-5:]:
    print(line)

print("")
print("VanitySearch is now running in background.")
print("Check found_hard.txt for results (if any).")
'''

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
            "code": RESTART_CODE,
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
    print("Monitoring VanitySearch for 60 seconds...\n")

    start_time = time.time()
    timeout = 120

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
                break

        except Exception as e:
            print(f"Error: {e}")
            break

    ws.close()

if __name__ == "__main__":
    execute_code()
