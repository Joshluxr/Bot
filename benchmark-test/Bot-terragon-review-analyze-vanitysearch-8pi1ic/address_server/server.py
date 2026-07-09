#!/usr/bin/env python3
"""Simple HTTP server to serve found addresses file"""

import http.server
import socketserver
import os

PORT = 8080
DIRECTORY = "/root/repo/address_server"

os.chdir(DIRECTORY)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://0.0.0.0:{PORT}")
    print(f"Access found.txt at http://localhost:{PORT}/found.txt")
    httpd.serve_forever()
