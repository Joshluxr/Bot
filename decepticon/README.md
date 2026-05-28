# Decepticon + OpenAI-Compatible Providers

Authorized red team engagement tooling based on [PurpleAILAB/Decepticon](https://github.com/PurpleAILAB/Decepticon) skill playbooks.

**Branch:** `devin/1779921489-openai-compatible-providers`

## Full Decepticon (Docker + LLM)

Requires Docker and an API key or OpenAI-compatible gateway:

```bash
curl -fsSL https://decepticon.red/install | bash
cp decepticon/.env.example ~/.decepticon/.env
# Edit CUSTOM_OPENAI_API_BASE, CUSTOM_OPENAI_API_KEY, CUSTOM_OPENAI_MODEL
decepticon onboard
decepticon
```

Set target in Soundwave: `https://lto.gov.ph`

## Headless scan (no Docker — this environment)

Uses Decepticon web-recon/CMS/WAF/exploit skill playbooks + nuclei/httpx/ffuf:

```bash
export PATH="/workspace/decepticon-tools/bin:$PATH"
cd wordpress-tool
python3 decepticon_attack_runner.py https://lto.gov.ph
```

Results: `readyTouse/decepticon/` and `readyTouse/decepticon-attack-report.json`

## OpenAI-compatible provider vars

| Variable | Purpose |
|----------|---------|
| `CUSTOM_OPENAI_API_BASE` | Gateway URL (must end with `/v1`) |
| `CUSTOM_OPENAI_API_KEY` | API key |
| `CUSTOM_OPENAI_MODEL` | Model name (use `custom/<model>` in overrides) |

See [Decepticon models.md](https://github.com/PurpleAILAB/Decepticon/blob/main/docs/models.md).
