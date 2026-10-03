# AMANI

A Ghana-first rights, safety and wellbeing support application based on the 14-page `Amani_Line_Rights_Support_System_Blueprint.pdf` and `blueprint_text.txt`.

## Run on this Windows computer

The production builds run with Node.js and the Python environment in `.venv`:

```powershell
.\.venv\Scripts\python.exe scripts\run_local.py
```

The launcher prints the actual URLs, selecting a free port when necessary. Its defaults are:

- Website: http://127.0.0.1:3000
- Moderator workspace: http://127.0.0.1:3100
- Internal API: http://127.0.0.1:8100
- URL reputation service: http://127.0.0.1:8200
- WhatsApp webhook: http://127.0.0.1:8300/webhook

These addresses work on this computer. They are not public internet deployments. Services run in the background without opening terminal windows. Logs and process details are in `.runtime/`.

The moderator login accepts the value of `ADMIN_API_TOKEN` when configured. Otherwise the local development token is in **`data/.admin-token`**. Open that file and enter its value in the moderator sign-in form. Do not publish this token or the encryption key.

To stop the managed processes:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\stop-local.ps1
```

## External services

Add real values to the existing `.env` file without removing other settings. `.env.example` lists the supported variables.

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
SAFE_BROWSING_API_KEY=
VIRUSTOTAL_API_KEY=
```

Configure at least one URL reputation provider. Local AI and scanner services reload these integration settings when `.env` changes. Restart services after changing deployment URLs, encryption keys or moderator credentials.

AI replies require the visitor's explicit consent to send recent messages to the configured provider. Without a usable AI key the application provides directory-based replies, labelled as such. The scanner returns **unknown**, never a fabricated safety verdict, when no provider returns a current result. A no-detections result is not a guarantee of safety.

Check external connectivity without printing secrets:

```powershell
.\.venv\Scripts\python.exe scripts\check_integrations.py
```

## Implemented flows

- English/French public interface, French automated support replies and bilingual topic/urgency routing.
- Anonymous capability sessions with encrypted conversation storage, seven-day expiry, deletion, quick exit and explicit AI consent.
- Nine support topics, searchable referral directory, official source links and honest contact-verification status.
- AI integration with conversation context, editorially published knowledge and referral grounding; immediate rule-based crisis routing before model generation.
- Server-sent events for live visitor and moderator updates, with polling/reconnection fallback.
- Human-support queue, priority cases, moderator replies and case status changes.
- Authenticated moderator workspace with HTTP-only cookies, editable referral contacts and a knowledge publication/withdrawal workflow.
- Google Safe Browsing and VirusTotal lookups, consent before URL sharing, bounded timeouts and conservative failure handling. The scanner never visits the submitted address.
- Signed Meta WhatsApp webhook, encrypted persistent inbox, duplicate-event suppression and delivery retries. WhatsApp is disabled until its real credentials and webhook are configured.

## Build and verify

```powershell
npm.cmd --prefix apps/web ci
npm.cmd --prefix apps/moderator-dashboard ci
.\.venv\Scripts\python.exe -m pip install -r apps/orchestrator/requirements.txt -r services/url-safety/requirements.txt -r apps/whatsapp-gateway/requirements.txt
npm.cmd run build
.\.venv\Scripts\python.exe -m pip install -r scripts/test_requirements.txt
.\.venv\Scripts\python.exe -m pytest apps/orchestrator/tests services/url-safety/tests apps/whatsapp-gateway/tests -q
.\.venv\Scripts\python.exe scripts/browser_check.py
```

Browser checks use installed Microsoft Edge via Playwright. Run them after starting the services. Screenshots are written to `artifacts/`. Tests use temporary databases and must never point to production data.

## Deployment status

See [PRODUCTION.md](PRODUCTION.md) for deployment configuration, external onboarding and remaining launch requirements. Passing a local build is not certification that this sensitive support service is ready for public use. Valid provider credentials, staffed human support, content review, HTTPS hosting and independent privacy/security review remain operational requirements.

The original legacy ingestion and retrieval modules remain in `apps/orchestrator/src/main.py`; their write and moderation endpoints now require authentication. The public site uses the new encrypted support workflow in `support.py`, not the old plaintext chat table. Existing legacy data was not deleted or migrated automatically.
