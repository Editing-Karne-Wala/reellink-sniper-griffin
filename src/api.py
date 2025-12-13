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

# Wrapper to create a new event loop for the thread
def start_bot_in_thread():
    """Runs the bot main function in a dedicated thread."""
    try:
        # 1. Create a fresh loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 2. Call bot_main() DIRECTLY (Not inside run_until_complete)
        # Why? Because bot_main() uses run_polling(), which is a BLOCKING call.
        # It handles the loop internally. We don't need to wrap it.
        bot_main() 
        
    except Exception as e:
        print(f"⚠️ Bot thread crashed: {e}")
    # 3. No loop.close() here! Let it die naturally with the thread.



@app.on_event("startup")

def startup_event():

    """

    On server startup, create and start the bot's thread.

    The 'daemon=True' flag ensures the thread will exit when the main server process exits.

    """

    print("🚀 Starting Bot in background thread...")

    bot_thread = threading.Thread(target=start_bot_in_thread, daemon=True)

    bot_thread.start()



@app.get("/")

def health_check():

    """

    A simple health check endpoint that Render can ping to make sure

    the web service is alive.

    """

    return {"status": "active", "service": "ReelLink Sniper API wrapper"}


