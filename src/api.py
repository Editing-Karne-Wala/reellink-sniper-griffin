from fastapi import FastAPI
import threading
import os

app = FastAPI()

# 1. The "Fake Website" Endpoint
# This tells Render: "Yes, I am alive! Don't kill me."
@app.get("/")
def health_check():
    return {"status": "active", "service": "ReelLink Sniper"}

# 2. The Background Worker
# This runs your REAL bot (main.py) in a separate thread.
def run_bot():
    print("🚀 Starting the Sniper Bot in background...")
    os.system("python main.py")

# 3. Start the bot when the server starts
@app.on_event("startup")
def startup_event():
    # daemon=True means if the server dies, the bot dies (clean exit)
    threading.Thread(target=run_bot, daemon=True).start()
