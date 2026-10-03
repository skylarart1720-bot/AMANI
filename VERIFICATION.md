# Verification record

Implementation environment: Windows, Python 3.11, Node.js, Next.js 15.5.26.

The original PDF and extracted blueprint were inspected. New public conversation storage is separate from the legacy database; existing user data was preserved.

## Automated checks

- Backend suite: 48 passing tests, including existing ingestion/retrieval tests plus encrypted sessions, access isolation, deletion, human replies, urgent routing, French routing, publication controls, URL provider failure handling, stale/missing report rescanning, pending-analysis deduplication, quota handling, private URL rejection and signed/deduplicated WhatsApp intake.
- Web and moderator applications: production builds include lint and TypeScript checks.
- Live proxy regression checks passed on both localhost and 127.0.0.1; unrelated origins were rejected.
- Visitor and moderator SSE delivery passed without polling; a moderator reply arrived in 1.00 second.
- Browser workflow passed at eight widths from 320px to 3440px, including French, human handoff in both directions, deletion, directory search and link checking, with no page errors.
- The running scanner returned a live VirusTotal `no_known_threats` report for the test URL. This is a reputation result, not a guarantee of safety.
- Moderator login regression checks now cover surrounding whitespace/newlines, authenticated cookies, logout and invalid-token rejection on both local hostnames. The original proxy rejected a valid token with surrounding spaces; the revised proxy accepts it.
- VirusTotal accepted a fresh scan submission for `https://www.python.org/` (HTTP 200), and the website returned a current `no_known_threats` result. VirusTotal refused scanning the reserved example.com test address with HTTP 403; provider refusals must remain unverified.
- Frontend dependency installs/audits: zero reported npm vulnerabilities after Next.js/PostCSS updates.
- Python dependency audit: not completed. Installing `pip-audit` failed because `files.pythonhosted.org` was unreachable. This must not be reported as a clean backend dependency audit.

The repeatable browser workflow is `scripts/browser_check.py`; it exercises visitor chat, a moderator response, directory filtering, scanner results, deletion and French UI/replies at multiple viewport sizes. `scripts/origin_check.py` checks both local hostnames and rejection of foreign origins. Generated screenshots are under `artifacts/`.

External model, reputation-provider and Meta delivery checks are separate from local application checks. `scripts/check_integrations.py` reports their actual configured/live status without printing secrets. No test result establishes that a human support team is staffed or that referral partners have accepted an integration.

Live credential verification: the supplied VirusTotal credential returned HTTP 200 for a public URL report. The supplied OpenAI credential returned HTTP 429 with code `credit_balance_exhausted`; generative AI cannot be activated successfully until the project has available credit. Credentials were written only to the ignored local `.env`, not documentation.

## Limits

This record is not a penetration test, clinical safety evaluation, legal review, translation certification, load test or production hosting verification. See `PRODUCTION.md` for launch requirements and architecture constraints.
