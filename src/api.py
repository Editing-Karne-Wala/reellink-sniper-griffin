from fastapi import FastAPI
import threading
import asyncio # New import for handling async in thread
import os
import sys

# --- Path Correction ---
# Add the project's root directory to the Python path.
# This allows us to import the 'src.bot' module from the parent directory.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
# =======================

from src.bot import main as bot_main # Import the actual async bot's main function

app = FastAPI()

# Wrapper to create a new event loop for the thread and run the async bot
def run_bot_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("🚀 Starting the Sniper Bot's async polling loop in background thread...")
    loop.run_until_complete(bot_main()) # Now bot_main() is an awaitable

@app.on_event("startup")
def startup_event():
    """
    On server startup, create and start the bot's thread.
    The 'daemon=True' flag ensures the thread will exit when the main server process exits.
    """
    thread = threading.Thread(target=run_bot_in_thread, daemon=True)
    thread.start()

@app.get("/")
def health_check():
    """
    A simple health check endpoint that Render can ping to make sure
    the web service is alive.
    """
    return {"status": "active", "service": "ReelLink Sniper API wrapper"}
