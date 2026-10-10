# Deployment and staff access checkpoint

## Current login design

The moderator sign-in offers **Staff** and **Super Admin**. Super Admin uses `ADMIN_API_TOKEN`, or the local token in `data/.admin-token`. Staff use an ID and password created by the Super Admin in **Staff accounts**. Create `AM001` and `AM002` there with chosen passwords; IDs are case-insensitive and stored lowercase. No staff passwords are assigned automatically.

Super Admin can create accounts, reset passwords, disable/re-enable accounts and inspect each person's activity. Staff operate support cases, referrals and knowledge content; account management and audit access are protected by the backend and hidden from staff.

Passwords are salted scrypt hashes. Staff sessions are stored as hashes and expire after one hour. Logout, password reset and disabling revoke sessions. Live moderator streams re-check authentication every iteration. The audit records sign-ins, failed sign-ins, account changes and operational actions under the staff ID, without storing passwords or tokens.

The earlier `STAFF_ACCOUNT_TOKENS` registry and `data/staff-access/*.token` files are obsolete and no longer accepted. The existing admin token is now the Super Admin credential. MFA and organisation isolation remain unimplemented.

## Verification

The latest update adds a public online staff/Super Admin picker, green presence markers, selected-person case routing, private assigned staff queues, a visible WhatsApp page and the Super Admin Setup & integrations checklist. Availability expires after 45 seconds without dashboard heartbeats. Configure `WHATSAPP_GATEWAY_URL` and `WHATSAPP_SUPPORT_NUMBER` on the hosted API when activating WhatsApp.

The availability checkpoint had 84 passing backend tests, including availability expiry, logout/disabled-account removal, chosen-person privacy and setup access controls. The later multilingual checkpoint is documented in [LANGUAGES-AND-SUPPORT.md](LANGUAGES-AND-SUPPORT.md) and `VERIFICATION.md`. Use `scripts/browser_presence_check.py` for the synthetic local end-to-end presence/routing workflow.

The current browser workflow passed staff and Super Admin presence, chosen-person assignment, human reply delivery, offline removal, WhatsApp pending status, setup visibility and layouts at 390, 768 and 1440 pixels. The synthetic account and its conversation were removed. Screenshots are in `artifacts/whatsapp-pending.png` and `artifacts/setup-integrations.png`. Public web and moderator production builds are running locally on the URLs printed by `scripts/run_local.py` (currently ports 3000 and 3100).

- 79 backend tests passed, including password storage, identity attribution, role restrictions, expiry, logout, reset/disable revocation and login throttling.
- Moderator lint, type checking and production build passed.
- The local stack was restarted with the new login code.
- The local browser workflow passed administrator creation, staff login, backend role restrictions, password reset, disable/revocation, audit filtering, logout and layout checks at 390, 768 and 1440 pixels. The synthetic account was removed after verification.
- Read-only hosted verification from the preceding checkpoint passed both HTTPS pages, support status, directory verification fields, region filtering and unauthenticated route protections. That verification does not establish deployment of this new authentication code.

## Deploy the new login

Authenticated hosting access is unavailable in this workspace. Deploy both the updated orchestrator and moderator frontend together. Retain the existing production `CHAT_ENCRYPTION_KEY`, `ADMIN_API_TOKEN` and persistent `/data` volume. Startup creates the staff account/session tables without replacing conversations. Staff accounts created locally do not automatically reach the production database.

The local Super Admin credential has been aligned with the existing Railway `ADMIN_API_TOKEN` supplied by the owner. Its value exists only in ignored local secret files. The hosted API reads Railway's environment variable; no token is embedded in the source, Dockerfile or frontend. Keep the moderator Vercel project's `ORCHESTRATOR_URL` pointed at that same Railway API. Deploy the backend authentication routes before the updated moderator frontend to avoid a temporary missing-login-route error. Keep the persistent volume so staff accounts survive subsequent pushes.

After deployment:

1. Choose **Super Admin** at the hosted moderator URL and use the existing production admin token.
2. Create `AM001` and `AM002` through **Staff accounts**, assigning passwords privately.
3. Verify staff logins, activity attribution, password reset, disabling and role restrictions on synthetic data.
4. Record deployed SHAs, backend origin, volume mounts and health checks. Inspect production schema and integrity on the host.
5. Verify persistence, backup restoration and hosted streaming/reconnection. These remain outstanding.

## Repeatable local verification

```powershell
.\.venv\Scripts\python.exe scripts/browser_staff_check.py
.\.venv\Scripts\python.exe -m pytest apps/orchestrator/tests services/url-safety/tests apps/whatsapp-gateway/tests -q
```

The browser check creates one randomly named synthetic staff account and removes only that account afterwards. Its audit records remain. `scripts/verify_deployment.py` performs read-only hosted endpoint checks and writes `artifacts/deployment-verification.json`; it does not authenticate or prove deployed SHAs.
