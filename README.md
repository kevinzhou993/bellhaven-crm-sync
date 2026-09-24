# Bellhaven CRM Ownership Reconciliation

A production-style pipeline that scrapes Bellhaven's public community directory, reconciles it against the CRM sandbox, and places every proposed write behind a local human-review queue.

## Quick start (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env`, paste the candidate token after `CRM_TOKEN=`, then run:

```powershell
python pipeline.py
python app.py
```

Open http://127.0.0.1:5000. Review the evidence and proposed field changes, then approve or reject each item. No API write occurs before approval.

## What it builds

- **Scraper:** walks every directory and detail page; extracts name, street, city, state, ZIP, and all care offerings.
- **Matcher:** combines normalized address, ZIP, city/state, and name evidence. It treats a same-name facility in another city as a different location.
- **Ownership workflow:** direct re-parenting is used only when allowed by the SOP. If both historical revenue and outstanding AR are positive, approval creates a new current account and links the preserved old record through `chow_current_account`.
- **Review app:** displays the current record, evidence, confidence, and exact proposed payload. Approve applies the API write; reject records the decision without writing.
- **Daily schedule:** `.github/workflows/daily.yml` shows the production schedule configuration.

## Matching and classification

An exact normalized name plus city/state is a stable identity and may support an address correction. An exact normalized street plus ZIP or city/state supports a rename, but requires separation from the runner-up because historical owner records can share an address. Ambiguous cases become creates for human review rather than destructive updates.

Care offerings are mapped only when the website value has one unambiguous CRM equivalent:

| Website | CRM |
| --- | --- |
| Short-Term Rehabilitation & Nursing | Skilled Nursing |
| Memory Support | Memory Care |
| Assisted Living | Assisted Living |
| Independent Living | Independent Living |

Existing Bellhaven children absent from the website are flagged `Needs Review`; they are never deleted automatically. Duplicate candidates require the same normalized street and ZIP. The matched/canonical record survives, while the losing copy is marked inactive and linked through `duplicate_of_account`.

## Safety and idempotency

- `.env` and generated data are excluded from Git.
- Collection and proposal generation are read-only.
- Every write requires explicit approval.
- Decisions persist in `data/decisions.json`; reruns do not reapply already-decided proposals.
- Proposal IDs include website contents, so a future website change creates a new review item instead of being hidden by an old rejection.
- CRM records are never merged or deleted.

## Tests

```powershell
python -m unittest -v test_matcher.py
```

The tests cover address correction, avoiding false matches across cities, CHOW preservation, and direct re-parenting when AR is zero.

## AI usage

I used AI to accelerate scaffolding, API integration, edge-case analysis, and test generation. I verified the logic against the real website and CRM snapshot, explicitly checked ambiguous same-address records, and retained human approval as the final production boundary.

## What I would build next

I would add saved HTML/API contract fixtures, structured audit logs, retry/backoff, transaction-like recovery for a partial CHOW sequence, authentication for the review UI, and Slack alerts for new ambiguous proposals.

