import json

from config import ACCOUNTS_PATH, PROPOSALS_PATH
from crm import CRMClient
from matcher import build_proposals
from scraper import scrape_locations


def main():
    client = CRMClient()
    print("Authenticated:", client.me())
    accounts = client.list_accounts()
    ACCOUNTS_PATH.write_text(json.dumps(accounts, indent=2), encoding="utf-8")
    locations = scrape_locations()
    proposals = build_proposals(locations, accounts)
    PROPOSALS_PATH.write_text(json.dumps(proposals, indent=2), encoding="utf-8")
    print(f"Saved {len(accounts)} accounts, {len(locations)} locations, and {len(proposals)} proposals.")


if __name__ == "__main__":
    main()
