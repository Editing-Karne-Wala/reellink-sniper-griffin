import asyncio
import os
import subprocess
import logging
import re
import urllib.parse
from urllib.parse import urlparse
import tempfile
import httpx
from .extractor import extract_tool_info_with_ai
from googleapiclient.discovery import build
from .config import GOOGLE_API_KEY, GOOGLE_CSE_ID

# --- Necessary Imports ---
# Ensures all required modules are imported at the top level to prevent NameErrors.
import tempfile
import httpx
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# --- Google Search Function ---
def google_search(query, num_results=5):
    """
    Uses the Official Google Custom Search JSON API.
    """
    logger.info(f"Searching via Google API for: {query}")
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        logger.error("Google API Key or CSE ID are not configured.")
        return []
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        res = service.cse().list(q=query, cx=GOOGLE_CSE_ID, num=num_results).execute()
        
        results = []
        if 'items' in res:
            for item in res['items']:
                results.append({
                    "title": item.get('title'),
                    "link": item.get('link'),
                    "snippet": item.get('snippet')
                })
            logger.info(f"Google API found {len(results)} results.")
        else:
            logger.warning(f"Google API returned no items for '{query}'.")
        return results
    except Exception as e:
        logger.error(f"Google Search API failed: {e}")
        return []

# --- Link Finding Logic ---
def find_direct_link(data):
    tool_name = data.get('tool_name')
    category = data.get('category')
    
    # 1. The "Heist" Bypass (For Resources)
    if category == "resource" and data.get('extracted_content'):
        return "Content Extracted from Video."

    # 2. Context-Aware Search Query
    if category == "github_repo":
        query = f"{tool_name} github repository"
    elif category == "mobile_app":
        query = f"{tool_name} app store"
    else:
        query = f"{tool_name} official website"

    # 3. Execute Search
    results = google_search(query)
    
    # 4. Context-Aware Filtering
    for res in results:
        link = res['link']
        
        # Router Logic
        if category == "github_repo" and "github.com" in link:
            return link
        if category == "mobile_app" and ("play.google.com" in link or "apps.apple.com" in link):
            return link
            
    # Fallback: Return the first result if no specific match found
    return results[0]['link'] if results else None

# --- Video Streaming to Temp File ---
async def stream_video_to_temp_file(url: str) -> str:
    """
    Gets the direct video URL and streams it to a temporary file on disk,
    which acts as a buffer and is deleted immediately after use.
    """
    cookie_file = "instagram_cookies.txt"
    if not os.path.exists(cookie_file):
        logger.error(f"FATAL: Cookie file '{cookie_file}' not found.")
        return None

    yt_dlp_command = ["yt-dlp", "--get-url", url, "--cookies", cookie_file]
    
    logger.info(f"Getting video URL for {url}")
    process = await asyncio.create_subprocess_exec(
        *yt_dlp_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logger.error(f"yt-dlp failed to get video URL for {url}. Error: {stderr.decode()}")
        return None
    
    video_url = stdout.decode().strip().split('\n')[-1] # Get the last URL
    logger.info("Successfully got video URL.")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_f:
            temp_video_path = temp_f.name
        
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", video_url, follow_redirects=True, timeout=60.0) as response:
                response.raise_for_status()
                with open(temp_video_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
        
        logger.info(f"Successfully streamed video to temporary file: {temp_video_path}")
        return temp_video_path
    except httpx.TimeoutException as e:
        logger.error(f"Timeout while streaming video to temp file: {e}")
        if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        return "TIMEOUT"
    except Exception as e:
        logger.error(f"Error streaming video to temp file: {e}")
        if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        return None

# --- Main Reel Processing Orchestrator ---
async def process_reel(reel_url: str) -> dict:
    """
    Orchestrates the entire process for a single reel using the robust stream-to-temp-file method.
    """
    logger.info(f"Processing reel: {reel_url}")
    
    temp_video_path = None
    try:
        temp_video_path = await stream_video_to_temp_file(reel_url)
        
        if temp_video_path == "TIMEOUT":
            return {"tool_name": "Error", "final_message": "Could not download video: The connection timed out. Please check your internet connection and try again."}
        if not temp_video_path:
            return {"tool_name": "Error", "final_message": "Could not download or process video."}
        
        logger.info(f"Video streamed to {temp_video_path}. Proceeding with AI extraction.")
        tool_data = await extract_tool_info_with_ai(temp_video_path)
        
        if tool_data.get("tool_name") == "AI_TIMEOUT":
            return {"tool_name": "Error", "final_message": "The AI analysis timed out, which can happen with very long videos or slow connections. Please try again."}
        
        if not tool_data or tool_data.get("tool_name") == "N/A":
            logger.warning(f"Tool not identified for reel {reel_url}.")
            return {"tool_name": "N/A", "final_message": "Tool not identified."}

        if tool_data.get("tool_name") == "Error":
            error_message = tool_data.get('extracted_content', 'Unknown AI extraction error.')
            logger.error(f"AI extraction failed for reel {reel_url}. Reason: {error_message}")
            return {"tool_name": "Error", "final_message": error_message}
        
        logger.info(f"AI extracted data: {tool_data}. Now finding direct link.")
        final_link = find_direct_link(tool_data)

        # Handle the "Content Extracted" case for resources
        if final_link == "Content Extracted from Video.":
             final_message = f"Tool detected: {tool_data.get('tool_name')}\n\n⚠️ **Direct Link Not Found** (It might be a resource).\n✅ **Smart Capture Successful:**\nI read the content directly from the video for you:\n\n`{tool_data.get('extracted_content')}`\n\n_(Note: This is an AI transcription.)_"
        elif not final_link:
            final_link = f"https://www.google.com/search?q={urllib.parse.quote_plus(tool_data.get('tool_name'))}"
            final_message = f"Tool detected: {tool_data.get('tool_name')}\nDirect link ↓\n{final_link}\n\n(no like/follow/comment needed)"
        else:
            final_message = f"Tool detected: {tool_data.get('tool_name')}\nDirect link ↓\n{final_link}\n\n(no like/follow/comment needed)"
        
        return {
            "tool_name": tool_data.get("tool_name"),
            "final_message": final_message,
            "category": tool_data.get("category")
        }
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            logger.info(f"Cleaning up temporary file: {temp_video_path}")
            try:
                os.remove(temp_video_path)
            except OSError as e:
                logger.error(f"Error removing temp file {temp_video_path}: {e}")