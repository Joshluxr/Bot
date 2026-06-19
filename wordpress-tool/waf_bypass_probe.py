#!/usr/bin/env python3
"""
AUTHZ-VULN-01 — CloudFront WAF bypass probe (read-only).

Checks whether /wp-login.php is blocked while percent-encoded variants
(e.g. /wp%2Dlogin.php) still reach the WordPress login page.
"""

import argparse
import sys
from urllib.parse import urljoin

import requests
import urllib3
from colorama import Fore, Style, init

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
init(autoreset=True)

LOGIN_PATHS = [
    ('/wp-login.php', 'standard'),
    ('/wp%2Dlogin.php', 'encoded-hyphen-upper'),
    ('/wp%2dlogin.php', 'encoded-hyphen-lower'),
]

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
}


def normalize_base(url: str) -> str:
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.rstrip('/')


def is_wp_login_page(text: str) -> bool:
    text = text.lower()
    return any(token in text for token in ('wp-login', 'user_login', 'wp-submit', 'wordpress'))


def probe_path(session: requests.Session, base: str, path: str) -> dict:
    url = base + path
    try:
        resp = session.get(url, headers=HEADERS, timeout=15, verify=False, allow_redirects=True)
        return {
            'url': url,
            'status': resp.status_code,
            'login_page': resp.status_code == 200 and is_wp_login_page(resp.text),
            'error': None,
        }
    except requests.RequestException as exc:
        return {'url': url, 'status': None, 'login_page': False, 'error': str(exc)}


def run_probe(target: str) -> int:
    base = normalize_base(target)
    session = requests.Session()
    session.verify = False

    print(f'\n{Style.BRIGHT}AUTHZ-VULN-01 CloudFront WAF Bypass Probe{Style.RESET_ALL}')
    print(f'Target: {base}\n')

    results = []
    for path, label in LOGIN_PATHS:
        result = probe_path(session, base, path)
        result['label'] = label
        results.append(result)

        status = result['status'] if result['status'] is not None else 'ERR'
        if result['error']:
            color = Fore.RED
            detail = result['error'][:80]
        elif result['login_page']:
            color = Fore.GREEN
            detail = 'WordPress login page reachable'
        elif result['status'] == 403:
            color = Fore.YELLOW
            detail = 'Blocked by WAF'
        else:
            color = Fore.WHITE
            detail = 'No login page detected'

        print(f'  [{label:22}] {status!s:>4}  {color}{detail}{Style.RESET_ALL}')

    standard = results[0]
    bypass_hits = [r for r in results[1:] if r['login_page']]

    print()
    if standard['status'] == 403 and bypass_hits:
        print(Fore.RED + Style.BRIGHT + 'VULNERABLE: WAF blocks standard path but encoded bypass works.')
        for hit in bypass_hits:
            print(Fore.RED + f'  Bypass URL: {hit["url"]}')
        return 2

    if standard['login_page']:
        print(Fore.YELLOW + 'Standard login path is publicly reachable (no WAF block on /wp-login.php).')
        return 1

    if bypass_hits:
        print(Fore.YELLOW + 'Encoded login paths reachable; verify WAF policy manually.')
        return 1

    print(Fore.GREEN + 'No reachable WordPress login surface detected via tested paths.')
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description='Probe CloudFront WAF wp-login bypass (AUTHZ-VULN-01)')
    parser.add_argument('target', help='Base URL, e.g. https://example.com')
    args = parser.parse_args()
    sys.exit(run_probe(args.target))


if __name__ == '__main__':
    main()
