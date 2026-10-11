# Public reviews

Visitors can open **Reviews** from the public website navigation. It shows an average of published ratings, the published count, and up to 50 recent anonymous reviews. The page explains that these are selected reviews rather than all private feedback. No case IDs, visitor session identifiers or staff IDs are returned by the public API.

After a support case is resolved, a visitor can submit optional feedback in their chat. Sharing feedback with Super Admin and allowing public publication are separate choices. Public sharing is unchecked by default. Existing private feedback remains private and cannot be published.

Super Admin opens **Visitor feedback**, finds an entry labelled **Visitor consented to public sharing**, reviews it for identifying/sensitive details and selects **Publish review**. The public text must be the original comment or a continuous excerpt. Leaving the excerpt empty publishes the unchanged rating alone. The original private comment is preserved and encrypted. Staff accounts cannot publish reviews. **Unpublish review** removes the review from the public listing; publishing/unpublishing is audited without recording comment text in audit records.

Do not select reviews solely because they are positive or use an excerpt that changes the meaning. The interface keeps the original rating unchanged, including critical ratings. Review text is rendered as plain text and is not sent to AI for translation. The new interface wording has French translations; original review text retains its language.

Deleting or expiring the linked visitor conversation removes the review and private feedback from the active service. Existing screenshots, browser/provider copies and unmanaged backups are outside this deletion mechanism. No sample reviews are seeded into production.

Verification: backend tests cover consent, Super Admin permissions, unchanged ratings, allowed excerpts, private/public separation, unpublishing and deletion. The local browser check exercises the actual publish/unpublish controls and public reading experience. Hosted browser checks verify the Reviews page and consent/publish controls without publishing synthetic reviews publicly.
