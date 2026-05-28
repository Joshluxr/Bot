# Bot

Security automation workspace.

## WordPress WAF bypass tooling

See [wordpress-tool/README.md](wordpress-tool/README.md) for setup of the WordPress assessment tool with **AUTHZ-VULN-01** (CloudFront WAF bypass) support.

```bash
cd wordpress-tool
pip install -r requirements.txt
python3 waf_bypass_probe.py https://your-authorized-target.example
```
