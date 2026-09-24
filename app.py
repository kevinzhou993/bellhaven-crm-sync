from __future__ import annotations

import json

from flask import Flask, redirect, render_template, request, url_for

from config import DECISIONS_PATH, PROPOSALS_PATH
from crm import CRMClient

app = Flask(__name__)


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


@app.get("/")
def index():
    proposals = load_json(PROPOSALS_PATH, [])
    decisions = load_json(DECISIONS_PATH, {})
    pending = [p for p in proposals if p["id"] not in decisions]
    return render_template("index.html", proposals=proposals, decisions=decisions, pending=pending)


@app.post("/decide/<proposal_id>")
def decide(proposal_id):
    choice = request.form["choice"]
    proposals = load_json(PROPOSALS_PATH, [])
    proposal = next(p for p in proposals if p["id"] == proposal_id)
    decisions = load_json(DECISIONS_PATH, {})
    if proposal_id in decisions:
        return redirect(url_for("index"))
    result = None
    if choice == "approve":
        client = CRMClient()
        if proposal["action"] == "create":
            result = client.create_account(proposal["changes"])
        elif proposal["action"] == "chow":
            created = client.create_account(proposal["changes"])
            new_id = created.get("id") or created.get("account_id")
            if not new_id:
                raise ValueError("Create succeeded but the API did not return a new account id")
            old_id = proposal["account"].get("id") or proposal["account"].get("account_id")
            linked = client.update_account(old_id, {"chow_current_account": new_id})
            result = {"created": created, "old_account_link": linked}
        else:
            account = proposal["account"]
            account_id = account.get("id") or account.get("account_id")
            result = client.update_account(account_id, proposal["changes"])
    decisions[proposal_id] = {"decision": choice, "api_result": result}
    save_json(DECISIONS_PATH, decisions)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
