#!/usr/bin/env python3
"""Minimal WAF + WordPress login simulator for offline tests (no Docker)."""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

WP_LOGIN_HTML = """<!DOCTYPE html><html><body class="login">
<form name="loginform" id="loginform" action="/wp-login.php" method="post">
<p><label>Username or Email Address</label><input type="text" name="log" id="user_login"/></p>
<p><label>Password</label><input type="password" name="pwd" id="user_pass"/></p>
<p><input type="submit" name="wp-submit" id="wp-submit" value="Log In"/></p>
</form></body></html>"""

VALID_USERS = {"admin", "scweb", "tyke-test-admin"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str, content_type: str = "text/html") -> None:
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _waf_block(self, uri: str) -> bool:
        # Literal substring match like CloudFront (no URL decode)
        return "wp-login.php" in uri

    def do_GET(self) -> None:
        uri = self.path
        if uri == "/health":
            return self._send(200, json.dumps({"ok": True}), "application/json")
        if self._waf_block(uri):
            return self._send(403, "WAF: blocked wp-login.php (literal match)")
        if "wp" in uri.lower() and "login" in uri.lower():
            return self._send(200, WP_LOGIN_HTML)
        return self._send(404, "not found")

    def do_POST(self) -> None:
        uri = self.path
        if self._waf_block(uri):
            return self._send(403, "WAF: blocked")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else ""
        fields = {k: v[0] for k, v in parse_qs(body).items()}
        user = fields.get("log", "")
        pwd = fields.get("pwd", "")
        if user == "admin" and pwd == "admin123":
            return self._send(200, "LOGIN_SUCCESS redirect wp-admin")
        if user in VALID_USERS:
            return self._send(200, '<div id="login_error">Error: The password you entered for the username is incorrect.</div>')
        return self._send(200, '<div id="login_error">Error: Invalid username.</div>')

    def log_message(self, fmt: str, *args) -> None:
        print(f"[mock-waf] {fmt % args}")


def main() -> None:
    server = HTTPServer(("127.0.0.1", 8080), Handler)
    print("[mock-waf] listening on http://127.0.0.1:8080")
    server.serve_forever()


if __name__ == "__main__":
    main()
