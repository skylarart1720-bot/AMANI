# Languages and support directory

The public app and moderator dashboard share an offline catalogue and a remembered language selector. Arabic and Urdu use right-to-left layouts. Original chat messages, staff IDs, organisation names, URLs and editable values remain unchanged. New AI responses request the selected language; existing assistant/human replies have an explicit **Translate reply** action, gated by AI consent and conversation ownership.

There are 24 registered language choices: English, French, Twi/Akan, Ewe, Ga, Hausa, Yoruba, Igbo, Swahili, Zulu, Amharic, Somali, Arabic, Spanish, Portuguese, German, Italian, Hindi, Simplified Chinese, Russian, Ukrainian, Bengali, Turkish and Urdu.

## Actual coverage

English and French cover all 431 currently extracted interface, setup and error keys. The other catalogues contain draft navigation, consent and referral-response wording: 20–29 keys each. **Ga has no offline translated wording yet** and currently uses English interface/fallback text. Language selection is not a claim that every model is fluent in every language. Twi/Akan, Ewe and Ga need particular native-speaker review. The interface explicitly reports incomplete coverage.

Urgent messages use offline emergency wording in 23 languages (English/French plus the drafted templates); Ga falls back to English. Multilingual phrase matching is a fallback, not clinical assessment or a guarantee that all emergencies will be recognised. Emergency links and manual human-support requests remain available.

The configured provider returned HTTP 429, `credit_balance_exhausted`, during live verification. This prevents testing live multilingual AI quality, completing the remaining catalogues and translating replies with the real provider. Browser tests mock reply translation; they do not certify linguistic accuracy. No formal security, clinical, accessibility or translation approval has been obtained.

## Complete and review catalogues

Only Super Admin can initiate generation in **Setup & integrations → Translation catalogues**. Select a language, then choose **Complete selected language**. Public catalogue reads do not call the model or spend credits. Generation sends only allowlisted public wording; it never reads conversations or credentials. One job runs at a time, saves progress in the persistent data volume, validates numbers/URLs/placeholders and preserves existing translations. English sentence echoes are rejected as incomplete translations. A failed provider keeps existing wording and reports unavailable coverage.

For repository-backed publication after credit restoration:

```powershell
node scripts/extract-locales.mjs
.\.venv\Scripts\python.exe scripts/extract-backend-locales.py
.\.venv\Scripts\python.exe scripts/seed-locales.py
.\.venv\Scripts\python.exe scripts/complete-translations.py ak ee gaa ha es ar pt de hi zh-CN
# Have native speakers review the generated JSON files before publication.
.\.venv\Scripts\python.exe scripts/seed-locales.py
npm.cmd run build
```

Catalogue files live in `apps/orchestrator/src/locales`. `seed-locales.py` copies them and the shared localisation implementation into both independent frontend build contexts. Frontend builds need no external translation service. Keep the backend persistent data volume for administrator-generated catalogues. Rebuild/deploy both frontends after changing bundled wording; deploy the API before frontends that use the new routes.

Reviewed source documents and original transcripts retain their original language. Translating a reply produces a separate display value and does not rewrite the encrypted transcript. Do not represent draft model translations as verified legal/medical guidance.

## Additional support links

Ten entries were added using the organisations' own pages. Website evidence is recorded, but direct service eligibility, responsiveness, hours and supported languages still require contact verification. New entries therefore retain `unverified` contact status and do not imply a partnership.

- [Legal Aid Commission Ghana](https://www.lac.gov.gh/contact-us/): legal aid contact information and regional offices.
- [CHRAJ complaints](https://chraj.gov.gh/normal-complaint-form/) and [discrimination reporting](https://sdrs.chraj.gov.gh/): official reporting routes.
- [Access Now](https://www.accessnow.org/help/): civil-society digital security assistance.
- [Front Line Defenders](https://www.frontlinedefenders.org/en/programme/emergency-contact): assistance options for eligible human rights defenders at risk.
- [UNHCR Help](https://help.unhcr.org/): country-specific refugee/asylum information.
- [Reporters Without Borders assistance](https://rsf.org/en/assistance-journalists-and-media) and [digital security resources](https://helpdesk.rsf.org/).
- [Ghana NCA complaints](https://complaints.nca.org.gh/): telecommunications consumer complaint portal.
- [WHO mental health information](https://www.who.int/health-topics/mental-health): information resource, not a counselling or crisis service.

The directory now has 20 seeded entries. Existing staff-edited records are preserved by insert-if-missing seeding. Search uses translated titles/descriptions when available. Referral category and coverage filters accept multiple entries in each category.

## Verification

The backend/gateway/scanner suite and production frontend builds passed; exact final results are recorded in `VERIFICATION.md`. The multilingual browser workflow passed 24 options, offline navigation, French directory search, Arabic layout at 390/768/1440 px, consent-gated mock translation, transcript preservation and multilingual staff sign-in. Screenshots are under ignored `artifacts/`.

Other setup work remains visible in the administrator's setup screen, including WhatsApp configuration, monitoring, backups, specialist reviews, MFA and additional messaging channels. The WhatsApp chat link needs the actual public business phone number; a Meta phone-number ID is not that number.

When the Meta gateway is connected, send `languages` to see language codes, then `language ak`, `language fr` or another listed code. The preference is saved per sender and included in subsequent chat requests without changing AI consent. Existing sender records migrate to English by default. Gateway command/help notices currently remain in English; the selected language controls new assistant replies. Actual Meta delivery remains unverified while the gateway is unconfigured.
