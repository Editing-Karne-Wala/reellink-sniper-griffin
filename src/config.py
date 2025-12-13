import os
from dotenv import load_dotenv

# Load the vault and override existing environment variables
load_dotenv(override=True)

# --- Extract Secrets ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# --- Sanity Check ---
# Prevents the bot from running if critical secrets are not found in the .env file.
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here" or not GEMINI_API_KEY or not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    raise ValueError(
        "CRITICAL ERROR: One or more secret keys (TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, GOOGLE_API_KEY, GOOGLE_CSE_ID) are missing! "
        "Please check your .env file and ensure all variables are set."
    )

# --- Non-Secret Configuration ---
DATABASE_URL = "sqlite:///reel_link_sniper.db"
