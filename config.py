import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
load_dotenv(ROOT / ".env")

BASE_URL = os.getenv("BASE_URL", "https://analyst-assessment-production.up.railway.app").rstrip("/")
CRM_TOKEN = os.getenv("CRM_TOKEN", "").strip()
ACCOUNTS_PATH = DATA_DIR / "accounts.json"
LOCATIONS_PATH = DATA_DIR / "locations.json"
PROPOSALS_PATH = DATA_DIR / "proposals.json"
DECISIONS_PATH = DATA_DIR / "decisions.json"

