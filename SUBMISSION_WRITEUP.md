# Submission write-up

I treated the website as the current ownership source and matched it to CRM accounts using normalized street address, ZIP, city/state, and name evidence. Exact name plus geography can support an address correction. Address matches can support a rename, but ambiguous same-address histories are sent to review or created as a new current record. Website locations without a safe match become create proposals; unmatched Bellhaven children are flagged Needs Review rather than deleted; duplicates are preserved as inactive records linked to the survivor.

I implemented the CHOW SOP as a separate approval action. When a facility is moving parents and the old account has both lifetime revenue and outstanding AR, approval creates a new Bellhaven account and then sets the old account's `chow_current_account` to the new ID. Otherwise the existing account can be re-parented directly.

AI tools helped with scaffolding, API integration, edge-case brainstorming, and tests. I checked the output against the live website and CRM data, reviewed ambiguous same-address cases, and kept every write behind explicit human approval. With more time I would add API contract fixtures, stronger retry/recovery for a partially completed CHOW action, centralized audit logging, and notifications for new review items.

**Actual focused time:** replace this line with your honest total before submitting.
