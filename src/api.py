from fastapi import FastAPI
from concurrent.futures import ThreadPoolExecutor
import asyncio
import os
import sys

# --- Path Correction ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
# =======================

from src.bot import main as bot_main # Import the now-synchronous bot_main

app = FastAPI()

# Define a thread pool executor for running the blocking bot code
executor = ThreadPoolExecutor(max_workers=1)

@app.on_event("startup")
async def startup_event():
    """
    On server startup, schedule the synchronous bot_main() function 
    to run in the background thread provided by the executor.
    """
    print("🚀 Starting Bot as a background Executor task...")
    
    # Get the event loop that Uvicorn is already running
    loop = asyncio.get_running_loop()
    
    # Schedule the blocking function to run in the executor
    loop.run_in_executor(executor, bot_main)

@app.get("/")
def health_check():
    """
    A simple health check endpoint that Render can ping to make sure
    the web service is alive.
    """
    return {"status": "active", "service": "ReelLink Sniper API wrapper"}


