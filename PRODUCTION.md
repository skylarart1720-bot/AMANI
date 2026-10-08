# Operating and deploying AMANI

## Current architecture

The two Next.js applications proxy requests to FastAPI through their own origins. Browsers never need an internal API hostname. The origin check compares the incoming browser origin with the actual Host header, allowing both localhost and 127.0.0.1 while rejecting cross-site mutations.

The public support store is SQLite on one persistent node, with Fernet-encrypted message content and hashed random session tokens. This is a single-node deployment design. Do not run multiple WhatsApp workers or scale API replicas across independent local disks. Multi-node scale needs a shared database, broker, distributed rate limiting and stronger operational coordination.

Visitor and moderator conversations use server-sent events. Reverse proxies must permit long-lived responses and disable buffering on `/api/support/events` and `/api/admin/events`. Ordinary API calls retain timeouts and return recoverable errors.

## Secrets and access

- `CHAT_ENCRYPTION_KEY`: stable Fernet key, required in production. Back it up separately from encrypted data. Changing it without migrating data makes existing messages unreadable.
- `ADMIN_API_TOKEN`: high-entropy moderator access token, required in production. Local mode generates one at `data/.admin-token` if none is configured.
- `STAFF_ACCOUNT_TOKENS`, optional: JSON object of staff id to bearer token, for example `{"ada":"<token>"}`. Each moderator then signs in with their own token, audit rows record their staff id, and removing an id revokes that person at the next restart. Leave unset to use the single shared token.
- `OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, `OPENAI_MODEL`: configured model provider. The OpenAI implementation requests `store: false`; this does not negate the provider's other retention policies.
- `SAFE_BROWSING_API_KEY` and/or `VIRUSTOTAL_API_KEY`: reputation lookup credentials. Confirm permitted use and quotas for your deployment.
- Meta values: `META_WHATSAPP_TOKEN`, `META_WHATSAPP_PHONE_NUMBER_ID`, `META_WEBHOOK_VERIFY_TOKEN`, `META_APP_SECRET`, `META_WHATSAPP_API_VERSION`, and `WHATSAPP_PROVIDER=meta`.

Never place provider keys or moderator tokens in `NEXT_PUBLIC_*` variables. Never expose `data/`, `.env`, `.runtime/` or the project folder through a static file server. Production secrets should be supplied by your hosting secret manager.

The supplied moderator token is suitable for a controlled operator installation, not individual staff identity management. Staff actions are now recorded in an audit trail with actor, action, affected record, outcome and time, and that trail is readable in the moderator workspace; it excludes message text, tokens and phone numbers, is removed after 90 days, and no route edits or deletes an entry. Attribution still depends on the credential: with `STAFF_ACCOUNT_TOKENS` configured a row names the staff id, and without it every row reads `shared-token`, so people sharing one token cannot be told apart. Individual accounts, MFA, role separation and automated revocation remain required before onboarding multiple organisations.

## Container deployment

Set production encryption and moderator secrets in the environment, then run:

```sh
docker compose up --build -d
```

Compose keeps API/scanner services private, persists backend data in the `support-data` volume, and binds web ports to loopback. Put an HTTPS reverse proxy in front of the public web app. Restrict the moderator hostname with your organisation's access controls. Configure a separate HTTPS webhook route for Meta. Never publish the raw FastAPI services or use plain HTTP for public conversations.

Docker configuration is provided; Docker deployment must be validated on the target hosting environment. The local verification uses Windows processes, not containers. Configure monitoring, error alerts, backups, restoration tests, disk limits and external uptime checks before launch.

## WhatsApp onboarding and behaviour

Create and verify a WhatsApp Business application/number with Meta. Select a currently supported Graph API version in your application dashboard. Register the HTTPS `/webhook` URL, verify its token and subscribe to messages. Requests are accepted only when the raw-body HMAC signature and configured destination phone ID match.

The gateway acknowledges incoming events after persisting an encrypted inbox entry. A single worker forwards messages to the same support API and retries delivery failures. Delivery is at least once; an ambiguous network failure after Meta accepts a message can still cause duplicate delivery on retry. A failed inbox entry remains available for operational investigation until retention expires; production operations need alerting and a controlled retry procedure.

Commands: `human`, `updates`, `enable ai`, `disable ai`, and `forget`. AI is opt-in. Human replies are retrieved using `updates`; proactive WhatsApp human-message delivery and template messages outside Meta's permitted customer-service window are not implemented. Staff can reply immediately through the web channel.

Meta necessarily receives the phone number. Amani stores delivery payloads encrypted, hashes sender lookup identifiers and purges retained inbox/sender records after seven days. Deletion from Amani cannot delete messages from Meta or the user's device.

## Content and safeguarding

URL reputation checks reuse current reports. Missing or older-than-seven-day VirusTotal reports trigger a fresh scan after URL-sharing consent. The public page polls the analysis for up to approximately two minutes; provider delays and quotas can still leave a URL unverified. VirusTotal submissions/reports may be public, so private tokens and personal information must be removed before submission. Analysis job identifiers are held in bounded, temporary process memory; a restart loses pending job tracking. See [VirusTotal scan API](https://docs.virustotal.com/reference/scan-url).

The blueprint's organisation list is illustrative, not proof of a partnership. Only the Ghana emergency number 112 and CSA reporting number 292 were checked against official pages during this implementation. Other listings explicitly require confirmation. Directory editors must verify contact channels, hours, service coverage and language availability before marking records checked.

Knowledge entries begin pending and are not available to the assistant until published by an authorised reviewer. Withdrawal removes them from future retrieval. Legal, health and crisis content needs qualified review; an administrative publish button does not establish clinical/legal accuracy.

The current urgent-risk classifier is a bilingual rules-based safety net, not a validated clinical classifier. It must undergo specialist evaluation, adversarial testing and appropriate false-negative analysis before public crisis use. The assistant does not establish the user's location and must not promise emergency intervention. 112 is labelled for Ghana.

The French interface and French referral responses are implemented. Source documents and moderator messages stay in their original language. Professional review of safety-critical translations remains necessary. Twi, Ga, Ewe, Hausa, SMS/USSD and automated source-ingestion schedules are not implemented in the new public workflow.

## Human support

Visitors can request a moderator without providing contact details. The request appears live in the moderator queue; replies return to the same visitor session. A functioning queue does not mean trained staff are available. Establish staffing hours, escalation protocols, supervision, response targets and agreements with referral partners before advertising live human help.

## Data lifecycle

New messages are encrypted in `support.db`. Cases reference sessions and are deleted with them. Sessions expire after seven days; an hourly cleanup task and request-time expiry enforce deletion. Audit actions are retained for up to 90 days. Backups, providers and browser/network history have separate retention obligations. Quick exit attempts deletion before navigation but cannot guarantee completion if connectivity fails.

The older `amani_line.db` and any pre-existing backups were preserved. They can contain plaintext legacy conversations. Inspect and migrate or delete that legacy data under an authorised retention policy before deployment; it is not covered by the new encrypted-storage claim. Do not deploy the original local data folder wholesale.

## Documentation sources

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [Google Safe Browsing lookup API](https://developers.google.com/safe-browsing/v4/lookup-api)
- [VirusTotal URL reports](https://docs.virustotal.com/reference/url)
- [Meta webhook signature validation](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/)
- [Ghana National Ambulance Service](https://www.nas.gov.gh/)
- [Ghana Cyber Security Authority reporting](https://csa.gov.gh/report)
