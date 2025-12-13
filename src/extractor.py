import json
import asyncio
import google.generativeai as genai
import time
import os
import logging
from .config import GEMINI_API_KEY
from google.api_core import exceptions as google_exceptions

# Set up logging for this module
logger = logging.getLogger(__name__)

# --- Rate Limiting ---
# The Gemini API free tier allows 2 requests per minute.
# A semaphore is used to ensure no more than 2 concurrent requests are made.
GEMINI_API_SEMAPHORE = asyncio.Semaphore(2)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("GEMINI_API_KEY not set in environment variables. AI functionalities will be limited.")

def construct_extraction_prompt():
    return """
    You are an expert investigator finding software tools in viral videos.
    
    Analyze the video visuals and audio to identify the PRIMARY tool or resource.
    Determine the CATEGORY based on the user's intent:
    - "github_repo": If the video shows code, a repo, or says "open source".
    - "mobile_app": If it shows an App Store, Play Store, or phone UI.
    - "resource": If it promotes a template, prompt pack, or PDF (e.g. "ChatGPT Prompts").
    - "website": The default for SaaS tools/websites.

    Return a raw JSON object with these fields (no markdown formatting):
    {
      "tool_name": "Name of the tool",
      "category": "github_repo" | "mobile_app" | "resource" | "website",
      "extracted_content": "Full text of prompts/template if category is 'resource' and text is visible, else null"
    }
    
    If no tool is found, return: {"tool_name": "N/A", "category": "N/A", "extracted_content": null}
    """

async def extract_tool_info_with_ai(video_path: str):
    """
    Uploads a video, waits for processing, and uses Gemini to extract structured tool information.
    Uses a semaphore to rate-limit requests to the Gemini API and runs blocking I/O in threads.
    """
    if not GEMINI_API_KEY:
        return {"tool_name": "Error", "category": "Error", "extracted_content": "GEMINI_API_KEY not configured."}

    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    video_file = None
    
    try:
        # --- Sanity Check: Ensure the file is a reasonable size ---
        if os.path.getsize(video_path) < 1000:
            logger.warning(f"File size of {video_path} is too small! It's likely not a valid video.")
            return {"tool_name": "Error", "category": "Error", "extracted_content": "Downloaded video file is invalid (too small)."}

        logger.info(f"Uploading file: {video_path}...")
        video_file = await asyncio.to_thread(
            genai.upload_file, path=video_path, display_name=os.path.basename(video_path)
        )
        logger.info(f"Completed upload. File name: {video_file.name}")

        logger.info("Waiting for file to be processed...")
        while video_file.state.name == "PROCESSING":
            await asyncio.sleep(10)
            video_file = await asyncio.to_thread(genai.get_file, name=video_file.name)

        if video_file.state.name == "FAILED":
            raise ValueError(f"Video processing failed: {video_file.state.name}")

        logger.info(f"File processing complete. State: {video_file.state.name}")

        # --- Acquire Semaphore ---
        logger.info(f"Waiting to acquire Gemini API semaphore for {video_path}...")
        async with GEMINI_API_SEMAPHORE:
            logger.info(f"Semaphore acquired for {video_path}. Making LLM inference request...")
            
            prompt = construct_extraction_prompt()
            
            # The actual rate-limited API call, run in a separate thread
            response = await asyncio.to_thread(
                model.generate_content,
                [video_file, prompt], 
                request_options={"timeout": 600}
            )
        # --- Release Semaphore ---
        
        logger.info(f"Raw Gemini Response Text: {response.text}")

        cleaned_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        
        try:
            tool_data = json.loads(cleaned_text)
            logger.info(f"Successfully parsed JSON: {tool_data}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from response: {cleaned_text} - Error: {e}")
            return {"tool_name": "N/A", "category": "N/A", "extracted_content": f"JSON Parse Error: {e}"}

        if not tool_data.get("tool_name") or tool_data["tool_name"] == "N/A":
            return {"tool_name": "N/A", "category": "N/A", "extracted_content": None}
            
        return tool_data

    except google_exceptions.DeadlineExceeded:
        logger.error(f"Gemini API call timed out for {video_path}.")
        return {"tool_name": "AI_TIMEOUT"}
    except Exception as e:
        logger.exception(f"An error occurred during AI extraction for {video_path}: {e}")
        return {"tool_name": "Error", "category": "Error", "extracted_content": str(e)}
    
    finally:
        if video_file:
            try:
                logger.info(f"Deleting uploaded file: {video_file.name}")
                await asyncio.to_thread(genai.delete_file, name=video_file.name)
            except Exception as e:
                logger.error(f"Error deleting file {video_file.name}: {e}")
