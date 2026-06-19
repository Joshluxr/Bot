# WordPress Security Assessment Tool

Based on [martinaparched251/Wordpress-BRUTE-FORCE-UPLOAD-SHELL](https://github.com/martinaparched251/Wordpress-BRUTE-FORCE-UPLOAD-SHELL), extended with **CloudFront WAF bypass** support for AUTHZ-VULN-01.

## Quick start

```bash
cd wordpress-tool
pip install -r requirements.txt

# Read-only WAF bypass check (authorized targets only)
python3 waf_bypass_probe.py https://your-lab-site.local

# Full checker (requires site list)
echo 'https://your-lab-site.local' > sites/lab.txt
python3 BRUTER.py sites/lab.txt

# Or batch launcher
chmod +x execut.sh
./execut.sh
```

## WAF bypass

When `/wp-login.php` returns 403 from CloudFront but `/wp%2Dlogin.php` returns the login page, `BRUTER.py` automatically uses the bypass URL for detection, enumeration, and login attempts.

See [docs/AUTHZ-VULN-01.md](docs/AUTHZ-VULN-01.md) for vulnerability details and remediation.

## Required files for shell upload phase

Place these under `Files/` (not included — supply your own lab payloads):

- `plugin.zip`
- `theme.zip`
- `index.php`

Brute-force and username extraction work without them.

## Output

Results are written to `readyTouse/`:

- `successfully_logged_WordPress.txt`
- `Shells.txt`
- `credentials_found.txt`

## Legal

For **authorized security testing only**. Unauthorized access to computer systems is illegal.
