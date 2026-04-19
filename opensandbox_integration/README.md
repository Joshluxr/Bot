# OpenSandbox integration for Terragon OSS (enzo-health fork)

This folder adds a **`opensandbox`** sandbox backend using Alibaba’s [OpenSandbox](https://github.com/alibaba/OpenSandbox) lifecycle server and the npm SDK [`@alibaba-group/opensandbox`](https://www.npmjs.com/package/@alibaba-group/opensandbox).

## 1. On the VPS: install and run OpenSandbox server

Requires Docker. From the [OpenSandbox README](https://github.com/alibaba/OpenSandbox):

```bash
# Pull the image used for coding-agent style workloads (Node, etc.)
docker pull opensandbox/code-interpreter:v1.0.2

uv pip install opensandbox-server
opensandbox-server init-config ~/.sandbox.toml --example docker
opensandbox-server
```

By default the HTTP API listens on **`localhost:8080`**. For a remote app host, bind appropriately (e.g. firewall, reverse proxy, or `0.0.0.0` if your deployment guide allows it).

## 2. Apply changes in your Terragon monorepo

From the root of `terragon-oss` (e.g. `/root/terragon-oss`):

1. **Apply the patch** (adds the provider file, dependency entry, and all wiring):

   ```bash
   git apply /path/to/opensandbox_integration/patch/opensandbox-terragon.patch
   ```

   The file `files/packages-sandbox-src-providers-opensandbox-provider.ts` is a duplicate of the provider for reference if you prefer copying instead of patching.

2. **Install dependencies** at the monorepo root:

   ```bash
   pnpm install
   ```

3. **Environment** — in `apps/www/.env.development.local` (or your deployment env), set at least:

   ```bash
   OPEN_SANDBOX_DOMAIN=127.0.0.1:8080
   OPEN_SANDBOX_PROTOCOL=http
   # OPEN_SANDBOX_API_KEY=...   # if your server requires auth
   OPEN_SANDBOX_IMAGE=opensandbox/code-interpreter:v1.0.2
   OPEN_SANDBOX_TIMEOUT_SECONDS=2700
   # If the app cannot reach sandbox execd directly (NAT), try:
   # OPEN_SANDBOX_USE_SERVER_PROXY=true
   ```

4. **Users** — in **Settings → Sandbox**, choose **OpenSandbox**.

5. **Claude Code in the sandbox** — the code-interpreter image includes Node; ensure the CLI is available the same way as in OpenSandbox’s [claude-code example](https://github.com/alibaba/OpenSandbox/tree/main/examples/claude-code) (e.g. install `@anthropic-ai/claude-code` in setup if needed).

## What was added

- New provider type: `opensandbox` in `@terragon/types` (stored like other providers in `user_settings` / threads).
- `OpenSandboxProvider` implements `ISandboxProvider` via `Sandbox.create` / `Sandbox.connect`, command execution, file read/write, pause (`hibernate`), kill (`shutdown`), renew (`extendLife`).
- Settings UI option **OpenSandbox**; broadcast terminal remains unsupported (same as docker/mock).
- Optional `apps-www` env vars for domain, API key, image, timeout, protocol, and server proxy mode.

## Security

Do not commit real `OPEN_SANDBOX_API_KEY` values. Restrict network access to the OpenSandbox API port to the app host only.
