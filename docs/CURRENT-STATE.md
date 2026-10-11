# AMANI current state — 10 October 2026

Feature release: `3489fff5cb58b50d37f2424a425a6b9d55783df7`. Setup documentation release: `f43bf6732d981ad4bd993dbfcd73030b37e89ec0`. Both Vercel applications, Railway API and scanner reported successful deployments; GitHub CI passed. This checkpoint supersedes deployment-pending statements in older checkpoint documents. Older PDFs remain dated snapshots.

Public: https://amani-navy.vercel.app
Moderator: https://amani-hck2.vercel.app
API: https://amani-api-production.up.railway.app

Implemented: public chat and consent controls, referral directory and link scanner, 24 language choices, online staff selection, individual staff credentials and roles, human replies, case assignment/transfers/status/private notes, activity/audit records, visitor feedback and consent-based public review publication, service settings, authenticator MFA and recovery codes, private service monitoring and optional operational webhooks, encrypted backup/restore tools. English/French interface catalogues are complete; other language catalogues remain partial.

Verification: backend tests, frontend lint/type checks/builds, CI and hosted browser checks passed. Hosted workflows verified existing-token Super Admin login, account security and monitoring navigation, chat/handoff/human replies, feedback/reviews, case notices and mobile layouts. Synthetic conversations were deleted. Local MFA checks covered staff enrollment, recovery login and cookie/session rotation. Owner MFA was not activated by deployment.

Operational setup still required: fund the AI API account separately from ChatGPT Plus; create and train actual staff; each operator enrolls MFA; configure the public WhatsApp number and complete Meta/gateway onboarding; configure an HTTPS alert receiver and external uptime monitoring; schedule off-host encrypted backups and test production restoration; validate referrals and complete/native-review translations. Organisation isolation, finer permissions, scaling and independent security/privacy/accessibility/content reviews remain outstanding.

Do not change existing `ADMIN_API_TOKEN`, `CHAT_ENCRYPTION_KEY` or remove persistent data volumes during routine updates. Staff passwords and authenticator/recovery secrets must never be committed. See [security and monitoring](SECURITY-AND-MONITORING.md), [backup and recovery](BACKUP-AND-RECOVERY.md), [public reviews](PUBLIC-REVIEWS.md) and [production setup](../PRODUCTION.md).
