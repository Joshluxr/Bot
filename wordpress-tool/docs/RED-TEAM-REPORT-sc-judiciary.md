# Red Team Final Analysis — sc.judiciary.gov.ph

**Classification:** Authorized Assessment / Client Deliverable  
**Target:** https://sc.judiciary.gov.ph  
**Finding ID:** AUTHZ-VULN-01 (and related)  
**Assessment date:** 2026-05-28  

---

## Executive Summary

Testing against `sc.judiciary.gov.ph` confirms a WordPress installation behind **AWS CloudFront** and **Apache/2.4.58 (Ubuntu)**. The originally reported **CloudFront WAF bypass** via `/wp%2Dlogin.php` appears **remediated** from current testing — all tested login path variants return **403 Forbidden**. However, **secondary authentication weaknesses remain**, including unauthenticated **REST API user enumeration** and **author archive disclosure**, which partially undermine the WAF’s intent to hide WordPress authentication surfaces.

| Finding | Severity | Status |
|---------|----------|--------|
| AUTHZ-VULN-01 — CloudFront WAF wp-login bypass | Critical | **Remediated** (retest recommended from client network) |
| AUTHZ-VULN-02 — REST API user enumeration | High | **Open** |
| AUTHZ-VULN-03 — Author archive username disclosure | Medium | **Open** |
| INFO-01 — XML-RPC blocked | Info | **Mitigated** |
| INFO-02 — Brute-force/rate-limit (login surface) | N/A | **Not testable** (login blocked at WAF) |

---

## AUTHZ-VULN-01 — CloudFront WAF Bypass (Historical / Retest)

### Original vulnerability

CloudFront WAF used **literal string matching** on `wp-login.php` without URL normalization. Requesting `/wp%2Dlogin.php` passed the WAF while Apache decoded `%2D` → `-` and served the login page.

### Current state (2026-05-28 retest)

| Path | HTTP Status | Login page |
|------|-------------|------------|
| `/wp-login.php` | 403 | No |
| `/wp%2Dlogin.php` | 403 | No |
| `/wp%2dlogin.php` | 403 | No |
| `/wp%2Dlogin%2ephp` | 403 | No |
| `/%77p-login.php` | 403 | No |

POST attempts to both standard and encoded login paths also return **403**.

**Conclusion:** WAF policy appears updated to block encoded variants, or origin/CloudFront now normalizes paths before rule evaluation. **Recommend client verify from their authorized red team egress** in case geo/IP-based rules differ.

### If bypass were still active — impact chain

1. Public WordPress login exposure  
2. Username enumeration via differential error messages  
3. Password reset user confirmation via `?action=lostpassword`  
4. Unrestricted brute force absent rate limiting / 2FA / lockout  

---

## AUTHZ-VULN-02 — REST API User Enumeration (Open)

**Endpoint:** `GET /wp-json/wp/v2/users` → **200 OK**

Confirmed accounts (matches prior assessment):

| ID | Username (slug) | Display name | Notes |
|----|-----------------|--------------|-------|
| 1 | `scweb` | scweb | First user — likely site administrator |
| 2 | `pio_tyke` | tyke pio | PIO content editor |
| 16 | `pio_jerome` | pio jerome | PIO content editor |
| 204 | `tyke-test-admin` | tyke Flores | Name suggests admin/test account — high value |
| 205 | `pio_rus` | Rus Narito | PIO content editor |

Individual user objects are also exposed, e.g. `GET /wp-json/wp/v2/users/1`.

**Impact:** Attackers can build username lists for credential stuffing without touching the blocked login form.

**Remediation:**

- Disable unauthenticated user listing (`rest_authentication_errors` filter or security plugin)
- Require authentication for `/wp/v2/users`
- Remove or rename test accounts (`tyke-test-admin`)

---

## AUTHZ-VULN-03 — Author Archive Disclosure (Open)

- `GET /?author=1` → **301** redirect to author archive  
- `GET /author/scweb/` → **200 OK**

WordPress author IDs and slugs are publicly discoverable independent of the login WAF.

**Remediation:** Disable author archives or redirect them; use security plugin to block `?author=` enumeration.

---

## INFO-01 — XML-RPC

`GET/POST /xmlrpc.php` → **403** (blocked at CloudFront). Good defensive posture.

---

## INFO-02 — Rate Limiting / Brute Force

Login surface is **not reachable** (403 at WAF), so login brute force and rate-limit testing could not be performed in this retest. If AUTHZ-VULN-01 were reintroduced or bypassed via another vector, absence of rate limiting would remain a concern based on prior testing.

---

## Infrastructure Observed

| Layer | Value |
|-------|-------|
| CDN/WAF | Amazon CloudFront (`X-Amz-Cf-Pop: IAD55-P6`) |
| Load balancer | AWS ELB (`awselb/2.0`) on blocked paths |
| Origin | Apache/2.4.58 (Ubuntu) |
| CMS | WordPress (confirmed via `/wp-json/`, `/readme.html`, homepage generator) |

---

## Recommended Remediation Priority

1. **Verify AUTHZ-VULN-01 fix** — regression test encoded paths after any WAF change  
2. **Close REST API enumeration** — highest remaining auth exposure  
3. **Disable author enumeration** — `?author=` and `/author/{slug}/`  
4. **Harden high-value accounts** — enforce 2FA, remove `tyke-test-admin` or restrict privileges  
5. **Defense in depth at origin** — do not rely on WAF alone for `/wp-login.php`  
6. **Enable login rate limiting / CAPTCHA** — for when login is intentionally exposed (e.g. VPN-only admin)

---

## Tooling Used

```bash
cd wordpress-tool
pip install -r requirements.txt

# Read-only engagement recon (generates JSON evidence)
python3 engagement_recon.py

# WAF bypass probe
python3 waf_bypass_probe.py https://sc.judiciary.gov.ph
```

Evidence artifact: `readyTouse/AUTHZ-VULN-01-recon.json`

---

## Limitations

- Testing performed from cloud egress (IAD55-P6); results may differ by source IP or geography  
- Login brute force **not executed** — login surface blocked during retest  
- Password reset flow **not tested** — requires reachable login form  

---

*Prepared for authorized red team delivery to sc.judiciary.gov.ph security stakeholders.*
