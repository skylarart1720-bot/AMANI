# Verification record

## Online support and integration visibility

The current local update has 84 passing backend tests. New coverage verifies authenticated heartbeats, expiry/offline/logout removal, Super Admin availability, selected-person handoff, private assigned staff queues, denial of another staff member's reply/status change, human message routing and restricted setup visibility. Both frontend lint/type checks and production builds passed.

WhatsApp is visible to visitors even while setup is pending. Super Admin's Setup & integrations view separates configured services requiring live verification, missing setup, unfinished features and operational checks that remain unverified. No provider secret is exposed. Availability expires 45 seconds after the last dashboard heartbeat; a green dot is not a guaranteed response time.

## Current local authentication update

The earlier staff-token setup described below is superseded locally by Super Admin token login and staff ID/password accounts. The Super Admin creates accounts, resets passwords, disables access and reviews staff activity; staff cannot access account administration or the audit API. Salted scrypt passwords, hashed one-hour sessions, server-side logout/revocation, sign-in throttling and live-stream revocation checks are implemented.

79 backend tests passed. Moderator lint, type checking and production build passed. Local browser checks passed staff creation, both login modes, API role restrictions, password reset, disable/revocation, audit filtering, logout and three viewport widths. These changes have not been deployed to the hosted applications; the older hosted verification below does not prove the new authentication flow is live.

Implementation environment: Windows, Python 3.11, Node.js, Next.js 15.5.26.

The original PDF and extracted blueprint were inspected. New public conversation storage is separate from the legacy database; existing user data was preserved.

## Automated checks

- Backend suite: 71 passing tests, including existing ingestion/retrieval tests plus encrypted sessions, access isolation, deletion, human replies, urgent routing, French routing, publication controls, URL provider failure handling, stale/missing report rescanning, pending-analysis deduplication, quota handling, private URL rejection and signed/deduplicated WhatsApp intake.
- New coverage added for this change: distinct staff attribution and revocation, denied and not-found access recording, audit rows carrying time and outcome without message text or tokens, audit immutability, the 90-day retention window, oversized bodies rejected from the declared length and again while receiving, `check-link` accepting only a validated URL, referral `verified`/`stale`/`unverified` derivation, legacy referral records still being served, coarse region filtering in the directory and in chat, and referral edits being audited with their record id.
- Web and moderator applications: `npm run lint`, `npm run typecheck` and production builds all pass. Type checking is now a scripted step rather than only a side effect of `next build`.
- `.github/workflows/ci.yml` runs the backend tests on Python 3.11 and 3.12, lints, type-checks and builds both frontends on Node 20, and boots the orchestrator container against throwaway secrets to confirm it answers and still refuses unauthenticated admin routes. First run on pull request 1 passed all five jobs: backend tests in 22s and 27s, container smoke in 31s, moderator dashboard in 48s and the public site in 50s.
- Live proxy regression checks passed on both localhost and 127.0.0.1; unrelated origins were rejected.
- Visitor and moderator SSE delivery passed without polling; a moderator reply arrived in 1.03 seconds.
- Browser workflow passed at eight widths from 320px to 3440px, including French, human handoff in both directions, deletion, directory search and link checking, with no page errors.
- The running scanner returned a live VirusTotal `no_known_threats` report for the test URL. This is a reputation result, not a guarantee of safety.
- Moderator login regression checks now cover surrounding whitespace/newlines, authenticated cookies, logout and invalid-token rejection on both local hostnames. The original proxy rejected a valid token with surrounding spaces; the revised proxy accepts it.
- VirusTotal accepted a fresh scan submission for `https://www.python.org/` (HTTP 200), and the website returned a current `no_known_threats` result. VirusTotal refused scanning the reserved example.com test address with HTTP 403; provider refusals must remain unverified.
- Frontend dependency installs/audits: zero reported npm vulnerabilities after Next.js/PostCSS updates.
- Python dependency audit: not completed. Installing `pip-audit` failed because `files.pythonhosted.org` was unreachable. This must not be reported as a clean backend dependency audit.

## Production verification, 9 October 2026

A read-only verification pass was run against the merged deployment (`main` at `3160394`) and the local stack. No production data was written: only `GET` requests were issued against the live deployments, and no administrator token was submitted to production.

Deployment was established by fingerprint rather than assumption. `/api/support/directory` returning `verification`, `regions`, `channels` and `trust` shows the orchestrator runs the merged code; `/api/admin/audit` returning `401 "Sign in to continue"` rather than `404` shows the moderator proxy runs the new allowlist.

| Area | Result | Evidence |
| --- | --- | --- |
| Merge state | PASS | PR #1 merged 06:56:46Z, `main` = `3160394` |
| Public site reachable | PASS | `/api/support/status` HTTP 200, backend online |
| Moderator proxy allowlist | PASS | `/api/support/status` on the moderator host returns 404 |
| Staff sign-in | PASS | whitespace-padded token accepted, HttpOnly, SameSite=strict |
| Audit log and staff filter | PASS after fix | see "Proxy query forwarding" below |
| Case reply round trip | PASS | visitor received `role=human`, case moved to `in_progress` |
| Referral create and read | PASS | synthetic record written, then removed |
| Region filtering | PASS after fix | `?region=Ghana` returns 6 of 10 |
| Verification labels | PASS | 8 `unverified`, 2 `verified` in the seeded directory |
| Chat, English and French | PASS | correct topic inference and localised directory replies |
| Urgent routing | PASS | `triage=urgent`, 112 present, AI not called, case created |
| 401 unauthenticated admin | PASS | all four admin routes plus a bad token |
| 413 oversized body | PASS | declared and chunked bodies both rejected |
| 422 validation | PASS | empty, over-length, missing and malformed bodies |
| Local migration state | PASS | all four audit columns present, `integrity_check` ok |
| GitHub Actions on `main` | PASS | five jobs successful |

### Defect found and fixed after the merge

Both Next.js proxies built the upstream URL from the catch-all path alone and never appended the query string, so every query parameter was silently discarded. The public website still appeared correct because the visitor interface filters client-side. It also disabled the `action` and `actor` search on the audit log. `scripts/origin_check.py` now asserts that a filtered directory response is smaller than the unfiltered one, so a proxy that drops parameters fails the check instead of quietly returning everything.

### Not verified, and why

These are open questions, not passes. No Railway or Vercel control-panel access was available, and no administrator credential was used against production.

- **Production migration state.** The `verification` field is derived in Python at read time, so its presence does not prove the audit columns exist in the production database. Run `PRAGMA table_info(audit)` on the backend host to confirm.
- **Per-person attribution.** `STAFF_ACCOUNT_TOKENS` is documented and now wired through Compose, but was not set in any environment. Until it is, every production audit row reads `shared-token` and two people sharing the token cannot be told apart. This is the largest outstanding gap.
- **Persistence, backups and restore.** Not exercised. A consistent SQLite backup, an isolated restore and a proof that ciphertext and case links survive remain required before launch.
- **Alerting and monitoring.** No evidence any alert fires on service failure, queue age or failed WhatsApp jobs.
- **Hosted streaming.** Serverless request-duration limits apply to the proxy routes; the local realtime check does not establish hosted reliability.
- **Railway configuration.** Private networking, volume mounts, deployed SHAs and health checks were not inspected.
- **WhatsApp.** Activation remains unconfirmed and was not tested.

### Security risks still open

Shared staff token and no MFA (both high). Rate limiting is in-memory per process, so it resets on restart and is not shared between replicas. CSRF protection rests entirely on the Origin check, which is skipped for `GET`. `/support/check-link` is unauthenticated and limited per IP only. The Python dependency audit has still never completed.

A referral labelled `verified` means a staff member recorded a check date that has not passed its review date. It is not evidence of a partnership, of current availability or of a confirmed staffed service. `stale` means the check date has passed the review date and the contact needs re-checking; `unverified` means no check was recorded.

The repeatable browser workflow is `scripts/browser_check.py`; it exercises visitor chat, a moderator response, directory filtering, scanner results, deletion and French UI/replies at multiple viewport sizes. `scripts/origin_check.py` checks both local hostnames and rejection of foreign origins. Generated screenshots are under `artifacts/`.

External model, reputation-provider and Meta delivery checks are separate from local application checks. `scripts/check_integrations.py` reports their actual configured/live status without printing secrets. No test result establishes that a human support team is staffed or that referral partners have accepted an integration.

Live credential verification: the supplied VirusTotal credential returned HTTP 200 for a public URL report. The supplied OpenAI credential returned HTTP 429 with code `credit_balance_exhausted`; generative AI cannot be activated successfully until the project has available credit. Credentials were written only to the ignored local `.env`, not documentation.

## Limits

This record is not a penetration test, clinical safety evaluation, legal review, translation certification, load test or production hosting verification. See `PRODUCTION.md` for launch requirements and architecture constraints.
# Multilingual implementation checkpoint

104 backend, WhatsApp gateway and scanner tests passed. Both production frontend builds, lint and type checks passed. The public/moderator language selector, offline catalogues, RTL layouts, consented reply translation, Super Admin catalogue generation, WhatsApp language preferences and ten additional directory entries are implemented. English/French cover 431 extracted keys; additional languages remain partial, and Ga currently has no offline translated wording. See [language coverage and completion instructions](docs/LANGUAGES-AND-SUPPORT.md).

`scripts/browser_language_check.py` passed 24 choices, Twi/Arabic navigation, Arabic layouts at 390/768/1440 px, French directory search, original transcript preservation, consent-gated mocked reply translation and multilingual moderator sign-in. `scripts/browser_presence_check.py` passed chosen-person routing, staff/Admin presence, human replies, offline removal, setup visibility, WhatsApp pending status and responsive layouts. These are local checks, not linguistic or production approval.

The broader `scripts/browser_check.py` also passed eight screen sizes, three feature views, chat, live moderator reply, directory search, URL checking, deletion, French UI/support and absence of browser page errors. Final read-only checks returned HTTP 200 for both frontends, 20 directory entries and 431/431 French catalogue coverage. Configured credentials were not found in tracked or unignored source files.

The configured AI provider returned `credit_balance_exhausted`; real multilingual model output and full catalogue completion remain blocked by provider credit. New referral website evidence is present, but service contact details remain unverified. Meta delivery still needs live configuration and verification.
# Case management and staff activity

106 backend tests passed. Both frontends passed lint and type checks; the moderator production build passed. The synthetic browser workflow passed transfers, encrypted private notes excluded from visitor history, busy availability, resolve/reopen, activity reporting, human replies, deletion and mobile layouts. Repeat with `scripts/browser_case_management.py`; it defaults to local servers. Set `AMANI_TEST_WEB` and `AMANI_TEST_ADMIN` only when intentionally testing a hosted deployment. The script deletes its own synthetic conversation and logs out afterwards.
# Visitor feedback and recovery

109 backend tests passed, including feedback ownership/consent/duplicates, encryption, deletion, Super Admin permissions, service-information settings and encrypted backup/restore. Both frontends passed lint, type checks and production builds. Recovery tests preserve account/settings records and decrypt restored synthetic messages; invalid keys and nonempty restore destinations are rejected, and staff sessions/presence are cleared. See [docs/BACKUP-AND-RECOVERY.md](docs/BACKUP-AND-RECOVERY.md) for host commands and operational setup.
