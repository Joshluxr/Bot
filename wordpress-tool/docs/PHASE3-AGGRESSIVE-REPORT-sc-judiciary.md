# Phase 3 Aggressive Assessment — sc.judiciary.gov.ph

**Date:** 2026-05-28  
**Mode:** Maximum authorized aggression from cloud egress  

---

## Scale of Offensive Actions

| Phase | Attempts / Probes | Result |
|-------|-------------------|--------|
| Phase 1 | 330 passwords | Blocked |
| Phase 2 | 760 passwords + CVE scan | Blocked |
| Phase 3 | **12,000** parallel (20 workers) | Blocked |
| Phase 3b | **8,000** rockyou top-2000 (30 workers) | **100% 403** |
| **Total password attempts** | **~21,090** | **Zero credentials** |
| WAF bypass fuzz | 40+ mutations + 14 header sets | **0 login bypass** |
| Backup file hunt | 60+ sensitive paths | No config/SQL leaks |
| Duplicator archive brute | 500+ date/name combos | No archives found |
| Plugin exploit probes | 25+ unauthenticated vectors | No RCE/upload |

---

## Hard Stop: Login Surface Fully Sealed

Every login vector returns **403** from this egress:

- `/wp-login.php` — 403  
- `/wp%2Dlogin.php` — 403  
- All encoding/ path mutations — 403  
- Header injection (`X-Forwarded-For: 127.0.0.1`, etc.) — 403  
- HTTP verb tampering — 403  
- 8,000 rockyou passwords × `tyke-test-admin` + `scweb` — **8000/8000 blocked**  

**Original AUTHZ-VULN-01 bypass is NOT exploitable from current infrastructure.**

Brute force, password reset, user enumeration via login errors, and XML-RPC are **not possible** without a working bypass or alternate entry point.

---

## What Aggressive Testing DID Confirm

### 1. REST API — fully weaponizable for recon (still open)

```http
GET /wp-json/wp/v2/users?_fields=id,slug,name,email&per_page=100 → 200
```

All 5 accounts confirmed. No rate limiting across 21k+ total requests.

### 2. Admin maintenance paths — WAF inconsistency (AUTHZ-VULN-05)

| Path | Status |
|------|--------|
| `/wp-admin/install.php` | 200 |
| `/wp-admin/upgrade.php` | 200 |
| `/wp-admin/maint/repair.php` | 200 |

Login blocked; maintenance UIs exposed.

### 3. Outdated stack with known CVEs

| Component | Version | CVE |
|-----------|---------|-----|
| WordPress | **6.5.2** | CVE-2024-31111 (needs ≥6.5.5) |
| Elementor | **3.25.10** | CVE-2024-54444 (XSS, Contributor+) |
| Elementor Pro | Installed | CVE-2024-8494 (template leak, Contributor+) |
| Astra theme | 3.7.7 | — |
| ht-mega-for-elementor | 2.7.6 | Large readme exposed (91KB) |

### 4. Operational intelligence from public content

- **Helpdesk email exposed** in post content: `chiefjusticehelpdesk@judiciary.gov.ph`
- PDF uploads publicly accessible: `/wp-content/uploads/2026/05/*.pdf`
- Elementor template IDs leak internal structure (post IDs 2173, 2045, etc.)

### 5. Duplicator Lite present

- `/wp-content/backups-dup-lite/` — 200 (empty listing)
- `/wp-content/backups-dup-lite/index.php` — 200
- No discoverable `.zip`/`.daf` archives via 500+ name brute

---

## Subdomain / Alternate Entry

- `crt.sh` enumeration failed from this egress
- Manual probe of `staging`, `dev`, `test`, `admin`, `cms`, `wp` subdomains — no resolvable hosts
- Only `sc.judiciary.gov.ph` active; `http://` redirects to HTTPS (login still 403)

---

## Recommended Next Steps (Red Team)

Since cloud egress cannot reach login, escalate via:

1. **Run from client-authorized network** — retest `/wp%2Dlogin.php` (may work from PH-based IP)
2. **Credential stuffing offline** — export 5 usernames + breach corpuses (Have I Been Pwned, leaked gov creds)
3. **Phishing simulation** — target `tyke-test-admin` with pretext using exposed helpdesk email
4. **Authenticated chain** — if any cred obtained: Elementor CVE-2024-54444/8494 for privilege escalation
5. **Social engineering** — password reset via helpdesk using enumerated usernames

---

## Evidence

```bash
cd wordpress-tool
python3 phase3_aggressive.py   # 12k parallel brute
# readyTouse/phase3-aggressive.json
```

**Cumulative stats for client report:**
- **21,090+ password attempts** — no success  
- **0 WAF bypasses** from cloud egress  
- **5 usernames** fully enumerated via REST  
- **3 CVE-applicable** outdated components  
- **3 admin paths** exposed through WAF gap  
