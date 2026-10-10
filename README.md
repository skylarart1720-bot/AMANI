# AMANI

For GitHub-to-Vercel setup, backend hosting and moderator login configuration, see [VERCEL.md](VERCEL.md).

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

Choose **Super Admin** on the moderator login and enter `ADMIN_API_TOKEN`, or the local development token in **`data/.admin-token`** when no token is configured. Open **Staff accounts** to create each staff ID and password. Staff choose **Staff** and sign in with those credentials. Do not publish the admin token or encryption key.

Staff accounts are stored in the persistent support database with salted scrypt password hashes. IDs are case-insensitive and stored lowercase. Staff sessions expire after one hour; logout, password reset and account disabling revoke sessions. Only the Super Admin can manage staff and inspect the audit trail. Staff can operate the support queue, directory and knowledge workflow; their actions are recorded under their own IDs. MFA is not implemented.

Create `AM001` and `AM002` in **Staff accounts** with passwords you choose. Earlier staff token files and `STAFF_ACCOUNT_TOKENS` are no longer used. See [docs/DEPLOYMENT-CHECKPOINT.md](docs/DEPLOYMENT-CHECKPOINT.md) for deployment instructions.

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

- Language selectors in the public app and moderator dashboard, 24 registered language choices, English/French offline catalogues, draft wording for additional languages, RTL layouts and multilingual AI instructions. See [actual coverage and completion steps](docs/LANGUAGES-AND-SUPPORT.md); additional full catalogues and native-speaker review remain pending.
- Anonymous capability sessions with encrypted conversation storage, seven-day expiry, deletion, quick exit and explicit AI consent.
- Nine support topics, searchable referral directory, official source links and honest contact-verification status.
- Referral records that state their real coverage areas, contact channels, languages and trust tier, with a `verified`, `stale` or `unverified` label derived from the check and review dates. A listing is never presented as a partnership.
- Optional coarse coverage filtering in the directory and in chat. AMANI never asks for or stores a precise location.
- AI integration with conversation context, editorially published knowledge and referral grounding; immediate rule-based crisis routing before model generation.
- Server-sent events for live visitor and moderator updates, with polling/reconnection fallback.
- Human-support queue, priority cases, moderator replies and case status changes.
- Super Admin token login, staff ID/password accounts, account creation, password reset, disabling, session revocation and role enforcement.
- Online staff and Super Admin picker at the top of web support, green presence indicators, selected-person handoff, private assigned staff queues and a general-queue fallback. Dashboard heartbeats refresh every 15 seconds; availability expires after 45 seconds without a heartbeat. Operators can switch Online/Offline.
- Visible WhatsApp channel page and clickable chat action when the public business number is configured; automation status is shown separately. Super Admin's Setup & integrations view lists missing setup, unfinished features and verification work.
- Attributable staff audit trail: actor/action/record/outcome/time for transcript reads, replies and content edits, failed access recorded, 90-day retention, and no route that edits or deletes an entry.
- Authenticated moderator workspace with HTTP-only cookies, editable referral contacts, a knowledge publication/withdrawal workflow and an audit log view.
- Bounded request bodies on every method, checked from the declared length before anything is buffered and capped again while receiving.
- Google Safe Browsing and VirusTotal lookups, consent before URL sharing, bounded timeouts and conservative failure handling. The scanner never visits the submitted address.
- Signed Meta WhatsApp webhook, encrypted persistent inbox, duplicate-event suppression and delivery retries. WhatsApp is disabled until its real credentials and webhook are configured.

## Build and verify

```powershell
npm.cmd --prefix apps/web ci
npm.cmd --prefix apps/moderator-dashboard ci
.\.venv\Scripts\python.exe -m pip install -r apps/orchestrator/requirements.txt -r services/url-safety/requirements.txt -r apps/whatsapp-gateway/requirements.txt
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
.\.venv\Scripts\python.exe -m pip install -r scripts/test_requirements.txt
.\.venv\Scripts\python.exe -m pytest apps/orchestrator/tests services/url-safety/tests apps/whatsapp-gateway/tests -q
.\.venv\Scripts\python.exe scripts\browser_check.py
```

`.github/workflows/ci.yml` runs the same backend tests on Python 3.11 and 3.12, lints, type-checks and builds both frontends on Node 20, builds the three Python container images and boots the orchestrator against throwaway secrets to prove it answers and still refuses unauthenticated admin routes.

Browser checks use installed Microsoft Edge via Playwright. Run them after starting the services. Screenshots are written to `artifacts/`. Tests use temporary databases and must never point to production data.

## Deployment status

See [PRODUCTION.md](PRODUCTION.md) for deployment configuration, external onboarding and remaining launch requirements. Passing a local build is not certification that this sensitive support service is ready for public use. Valid provider credentials, staffed human support, content review, HTTPS hosting and independent privacy/security review remain operational requirements.

The original legacy ingestion and retrieval modules remain in `apps/orchestrator/src/main.py`; their write and moderation endpoints now require authentication. The public site uses the new encrypted support workflow in `support.py`, not the old plaintext chat table. Existing legacy data was not deleted or migrated automatically.
