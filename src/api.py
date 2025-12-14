import os
import sys # Add this line
import json
import asyncio
from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor

# === START COOKIE SETUP ===
# This code runs once when the Uvicorn server starts.
if os.getenv("IG_COOKIES_JSON"):
    print("🍪 Found cookie data in Env Var!")
    raw_json = os.getenv("IG_COOKIES_JSON")
    
    # 1. Save JSON File (for Instagrapi, though not currently used for login resumption)
    with open("session.json", "w") as f:
        f.write(raw_json)
        
    # 2. Convert to Netscape File (for yt-dlp)
    try:
        data = json.loads(raw_json)
        cookies = data.get("cookies", {})
        with open("instagram_cookies.txt", "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for name, value in cookies.items():
                f.write(f".instagram.com\tTRUE\t/\tTRUE\t2147483647\t{name}\t{value}\n")
        print("✅ Created instagram_cookies.txt (Netscape format) for yt-dlp.")
    except Exception as e:
        print(f"⚠️ Cookie conversion failed: {e}")
# === END COOKIE SETUP ===


# --- Path Correction ---
# This allows us to import from the 'src' directory.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
# =======================

from src.bot import main as bot_main

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=1)

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Bot as a background Executor task...")
    loop = asyncio.get_running_loop()
    loop.run_in_executor(executor, bot_main)

@app.get("/")
def health_check():
    return {"status": "active", "service": "ReelLink Sniper API wrapper"}