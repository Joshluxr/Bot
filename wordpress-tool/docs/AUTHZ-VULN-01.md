# AUTHZ-VULN-01 — CloudFront WAF Bypass on WordPress Login

## Summary

Some AWS CloudFront WAF rules block requests containing the literal string `wp-login.php` in the URL path. The rule does **not** normalize percent-encoded characters before matching. Apache (and most origin servers) decode `%2D` to `-`, so an encoded path reaches the same WordPress login handler.

| Request path       | WAF sees          | Origin serves      | Typical result |
|--------------------|-------------------|--------------------|----------------|
| `/wp-login.php`    | `wp-login.php`    | `wp-login.php`     | **403 Blocked** |
| `/wp%2Dlogin.php`  | `wp%2Dlogin.php`  | `wp-login.php`     | **200 Login page** |

## Impact

When this bypass works, protections intended to hide WordPress authentication are ineffective:

1. **Login exposure** — Public access to the admin login form
2. **User enumeration** — Different error strings for valid vs invalid usernames
3. **Password reset probing** — `/wp%2Dlogin.php?action=lostpassword` reveals valid accounts
4. **Brute force** — If no rate limiting, CAPTCHA, or lockout exists behind the WAF

## Detection (read-only)

Use the included probe script against **authorized** targets only:

```bash
cd wordpress-tool
pip install -r requirements.txt
python3 waf_bypass_probe.py https://your-target.example
```

Exit codes:

- `0` — No login surface detected on tested paths
- `1` — Login reachable (review WAF policy)
- `2` — **Vulnerable** — standard path blocked, encoded bypass works

## Remediation

### CloudFront / WAF

1. **Normalize URLs before rule evaluation** — Decode percent-encoding (and ideally apply Unicode normalization) prior to string matching.
2. **Block at origin** — Restrict `/wp-login.php` (and variants) via Apache/nginx `LocationMatch` or WordPress hardening plugins, not WAF alone.
3. **Use managed rule groups** — AWS AWSManagedRulesCommonRuleSet includes normalization; verify custom rules do too.
4. **Add defense in depth**:
   - Rate limiting on login (e.g. Wordfence, fail2ban, CloudFront rate-based rules)
   - CAPTCHA on `wp-login.php`
   - Disable user enumeration (`/wp-json/wp/v2/users` and login errors)
   - Require 2FA for all admin accounts
   - Remove or rename test accounts (e.g. `*-test-admin`)

### Apache origin example

```apache
# Deny encoded login path variants at the origin
<LocationMatch "(?i)/wp(%2[dD]|[-])login\.php">
    Require all denied
</LocationMatch>
```

### WordPress

- Move login to a non-default URL (plugin or custom endpoint)
- Disable REST API user listing for unauthenticated requests
- Enforce strong passwords and 2FA

## Tooling in this repo

| File | Purpose |
|------|---------|
| `BRUTER.py` | WordPress checker with WAF bypass login path resolution |
| `waf_bypass_probe.py` | Read-only AUTHZ-VULN-01 detection |
| `execut.sh` | Linux launcher for batch runs |
| `sites/*.txt` | Target lists (one URL per line) |

**Use only on systems you own or have explicit written authorization to test.**
