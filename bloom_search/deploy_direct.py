#!/usr/bin/env python3
"""
Direct deployment via Jupyter REST API
"""

import json
import time
import urllib.request
import ssl

GPU_SERVER = "100.66.143.247"
JUPYTER_PORT = 8888
JUPYTER_TOKEN = "vanitysearch"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def run_code(code, timeout=300):
    """Execute code via Jupyter REST API"""
    base_url = f"http://{GPU_SERVER}:{JUPYTER_PORT}"
    headers = {"Authorization": f"token {JUPYTER_TOKEN}", "Content-Type": "application/json"}

    # Get kernel list
    try:
        req = urllib.request.Request(f"{base_url}/api/kernels", headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        kernels = json.loads(resp.read())

        if not kernels:
            # Create kernel
            req = urllib.request.Request(
                f"{base_url}/api/kernels",
                data=json.dumps({"name": "python3"}).encode(),
                headers=headers,
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=10)
            kernel = json.loads(resp.read())
            kernel_id = kernel['id']
            print(f"Created kernel: {kernel_id}")
        else:
            kernel_id = kernels[0]['id']
            print(f"Using kernel: {kernel_id}")

    except Exception as e:
        print(f"Error: {e}")
        return None

    # Execute code via WebSocket
    import websocket
    ws_url = f"ws://{GPU_SERVER}:{JUPYTER_PORT}/api/kernels/{kernel_id}/channels?token={JUPYTER_TOKEN}"

    ws = websocket.create_connection(ws_url, timeout=timeout)
    msg_id = f"exec_{time.time()}"

    msg = {
        "header": {"msg_id": msg_id, "msg_type": "execute_request", "username": "", "session": msg_id, "version": "5.3"},
        "parent_header": {},
        "metadata": {},
        "content": {"code": code, "silent": False, "store_history": False, "user_expressions": {}, "allow_stdin": False}
    }

    ws.send(json.dumps(msg))

    output = []
    start = time.time()

    while time.time() - start < timeout:
        try:
            ws.settimeout(5)
            resp = ws.recv()
            data = json.loads(resp)
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
                output.append(f"ERROR: {tb}")
                print(f"ERROR: {tb}")
            elif msg_type == "execute_reply":
                break
        except websocket.WebSocketTimeoutException:
            continue
        except Exception as e:
            print(f"WS Error: {e}")
            break

    ws.close()
    return "".join(output)

if __name__ == "__main__":
    print("Testing connection...")

    # Test
    result = run_code("print('Connected!'); import os; os.chdir('/root/VanitySearch'); print(os.getcwd())")
    print(f"\nResult: {result}")
