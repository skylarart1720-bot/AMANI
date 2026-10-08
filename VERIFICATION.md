# Verification record

Implementation environment: Windows, Python 3.11, Node.js, Next.js 15.5.26.

The original PDF and extracted blueprint were inspected. New public conversation storage is separate from the legacy database; existing user data was preserved.

## Automated checks

- Backend suite: 71 passing tests, including existing ingestion/retrieval tests plus encrypted sessions, access isolation, deletion, human replies, urgent routing, French routing, publication controls, URL provider failure handling, stale/missing report rescanning, pending-analysis deduplication, quota handling, private URL rejection and signed/deduplicated WhatsApp intake.
- New coverage added for this change: distinct staff attribution and revocation, denied and not-found access recording, audit rows carrying time and outcome without message text or tokens, audit immutability, the 90-day retention window, oversized bodies rejected from the declared length and again while receiving, `check-link` accepting only a validated URL, referral `verified`/`stale`/`unverified` derivation, legacy referral records still being served, coarse region filtering in the directory and in chat, and referral edits being audited with their record id.
- Web and moderator applications: `npm run lint`, `npm run typecheck` and production builds all pass. Type checking is now a scripted step rather than only a side effect of `next build`.
- `.github/workflows/ci.yml` runs the backend tests on Python 3.11 and 3.12, lints, type-checks and builds both frontends on Node 20, and boots the orchestrator container against throwaway secrets to confirm it answers and still refuses unauthenticated admin routes. The workflow is unproven until it has run on GitHub Actions.
- Live proxy regression checks passed on both localhost and 127.0.0.1; unrelated origins were rejected.
- Visitor and moderator SSE delivery passed without polling; a moderator reply arrived in 1.03 seconds.
- Browser workflow passed at eight widths from 320px to 3440px, including French, human handoff in both directions, deletion, directory search and link checking, with no page errors.
- The running scanner returned a live VirusTotal `no_known_threats` report for the test URL. This is a reputation result, not a guarantee of safety.
- Moderator login regression checks now cover surrounding whitespace/newlines, authenticated cookies, logout and invalid-token rejection on both local hostnames. The original proxy rejected a valid token with surrounding spaces; the revised proxy accepts it.
- VirusTotal accepted a fresh scan submission for `https://www.python.org/` (HTTP 200), and the website returned a current `no_known_threats` result. VirusTotal refused scanning the reserved example.com test address with HTTP 403; provider refusals must remain unverified.
- Frontend dependency installs/audits: zero reported npm vulnerabilities after Next.js/PostCSS updates.
- Python dependency audit: not completed. Installing `pip-audit` failed because `files.pythonhosted.org` was unreachable. This must not be reported as a clean backend dependency audit.

## What the audit trail does and does not prove

Attribution depends on how a moderator authenticated. With `STAFF_ACCOUNT_TOKENS` configured, audit rows carry the individual staff id and removing an id revokes that person's access. Without it, the shared `ADMIN_API_TOKEN` is the only credential, so every row reads `shared-token`: the trail proves what was done and that an authorised credential did it, but not which person held the token. Individual accounts, MFA and role separation are still outstanding. Transcript reads, replies and content edits are recorded without message text, tokens or phone numbers; audit rows are removed after 90 days and no route edits or deletes them.

A referral labelled `verified` means a staff member recorded a check date that has not passed its review date. It is not evidence of a partnership, of current availability or of a confirmed staffed service. `stale` means the check date has passed the review date and the contact needs re-checking; `unverified` means no check was recorded.

The repeatable browser workflow is `scripts/browser_check.py`; it exercises visitor chat, a moderator response, directory filtering, scanner results, deletion and French UI/replies at multiple viewport sizes. `scripts/origin_check.py` checks both local hostnames and rejection of foreign origins. Generated screenshots are under `artifacts/`.

External model, reputation-provider and Meta delivery checks are separate from local application checks. `scripts/check_integrations.py` reports their actual configured/live status without printing secrets. No test result establishes that a human support team is staffed or that referral partners have accepted an integration.

Live credential verification: the supplied VirusTotal credential returned HTTP 200 for a public URL report. The supplied OpenAI credential returned HTTP 429 with code `credit_balance_exhausted`; generative AI cannot be activated successfully until the project has available credit. Credentials were written only to the ignored local `.env`, not documentation.

## Limits

This record is not a penetration test, clinical safety evaluation, legal review, translation certification, load test or production hosting verification. See `PRODUCTION.md` for launch requirements and architecture constraints.
