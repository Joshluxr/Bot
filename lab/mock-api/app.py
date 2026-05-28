"""Minimal API lab for AUTHZ-VULN-01 (IDOR) and login without rate limits."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

SECRET = b"lab-jwt-secret-change-me"
USERS = {
    1: {"id": 1, "email": "admin@lab.local", "role": "admin", "phone": "+1-555-0100"},
    2: {"id": 2, "email": "user2@lab.local", "role": "user", "phone": "+1-555-0102"},
}
PASSWORDS = {
    "admin@lab.local": "admin123",
    "user2@lab.local": "password2",
}


def b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign_jwt(payload: dict) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{body}".encode()
    sig = b64url(hmac.new(SECRET, signing_input, hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


def verify_jwt(token: str) -> dict | None:
    try:
        header, body, sig = token.split(".")
        signing_input = f"{header}.{body}".encode()
        expected = b64url(hmac.new(SECRET, signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            return None
        padded = body + "=" * (-len(body) % 4)
        import base64

        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            return {}

    def _auth_user_id(self) -> int | None:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        claims = verify_jwt(auth[7:])
        return int(claims["id"]) if claims and "id" in claims else None

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/auth/login":
            body = self._read_json()
            email = body.get("email", "")
            password = body.get("password", "")
            if PASSWORDS.get(email) != password:
                return self._json(401, {"error": "Invalid credentials"})
            user = next(u for u in USERS.values() if u["email"] == email)
            token = sign_jwt({"id": user["id"], "email": email, "exp": int(time.time()) + 3600})
            return self._json(200, {"token": token, "user": user})
        self._json(404, {"error": "not found"})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/users/"):
            requester = self._auth_user_id()
            if requester is None:
                return self._json(401, {"error": "unauthorized"})
            try:
                target_id = int(path.rsplit("/", 1)[-1])
            except ValueError:
                return self._json(400, {"error": "bad id"})
            # AUTHZ-VULN-01: no check that requester may view target_id
            user = USERS.get(target_id)
            if not user:
                return self._json(404, {"error": "not found"})
            return self._json(200, user)
        if path == "/health":
            return self._json(200, {"ok": True})
        self._json(404, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[mock-api] {self.address_string()} - {fmt % args}")


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
