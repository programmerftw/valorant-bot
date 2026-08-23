import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

GUILDS_FILE = DATA_DIR / "guilds.json"

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
VLR_API_BASE = os.getenv("VLR_API_BASE", "http://127.0.0.1:3001").rstrip("/")

NEWS_POLL_INTERVAL = int(os.getenv("NEWS_POLL_INTERVAL", "3600"))
LIVE_POLL_INTERVAL = int(os.getenv("LIVE_POLL_INTERVAL", "80"))
UPCOMING_POLL_INTERVAL = int(os.getenv("UPCOMING_POLL_INTERVAL", "7200"))
RESULTS_POLL_INTERVAL = int(os.getenv("RESULTS_POLL_INTERVAL", "21600"))
