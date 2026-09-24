from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher


def norm(value) -> str:
    value = str(value or "").lower().replace("&", " and ")
    replacements = {
        r"\bnorthwest\b": "nw", r"\bnortheast\b": "ne",
        r"\bsouthwest\b": "sw", r"\bsoutheast\b": "se",
        r"\bnorth\b": "n", r"\bsouth\b": "s", r"\beast\b": "e", r"\bwest\b": "w",
        r"\bstreet\b": "st", r"\broad\b": "rd", r"\bavenue\b": "ave",
        r"\blane\b": "ln", r"\bdrive\b": "dr", r"\bboulevard\b": "blvd",
        r"\bcentre\b": "center", r"\brehabilitation\b": "rehab",
    }
    for pattern, replacement in replacements.items():
        value = re.sub(pattern, replacement, value)
    return re.sub(r"[^a-z0-9]", "", value)


def account_id(account: dict | None):
    return (account or {}).get("id") or (account or {}).get("account_id")


def proposal_id(action: str, location: dict | None, account: dict | None) -> str:
    source = (location or {}).get("source_url") or (location or {}).get("url") or ""
    location_fingerprint = json.dumps(location or {}, sort_keys=True, separators=(",", ":"))
    raw = "|".join([action, source, str(account_id(account)), location_fingerprint])
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def name_similarity(a, b) -> int:
    return round(100 * SequenceMatcher(None, norm(a), norm(b)).ratio())


def mapped_care_type(location: dict) -> str | None:
    mapped = []
    for item in location.get("care_offerings") or []:
        low = item.lower()
        if "rehabilitation" in low or "nursing" in low:
            mapped.append("Skilled Nursing")
        elif "memory" in low:
            mapped.append("Memory Care")
        elif "assisted" in low:
            mapped.append("Assisted Living")
        elif "independent" in low:
            mapped.append("Independent Living")
    return mapped[0] if len(set(mapped)) == 1 else None


def score(location: dict, account: dict) -> tuple[int, list[str]]:
    evidence, points = [], 0
    street_match = bool(norm(location.get("street"))) and norm(location.get("street")) == norm(account.get("street"))
    zip_match = bool(norm(location.get("zip"))) and norm(location.get("zip")) == norm(account.get("zip"))
    geo_match = norm(location.get("city")) == norm(account.get("city")) and norm(location.get("state")) == norm(account.get("state"))
    exact_name = norm(location.get("name")) == norm(account.get("name"))
    similarity = name_similarity(location.get("name"), account.get("name"))
    if street_match:
        points += 60; evidence.append("exact normalized street")
    if zip_match:
        points += 15; evidence.append("exact ZIP")
    if geo_match:
        points += 15; evidence.append("exact city/state")
    if exact_name:
        points += 25; evidence.append("exact normalized name")
    else:
        points += round(similarity * 0.15); evidence.append(f"name similarity {similarity}%")
    return min(points, 100), evidence


def is_confident(location: dict, account: dict, best_score: int, runner_up: int) -> bool:
    street_match = bool(norm(location.get("street"))) and norm(location.get("street")) == norm(account.get("street"))
    zip_match = bool(norm(location.get("zip"))) and norm(location.get("zip")) == norm(account.get("zip"))
    geo_match = norm(location.get("city")) == norm(account.get("city")) and norm(location.get("state")) == norm(account.get("state"))
    exact_name = norm(location.get("name")) == norm(account.get("name"))
    strong_identity = street_match and (zip_match or geo_match)
    stable_identity = exact_name and geo_match
    # Exact name + geography is independently strong even when historical owner
    # records share the same address. Renames rely on address plus a clear margin.
    return stable_identity or (strong_identity and best_score - runner_up >= 8)


def desired_fields(location: dict, parent_id: str) -> dict:
    fields = {
        "name": location["name"], "billing_street": location["street"],
        "billing_city": location["city"], "billing_state": location["state"],
        "billing_zip": location["zip"], "parent_id": parent_id, "status": "Active",
    }
    care_type = mapped_care_type(location)
    if care_type:
        fields["care_type"] = care_type
    return fields


def changed_fields(account: dict, desired: dict) -> dict:
    changes = {}
    for field, value in desired.items():
        current = account.get(field)
        canonical = {
            "billing_street": "street", "billing_city": "city",
            "billing_state": "state", "billing_zip": "zip",
        }.get(field, field)
        current = account.get(field) if field in account else account.get(canonical)
        if canonical in {"name", "street", "city", "state", "zip"}:
            different = norm(current) != norm(value)
        else:
            different = str(current or "") != str(value or "")
        if different:
            changes[field] = value
    return changes


def build_proposals(locations: list[dict], accounts: list[dict]) -> list[dict]:
    bellhaven_parent = next((a for a in accounts if "bellhaven senior living" in str(a.get("name", "")).lower() and "parent" in str(a.get("name", "")).lower()), None)
    if not bellhaven_parent:
        raise ValueError("Bellhaven parent account not found")
    parent_id = account_id(bellhaven_parent)
    candidates = [a for a in accounts if account_id(a) != parent_id and "parent account" not in str(a.get("name", "")).lower()]

    proposals, matched_ids = [], set()
    for location in locations:
        ranked = sorted(((score(location, a)[0], score(location, a)[1], a) for a in candidates), key=lambda x: x[0], reverse=True)
        best_score, evidence, best = ranked[0]
        runner_up = ranked[1][0] if len(ranked) > 1 else 0
        if is_confident(location, best, best_score, runner_up):
            matched_ids.add(account_id(best))
            desired = desired_fields(location, parent_id)
            changes = changed_fields(best, desired)
            if not changes:
                continue
            moving_parent = str(best.get("parent_id") or "") != str(parent_id)
            chow_required = moving_parent and float(best.get("lifetime_revenue") or 0) > 0 and float(best.get("outstanding_ar") or 0) > 0
            action = "chow" if chow_required else "update"
            proposals.append({
                "id": proposal_id(action, location, best), "action": action,
                "confidence": best_score, "location": location, "account": best,
                "changes": desired if chow_required else changes,
                "old_account_changes": {"chow_current_account": "$NEW_ACCOUNT_ID"} if chow_required else {},
                "evidence": evidence + (["revenue history and outstanding AR are both positive"] if chow_required else []),
                "reason": "CHOW SOP: create the current account under Bellhaven and preserve/link the old account." if chow_required else "Confident match; synchronize website truth and ownership.",
            })
        else:
            proposals.append({
                "id": proposal_id("create", location, None), "action": "create",
                "confidence": best_score, "location": location, "account": best,
                "changes": desired_fields(location, parent_id),
                "evidence": evidence + [f"best candidate score {best_score}; no strong identity match"],
                "reason": "No safe CRM match; create only after human review.",
            })

    children = [a for a in accounts if str(a.get("parent_id") or "") == str(parent_id)]
    by_address = defaultdict(list)
    for account in children:
        key = (norm(account.get("street")), norm(account.get("zip")))
        if all(key):
            by_address[key].append(account)
    duplicate_ids = set()
    for duplicates in by_address.values():
        active = [a for a in duplicates if a.get("status") != "Inactive"]
        if len(active) < 2:
            continue
        website_streets = {norm(l.get("street")) for l in locations}
        survivor = sorted(active, key=lambda a: (account_id(a) in matched_ids, float(a.get("lifetime_revenue") or 0), norm(a.get("street")) in website_streets), reverse=True)[0]
        for losing in active:
            if account_id(losing) == account_id(survivor):
                continue
            duplicate_ids.add(account_id(losing))
            proposals.append({
                "id": proposal_id("duplicate", None, losing), "action": "duplicate", "confidence": 100,
                "location": None, "account": losing,
                "changes": {"duplicate_of_account": account_id(survivor), "status": "Inactive"},
                "evidence": ["same normalized street and ZIP", f"survivor: {survivor.get('name')} ({account_id(survivor)})"],
                "reason": "Duplicate Bellhaven child; keep one canonical record and preserve the losing record as inactive.",
            })

    for account in children:
        aid = account_id(account)
        if aid not in matched_ids and aid not in duplicate_ids and account.get("status") not in {"Inactive", "Needs Review"}:
            proposals.append({
                "id": proposal_id("stale", None, account), "action": "stale", "confidence": 75,
                "location": None, "account": account,
                "changes": {"status": "Needs Review", "note": "Not found on current Bellhaven website; verify closure or divestiture."},
                "evidence": ["currently under Bellhaven parent", "no current website location matched"],
                "reason": "Flag a possible closure/divestiture for review; never delete automatically.",
            })
    return proposals

