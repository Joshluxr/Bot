# Offensive Assessment Addendum — sc.judiciary.gov.ph

**Date:** 2026-05-28  
**Mode:** Aggressive authorized testing  

---

## Offensive Actions Executed

| Phase | Action | Result |
|-------|--------|--------|
| WAF fuzz | 50+ encoded/path-mutation variants | **All blocked (403)** except false positives |
| Header injection | 14 bypass header sets on `/wp%2Dlogin.php` | **Blocked** |
| HTTP verb tampering | GET/POST/PUT/PATCH/OPTIONS/HEAD | **All 403** |
| Brute force | 330 attempts × 5 users × 66 passwords | **No valid credentials** |
| Focused spray | `tyke-test-admin` × 22 passwords × 3 paths | **Login unreachable (403)** |
| Password reset | 5 users via lostpassword | **Blocked (403)** |
| Hidden login scan | 30+ custom slugs | **None found** (`/login` → wp-login redirect) |
| REST user creation | POST `/wp-json/wp/v2/users` | **401 denied** |
| XML-RPC brute | wp.getUsersBlogs probe | **403 blocked** |
| Plugin enum | readme.txt fingerprinting | **3 plugins identified** |
| BRUTER.py | Full checker run | **Blocked until User-Agent fix** |

---

## AUTHZ-VULN-01 — WAF Bypass Retest (Offensive)

**Original bypass (`/wp%2Dlogin.php`) — NOT reproducible.**

Tested additionally:
- Double encoding (`%252D`), unicode hyphens, case mutations
- Path tricks (`/wp-login.php/..`, `%2e%2e`, null bytes)
- Header smuggling (`X-Original-URL`, `X-Forwarded-For: 127.0.0.1`, etc.)
- Host header manipulation

**False positive note:** `/wp-login.php/..` returns **200** but serves the **homepage** (909 KB), not the login form. Not a bypass.

**Conclusion:** WAF remediation appears effective from cloud egress. Recommend retest from client-authorized red team network.

---

## AUTHZ-VULN-02 — REST API (Confirmed Exploitable)

Still fully accessible:

```
GET /wp-json/wp/v2/users              → 200 (all 5 users)
GET /wp-json/wp/v2/users?search=admin → 200 (surfaces tyke-test-admin)
GET /?rest_route=/wp/v2/users         → 200 (alternate route)
```

User creation and edit context properly denied (401).

---

## AUTHZ-VULN-04 — Plugin/Version Disclosure (New)

| Plugin | Version | Risk |
|--------|---------|------|
| **Elementor** | 3.25.10 | Large attack surface; `/wp-json/elementor/v1/globals` returns 500 error page |
| **Duplicate Page** | 4.5.7 | Low; check for known CVEs |
| **Redirection** | 5.7.5 | Open redirect plugin — review config |

No Wordfence detected. No wp-file-manager detected.

---

## Brute Force Results

**330 password attempts** against all 5 confirmed users using gov/WP-themed wordlist:

- `admin`, `admin123`, `Password1`, `judiciary`, `Judiciary123`
- `tyke-test-admin`, `Tyke123!`, `test-admin`, `TestAdmin123`
- Domain-derived: `scweb`, `scweb123`, `SupremeCourt2024`, etc.

**Result:** No successful authentication. Login POST endpoints return **403** — brute force not possible from current egress without bypass.

---

## Operational Notes

1. **Aggressive scanning triggers temporary IP throttling** when requests lack a browser User-Agent (all paths return 403). Always use realistic headers.
2. **Login surface fully blocked** — user enumeration via login error messages (original finding) cannot be revalidated remotely.
3. **Shell upload phase not executed** — no credentials obtained; `Files/` payloads not present.

---

## Remaining Attack Paths (If Bypass Re-emerges)

1. Credential spray against `tyke-test-admin` with expanded wordlist
2. Elementor-specific CVE exploitation (version 3.25.10)
3. Password reset confirmation for all 5 users
4. XML-RPC multicall brute force (currently blocked)

---

## Evidence

- `readyTouse/offensive-assessment.json` — full machine-readable output
- `offensive_assessment.py` — re-runnable offensive script

```bash
cd wordpress-tool
python3 offensive_assessment.py
```
