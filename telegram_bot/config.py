"""Environment-based configuration for the OBD-Insight Telegram bot."""

import os
from pathlib import Path

BOT_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PREMIUM_STARS_PRICE = int(os.environ.get("PREMIUM_STARS_PRICE", "199"))
DB_PATH = os.environ.get("OBD_INSIGHT_DB_PATH", str(BOT_DIR / "data" / "bot_state.db"))
