# AMANI funder preview

First prepare a private demonstration environment with synthetic conversations and a clear list of working features and remaining work. Do not copy the local data folder into the deployment.

## Hosting setup

1. Host the Python orchestrator and URL safety service on infrastructure that supports persistent processes. The current SQLite design requires a persistent disk and one API instance. Keep internal services restricted and expose the required API through HTTPS with appropriate access controls.
2. Create a Vercel Next.js project with Root Directory `apps/web`. Set its server-side `ORCHESTRATOR_URL` to the hosted API URL; localhost will not reach your computer from Vercel.
3. If demonstrating moderator operations, create a separate Vercel project rooted at `apps/moderator-dashboard`, with the same `ORCHESTRATOR_URL` and `COOKIE_SECURE=true`. Restrict access to the moderator workspace.
4. Configure stable `CHAT_ENCRYPTION_KEY`, a new demonstration `ADMIN_API_TOKEN`, production environment settings, backend storage and scanner URL on the backend. Configure provider keys only on services that need them. See `PRODUCTION.md` for details.
5. Protect the preview deployment and confirm that invited reviewers can access it. Check the protection settings for the exact URL you share.
6. Verify chat, human handoff, moderator replies, deletion, French translation and mobile layout on the hosted URLs. Test live updates and reconnection against hosting request-duration limits.

Vercel documentation: [monorepos](https://vercel.com/docs/monorepos), [deployment protection](https://vercel.com/docs/deployment-protection).

## Five-minute demonstration

- Introduce the problem, intended users and what the funding has enabled.
- Send a fictional support question and explain whether the reply is AI-generated or a directory response.
- Request human support and show a moderator replying to that conversation.
- Show referral search, French language and link checking. Explain any unavailable integrations accurately.
- Delete the demonstration conversation.
- Close with remaining launch work, the next milestones and the outcomes you will measure.

## Before sharing

- Use synthetic data and separate demonstration secrets; exclude `.env`, local databases, logs and tokens from uploads.
- Clearly describe the preview as a demonstration. Do not promise staffed emergency response or verified partnerships.
- Confirm provider connectivity if demonstrating AI or reputation scanning. WhatsApp requires separate Meta onboarding and a hosted webhook.
- Prepare a short progress note: implemented features, evidence from testing, current limitations, funding spent and next milestones.
- Before public service launch, complete the content, safeguarding, staffing, privacy, security and backup requirements in `PRODUCTION.md`.
