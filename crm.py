from __future__ import annotations

import requests

from config import BASE_URL, CRM_TOKEN


class CRMClient:
    def __init__(self, token: str | None = None):
        self.token = (token or CRM_TOKEN).strip()
        if not self.token:
            raise ValueError("CRM_TOKEN is missing. Copy .env.example to .env and add the token.")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self.api = f"{BASE_URL}/api/v1"

    def _request(self, method: str, path: str, **kwargs):
        response = self.session.request(method, f"{self.api}{path}", timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()

    def me(self):
        return self._request("GET", "/me")

    def list_accounts(self):
        payload = self._request("GET", "/accounts", params={"page": 1, "page_size": 200})
        if isinstance(payload, list):
            accounts = payload
        else:
            accounts = next(
                (payload[key] for key in ("accounts", "items", "results", "data")
                 if isinstance(payload.get(key), list)),
                None,
            )
        if accounts is None:
            raise ValueError(f"Unexpected account response shape: {type(payload).__name__}")
        # Keep the API's write-field names while adding canonical aliases used
        # by the matching layer.
        return [{
            **account,
            "id": account.get("id") or account.get("account_id"),
            "street": account.get("street") or account.get("billing_street"),
            "city": account.get("city") or account.get("billing_city"),
            "state": account.get("state") or account.get("billing_state"),
            "zip": account.get("zip") or account.get("billing_zip"),
        } for account in accounts]

    def create_account(self, fields: dict):
        return self._request("POST", "/accounts", json=fields)

    def update_account(self, account_id: str, fields: dict):
        return self._request("PATCH", f"/accounts/{account_id}", json=fields)
