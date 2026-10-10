# Deploy AMANI with Vercel

The repository contains two independently deployable Next.js apps. Both need the Python API to provide working conversations and moderator operations. Vercel does not run this repository's Docker Compose stack. The current support database uses local SQLite and requires a persistent backend disk; setting DATABASE_URL does not migrate the support workflow to PostgreSQL.

## Current deployments

Recorded so an operator does not have to reconstruct them from project history. Confirm ownership and that each still points at the expected backend before relying on any of them.

| Component | Project | URL |
| --- | --- | --- |
| Public website | `amani` | `https://amani-navy.vercel.app` |
| Moderator dashboard | `amani-hck2` | `https://amani-hck2.vercel.app` |
| Backend API | Railway project | Record the public HTTPS origin here |

The backend origin is deliberately left blank rather than guessed. Copy it from the orchestrator's public domain in the Railway networking settings, without a trailing slash, and paste it into `ORCHESTRATOR_URL` for both Vercel projects. A Railway dashboard link is a control panel, not an API origin. Until it is recorded here, nobody can confirm which backend the frontends are talking to.

As of 9 October 2026 both frontends answer on HTTPS. Configuration flags indicate available settings, not successful provider requests. This update adds separate Staff and Super Admin sign-in as described in section 3; verify both backend and frontend deployments before using it.

## 1. Deploy the backend first

Use a container host or server with persistent disk storage. Existing Dockerfiles are in `apps/orchestrator` and `services/url-safety`; set each service's build context to that directory. Run one orchestrator instance with one worker. The orchestrator listens on port 8000; the scanner listens on port 8001. Both expose `/health`.

Configure the orchestrator's environment:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `PROJECT_ROOT` | `/app` for the supplied Dockerfile |
| `AMANI_DATA_DIR` | `/data`, with a persistent disk mounted there |
| `ADMIN_API_TOKEN` | Preserve the existing Railway token; generate only for a first installation |
| `CHAT_ENCRYPTION_KEY` | Preserve the existing encryption key; generate only for a first installation |
| `URL_SAFETY_URL` | Scanner's private service origin, including port if needed; no trailing slash |
| `OPENAI_API_KEY` | Your funded provider key, if demonstrating AI |
| `OPENAI_MODEL` | Your provider's supported model |
| `OPENAI_BASE_URL` | Your provider's API base URL, if overriding the default |

Configure `APP_ENV=production` and `VIRUSTOTAL_API_KEY` and/or `SAFE_BROWSING_API_KEY` on the scanner. Keep the scanner private. Publish the orchestrator through an HTTPS endpoint reachable by Vercel, with firewall/reverse-proxy controls appropriate to the host. Do not expose databases, server folders or the scanner. Moderator endpoints already require the moderator bearer token.

For an existing Railway deployment, keep its current `ADMIN_API_TOKEN` and `CHAT_ENCRYPTION_KEY` unchanged when deploying this update. Super Admin login validates against that existing Railway token. A Git push does not copy the local `.env` or replace Railway variables. Generate secrets below only for a first installation:

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

After deploying the updated backend and moderator frontend, open the moderator URL, choose **Super Admin**, enter the backend `ADMIN_API_TOKEN` and sign in. Open **Staff accounts** and create each staff ID/password. Staff choose **Staff** on the login and use their own credentials. Cookies are HTTP-only, secure and same-site, with one-hour expiry. Staff logout, password reset and disabling revoke backend sessions; rotating the admin token revokes administrator access after the backend reloads it. Keep the existing production encryption key stable.

Use the existing Railway admin token for this deployment. Keep it out of the public website, Vercel configuration files and GitHub. The dashboard does not need an `ADMIN_API_TOKEN` environment variable; it forwards the operator's submitted token server-side.

For a controlled demo with one operator, use this token plus restricted dashboard access. Use Vercel deployment protection for reviewer access and verify protection on the exact URL you share. This protection is separate from AMANI's moderator login. Do not give funders moderator access unless they need to operate the system; use a guided demonstration otherwise.

Staff accounts, two roles, session revocation and per-person audit records are implemented. MFA and organisation isolation still require work. The earlier `STAFF_ACCOUNT_TOKENS` configuration is no longer used; account records live on the persistent backend disk.

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

## 5. Record what you verified

Deployment steps are not evidence. After any change, note the commit SHA each surface is running and how you confirmed it, so the next operator does not have to guess. Useful checks:

```powershell
# Public site and backend health (read-only, no data written)
curl.exe -s https://amani-navy.vercel.app/api/support/status

# Which backend code is live: pre-merge this has no "verification" field
curl.exe -s "https://amani-navy.vercel.app/api/support/directory?region=Ghana"

# Whether the moderator allowlist includes admin/audit: 401 means new code, 404 means old
curl.exe -s -o NUL -w "%{http_code}" https://amani-hck2.vercel.app/api/admin/audit

# Database migration state, run on the backend host with an authorised session
# PRAGMA table_info(audit);   -- expect actor, resource, outcome, detail
# PRAGMA integrity_check;
```

Only `GET` requests are safe against the live deployment. Do not use them to create sessions, post chats or call `check-link` during routine verification.
