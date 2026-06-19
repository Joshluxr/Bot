# Phase 2 Offensive Assessment — sc.judiciary.gov.ph

**Date:** 2026-05-28  
**Tests run:** Elementor CVE checks, 760-password spray, plugin fingerprint, admin path exposure, REST deep enum, BRUTER full run  

---

## New Findings (Phase 2)

### AUTHZ-VULN-05 — WAF Bypass via Admin Maintenance Paths (High)

WordPress login (`/wp-login.php`, `/wp%2Dlogin.php`) is **blocked (403)**, but these admin paths are **publicly reachable (200)**:

| Path | Status | Content |
|------|--------|---------|
| `/wp-admin/install.php` | **200** | WordPress Installation page ("Already Installed") |
| `/wp-admin/upgrade.php` | **200** | WordPress Update page |
| `/wp-admin/maint/repair.php` | **200** | Database Repair instructions |
| `/wp-admin/setup-config.php` | **409** | Config already exists |

**Impact:** WAF policy is inconsistent — blocks login but exposes admin maintenance UIs. `repair.php` documents how to enable `WP_ALLOW_REPAIR` in `wp-config.php`. If an attacker gains config write access, this enables unauthenticated DB repair/recon.

---

### AUTHZ-VULN-06 — Outdated WordPress Core (Medium)

| Component | Detected | Latest secure |
|-----------|----------|---------------|
| WordPress | **6.5.2** | ≥ 6.5.5 (Jun 2024 security release) |

Missing patches for:
- CVE-2024-31111 — Stored XSS via Template Part block (fixed in 6.5.5)
- Additional XSS/HTML API fixes in 6.5.5

Requires **authenticated** contributor+ to exploit, but combined with credential access becomes critical.

---

### AUTHZ-VULN-07 — Outdated Elementor + Elementor Pro (Medium–High)

| Plugin | Version | CVE | Requirement |
|--------|---------|-----|-------------|
| Elementor | **3.25.10** | CVE-2024-54444 (Stored XSS) | Contributor+ |
| Elementor Pro | **Installed** (≤3.25.10) | CVE-2024-8494 (template data leak) | Contributor+ |

Fix: Update to **≥ 3.25.11**.

Additional Elementor ecosystem plugins detected:
- ht-mega-for-elementor 2.7.6
- add-search-to-menu 5.5.14
- interactive-3d-flipbook 1.16.19

---

### AUTHZ-VULN-08 — REST API No Rate Limiting (Medium)

15 consecutive `GET /wp-json/wp/v2/users` requests — **all 200**, no 429.

Combined with open user enumeration, enables unlimited username harvesting for offline attacks.

---

### AUTHZ-VULN-09 — Comments REST Data Exposure (Low–Medium)

`GET /wp-json/wp/v2/comments?per_page=5` returns public comments with:
- Author names (including staff: `pio jerome`)
- External URLs in comment author fields
- Full comment content

---

## Phase 2 Offensive Results

| Test | Volume | Result |
|------|--------|--------|
| Expanded password spray | **760 attempts** (5 users × 76 passwords × 2 paths) | **No credentials** |
| WAF bypass (login paths) | 24 variants | **All 403** |
| BRUTER.py full run | 2061 credential combos + exploits | **No shell/creds** (login blocked) |
| Password reset | 5 users | **403 blocked** |
| User registration | `/wp-login.php?action=register` | **403 blocked** |
| XML-RPC | All methods | **403 blocked** |

---

## Infrastructure Fingerprint

| Component | Value |
|-----------|-------|
| WordPress | 6.5.2 |
| Theme | **Astra 3.7.7** |
| CDN | CloudFront (IAD55-P6) |
| Origin | Apache/2.4.58 (Ubuntu) |

### Plugins fingerprinted

| Plugin | Version |
|--------|---------|
| elementor | 3.25.10 |
| elementor-pro | installed |
| ht-mega-for-elementor | 2.7.6 |
| duplicate-page | 4.5.7 |
| redirection | 5.7.5 |
| add-search-to-menu | 5.5.14 |
| audioigniter | 2.0.2 |
| interactive-3d-flipbook | 1.16.19 |
| wpfront-scroll-top | 3.0.1 |

Backup indicator: `/wp-content/backups-dup-lite/` returns 200 (Duplicator Lite installed).

---

## Attack Path Summary (Updated)

```
[WAF blocks wp-login.php and /wp%2Dlogin.php]
        │
        ├── REST API user enum ──────────► OPEN (5 users, no rate limit)
        ├── Author archives ─────────────► OPEN
        ├── Admin maintenance paths ─────► OPEN (install/upgrade/repair)
        ├── Comments/media REST ─────────► OPEN (PII in comments)
        ├── Plugin version disclosure ───► OPEN (Elementor 3.25.10 CVEs)
        │
        └── Login brute force ───────────► BLOCKED (403)
            Password reset ──────────────► BLOCKED (403)
            XML-RPC ─────────────────────► BLOCKED (403)
```

**Primary remaining unauthenticated vectors:** REST user enum + admin path exposure + outdated plugin CVEs (require creds).

---

## Recommendations (Priority Order)

1. Block `/wp-admin/install.php`, `/upgrade.php`, `/maint/repair.php` at WAF **and** origin
2. Disable unauthenticated REST user listing
3. Update WordPress to ≥ 6.5.5 (or latest 6.x)
4. Update Elementor/Pro to ≥ 3.25.11
5. Add rate limiting on REST API
6. Remove `tyke-test-admin` or enforce 2FA
7. Review Duplicator Lite backup directory permissions

---

## Evidence

```bash
cd wordpress-tool
python3 phase2_offensive.py
# Output: readyTouse/phase2-offensive.json
```
