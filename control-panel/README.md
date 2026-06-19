# Red Team Control Panel

Admin-only dashboard to monitor and control all offensive security tooling in this repository.

## Features

- **JWT authentication** with bcrypt password hashing
- **Admin-only** settings editing, job launch/stop, engagement management, audit log
- **Live job monitor** with streaming log tail (4s polling)
- **Tool launcher** for all `wordpress-tool` scripts:
  - WAF bypass probe, engagement recon, offensive phases 1–3
  - Decepticon attack runner, WordPress bruter
- **SQLite persistence** for settings, jobs, engagements, audit trail
- **Dark-themed UI** with responsive layout

## Quick start

```bash
cd control-panel
chmod +x run.sh
./run.sh
```

Open http://localhost:8080

### Default credentials

| Variable | Default |
|----------|---------|
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_PASSWORD` | `admin` |

**Change these before any production use.** Also set `CONTROL_PANEL_SECRET` to a long random string.

```bash
export ADMIN_USERNAME=ops
export ADMIN_PASSWORD='your-strong-password'
export CONTROL_PANEL_SECRET='$(openssl rand -hex 32)'
./run.sh
```

## API

Interactive docs: http://localhost:8080/api/docs

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/auth/login` | Public | Get JWT token |
| `GET /api/stats` | User | Dashboard metrics |
| `GET /api/settings` | User | List settings (secrets masked) |
| `PUT /api/settings/{key}` | **Admin** | Update a setting |
| `POST /api/jobs` | **Admin** | Start a tool job |
| `POST /api/jobs/{id}/stop` | **Admin** | Stop running job |
| `GET /api/audit` | **Admin** | Audit log |

## Directory layout

```
control-panel/
├── backend/          # FastAPI app
├── frontend/dist/    # Static SPA
├── data/             # SQLite DB + job logs (created at runtime)
├── requirements.txt
└── run.sh
```

## Security notes

- Only users with `role=admin` can modify settings or control jobs.
- API keys are masked in the UI after save; leave blank to keep existing value.
- Restrict network access (bind to localhost or place behind VPN/reverse proxy with TLS).
- All admin actions are written to the audit log.
