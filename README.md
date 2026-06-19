# Bot

Security automation workspace.

## WordPress WAF bypass tooling

See [wordpress-tool/README.md](wordpress-tool/README.md) for the WordPress assessment suite with **AUTHZ-VULN-01** (CloudFront WAF bypass) support.

```bash
cd wordpress-tool
pip install -r requirements.txt
python3 waf_bypass_probe.py https://your-authorized-target.example
```

## WordPress bruter (curl-backed)

See [tools/wordpress-bruter/README.md](tools/wordpress-bruter/README.md) for curl-backed bypass testing, lab environment, and engagement runbook.

```bash
cd tools/wordpress-bruter && ./setup.sh && ./run_tests.sh
```

## Decepticon integration

See [decepticon/README.md](decepticon/README.md) for OpenAI-compatible provider setup and [wordpress-tool/decepticon_attack_runner.py](wordpress-tool/decepticon_attack_runner.py) for headless skill playbooks.

## Admin control panel

```bash
cd control-panel && ./run.sh
```

Open http://localhost:8080 — admin-only dashboard for monitoring and job control.
