# Deploy AMANI with Vercel

The repository contains two independently deployable Next.js apps. Both need the Python API to provide working conversations and moderator operations. Vercel does not run this repository's Docker Compose stack. The current support database uses local SQLite and requires a persistent backend disk; setting DATABASE_URL does not migrate the support workflow to PostgreSQL.

## 1. Deploy the backend first

Use a container host or server with persistent disk storage. Existing Dockerfiles are in `apps/orchestrator` and `services/url-safety`; set each service's build context to that directory. Run one orchestrator instance with one worker. The orchestrator listens on port 8000; the scanner listens on port 8001. Both expose `/health`.

Configure the orchestrator's environment:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `PROJECT_ROOT` | `/app` for the supplied Dockerfile |
| `AMANI_DATA_DIR` | `/data`, with a persistent disk mounted there |
| `ADMIN_API_TOKEN` | A new random token, generated below |
| `CHAT_ENCRYPTION_KEY` | A new Fernet key, generated below; keep it stable |
| `URL_SAFETY_URL` | Scanner's private service origin, including port if needed; no trailing slash |
| `OPENAI_API_KEY` | Your funded provider key, if demonstrating AI |
| `OPENAI_MODEL` | Your provider's supported model |
| `OPENAI_BASE_URL` | Your provider's API base URL, if overriding the default |

Configure `APP_ENV=production` and `VIRUSTOTAL_API_KEY` and/or `SAFE_BROWSING_API_KEY` on the scanner. Keep the scanner private. Publish the orchestrator through an HTTPS endpoint reachable by Vercel, with firewall/reverse-proxy controls appropriate to the host. Do not expose databases, server folders or the scanner. Moderator endpoints already require the moderator bearer token.

Generate new backend secrets locally, separately, using the installed Python environment:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store the first output as `ADMIN_API_TOKEN` and the second as `CHAT_ENCRYPTION_KEY` in the backend host's secret settings. Do not commit either value. Back up the encryption key separately from the database. Use fresh demonstration data rather than copying `data/` from this computer. The full container setup and operational requirements are in [PRODUCTION.md](PRODUCTION.md).

## 2. Import the GitHub repository twice into Vercel

Select `skylarart1720-bot/AMANI` for each project:

| Setting | Public website | Moderator dashboard |
| --- | --- | --- |
| Suggested project name | `amani-web` | `amani-admin` |
| Root Directory | `apps/web` | `apps/moderator-dashboard` |
| Framework | Next.js | Next.js |
| Install command | `npm ci` | `npm ci` |
| Build command | `npm run build` | `npm run build` |
| Output directory | Framework default | Framework default |
| `ORCHESTRATOR_URL` | Hosted HTTPS API origin | Same hosted HTTPS API origin |
| `COOKIE_SECURE` | Not needed | `true` |

Each app includes `vercel.json` and `.env.example`. Select the Root Directory in Vercel; it is not the repository root. Do not use the root `npm run build` command as the build override for these projects.

Set environment variables for the deployment environment you use (Production and/or Preview), then deploy or redeploy. Replace `https://api.example.com` with your real API origin, without a trailing slash. `localhost` and `127.0.0.1` do not connect Vercel to your laptop. Do not prefix secrets or the API setting with `NEXT_PUBLIC_`.

## 3. Sign in to the moderator dashboard

Open the moderator project's URL. Paste the new backend `ADMIN_API_TOKEN` into **Access token** and click **Sign in**. No username is currently required. The dashboard validates the token against the backend and sets a one-hour HTTP-only, secure, same-site cookie. Logout removes that browser's cookie. Rotating the backend token revokes existing access after the backend reloads the new value.

Do not reuse the local development token that was shared in the conversation. Do not add the admin token to the public website, Vercel configuration files or GitHub. The dashboard does not need an `ADMIN_API_TOKEN` environment variable; it forwards the operator's submitted token server-side.

For a controlled demo with one operator, use this token plus restricted dashboard access. Use Vercel deployment protection for reviewer access and verify protection on the exact URL you share. This protection is separate from AMANI's moderator login. Do not give funders moderator access unless they need to operate the system; use a guided demonstration otherwise.

Before multiple staff use this with real support data, replace the shared token with individual accounts, MFA, roles, revocation and per-person audit records. Those identity features are not implemented by the current token login.

## 4. Verify the hosted demo

- Check the public site reports a connected support service.
- Send a fictional question; verify AI or clearly labelled directory fallback.
- Request human support, sign in on the separate moderator URL and reply.
- Verify live updates reconnect and polling recovers when serverless streaming requests end. Vercel request-duration limits apply to the proxy routes; local browser tests do not establish hosted streaming reliability.
- Verify incorrect tokens are rejected, logout works and protected links require access.
- Check referral search, link scanning, French, mobile layout and conversation deletion.
- Confirm no real conversations or local secrets were uploaded.

AI credit must be available for live AI replies. WhatsApp is optional and requires a separately hosted gateway and Meta onboarding; Vercel deployment does not activate it.

See [FUNDER_PREVIEW.md](FUNDER_PREVIEW.md) for a demonstration script. A successful frontend deployment alone does not establish a working backend or public-launch readiness.

Official references: [Vercel monorepos](https://vercel.com/docs/monorepos), [environment variables](https://vercel.com/docs/environment-variables), [SQLite limitations](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel), [function limits](https://vercel.com/docs/functions/limitations), [deployment protection](https://vercel.com/docs/deployment-protection).
