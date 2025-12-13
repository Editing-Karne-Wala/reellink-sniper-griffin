import logging
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    TypeHandler
)
from telegram.ext import AIORateLimiter
import asyncio
import re
import time # Import time for potential sleep if needed in post_init, though async delays are preferred
from .config import TELEGRAM_BOT_TOKEN
from .processor import process_reel
from .database import get_or_create_user

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler() # Also log to console for visibility if not run in background
    ]
)
logger = logging.getLogger(__name__)

# --- Per-User Rate Limiting ---
# Allows 5 requests per user every 60 seconds.
user_rate_limiter = AIORateLimiter(overall_max_rate=5, overall_time_period=60)

async def rate_limit_exceeded(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notifies user when they have exceeded the request rate limit."""
    user = update.effective_user
    logger.warning(f"Rate limit exceeded for user {user.id}. Message: {update.message.text}")
    await update.message.reply_text(
        "You are sending requests too quickly. Please wait a moment before trying again. ⏳",
        reply_to_message_id=update.message.message_id
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /start is issued."""
    user = update.effective_user
    get_or_create_user(user.id, user.username)
    logger.info(f"User {user.id} started the bot.")
    await update.message.reply_html(
        f"Hi {user.mention_html()}! Send me Instagram/TikTok/YouTube Reel links and I'll find the hidden tools for you.",
        reply_to_message_id=update.message.message_id
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    user = update.effective_user
    logger.info(f"User {user.id} requested help.")
    await update.message.reply_text(
        "Simply share a reel link with me, or paste up to 10 links at once!",
        reply_to_message_id=update.message.message_id
    )

async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message detailing the bot's privacy policy."""
    user = update.effective_user
    logger.info(f"User {user.id} requested privacy policy.")
    privacy_text = (
        "**Privacy Policy**\n\n"
        "I am designed with your privacy in mind. Here’s what you need to know:\n\n"
        "**What I Store:**\n"
        "- `User ID`: Your numeric Telegram ID is stored to recognize you as a user.\n"
        "- `Username`: Your Telegram username is stored for the same reason.\n\n"
        "**What I DO NOT Store:**\n"
        "- I **do not** store the links to the reels you send me.\n"
        "- I **do not** store the videos downloaded for analysis. They are deleted from memory immediately after being processed.\n"
        "- I **do not** store any information extracted from the videos.\n\n"
        "Your data is only used to process your requests and is never shared. My purpose is to find links, not to collect your data."
    )
    await update.message.reply_text(
        privacy_text,
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id,
        disable_web_page_preview=True
    )

async def handle_reel_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes messages containing reel links."""
    text = update.message.text
    user = update.effective_user
    
    # Register user or update last activity
    get_or_create_user(user.id, user.username)
    logger.info(f"User {user.id} sent message: {text}")

    # Regex to find common video reel links
    # This regex is basic and might need refinement for all cases.
    reel_links = re.findall(r'(https?://(?:www\.)?(?:instagram\.com|tiktok\.com|youtube\.com|youtu\.be)/(?:reel|shorts|video)/[a-zA-Z0-9_-]+(?:/?(?:c|\?|&)[^ \n]*)?)', text)
    
    if not reel_links:
        logger.info(f"No valid reel links found in message from user {user.id}.")
        await update.message.reply_text(
            "That doesn\'t look like a valid reel link. Please send a direct link to an Instagram Reel, TikTok, or YouTube Short.",
            reply_to_message_id=update.message.message_id
        )
        return

    # Limit processing to a reasonable number if many links are sent
    if len(reel_links) > 10:
        logger.warning(f"User {user.id} sent {len(reel_links)} links, processing only first 10.")
        await update.message.reply_text(
            f"You sent {len(reel_links)} links. I will process the first 10 for now. Please send fewer links next time for faster processing.",
            reply_to_message_id=update.message.message_id
        )
        reel_links = reel_links[:10]

    # Process each reel link
    for i, link in enumerate(reel_links):
        logger.info(f"Processing reel {i+1}/{len(reel_links)} for user {user.id}: {link}")
        # Instantly reply "Scanning..." and quote the exact reel message
        status_message = await update.message.reply_text(
            f"Scanning Reel {i+1}/{len(reel_links)}: ⏳\n`{link}`",
            reply_to_message_id=update.message.message_id,
            parse_mode="Markdown"
        )
        
        # Dispatch the processing to a background task
        # This allows the bot to immediately respond to other users or reels
        asyncio.create_task(
            send_processed_reel_result(
                context, 
                chat_id=update.effective_chat.id, 
                reply_to_message_id=status_message.message_id, # Reply to the "Scanning..." message
                original_reel_url=link,
                reel_index=i+1,
                total_reels=len(reel_links)
            )
        )

async def send_processed_reel_result(context: ContextTypes.DEFAULT_TYPE, chat_id: int, reply_to_message_id: int, original_reel_url: str, reel_index: int, total_reels: int) -> None:
    """
    Sends the result of a processed reel back to the user by editing the 'Scanning...' message.
    The processor now returns a fully-formed message for the user.
    """
    try:
        result = await process_reel(original_reel_url)
        
        # The 'processor' now formats the entire message, including errors.
        final_message = result.get("final_message", "An unexpected error occurred.")
        
        # Add the reel count to the beginning of the message for context.
        response_text = f"Reel {reel_index}/{total_reels}:\n" + final_message
        
        # Log based on the result
        if result.get("tool_name") == "N/A" or result.get("tool_name") == "Error":
            logger.error(f"Failed to process reel {original_reel_url}. Final message: {final_message}")
        else:
            logger.info(f"Successfully processed reel {original_reel_url}. Tool: {result.get('tool_name')}")
        
        # Edit the existing "Scanning..." message to show the result
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=reply_to_message_id,
            text=response_text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.exception(f"Critical error in send_processed_reel_result for {original_reel_url}: {e}")
        # This is a fallback for unexpected errors in the processing pipeline itself
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=reply_to_message_id,
            text=f"Reel {reel_index}/{total_reels} failed due to a critical internal error. The team has been notified. Please try again later.",
            parse_mode="Markdown"
        )

async def post_init(application: Application) -> None:
    """
    Called after the Application is built.
    Ensures a clean Telegram API state by deleting webhooks before polling starts.
    """
    logger.info("Running post_init: Deleting old webhooks to clear conflicts.")
    try:
        # Delete any pending webhooks
        await application.bot.delete_webhook()
        logger.info("Old webhooks deleted in post_init.")
    except Exception as e:
        logger.warning(f"Error while trying to delete webhook in post_init: {e}")
    
    # Small delay to let Telegram API process changes
    await asyncio.sleep(1)
    logger.info("post_init complete. Ready to start polling.")


async def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Error: TELEGRAM_BOT_TOKEN not found in environment variables. Please set it in your .env file.")
        return

    # Build the application with the post_init hook and rate limiter
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .rate_limiter(user_rate_limiter)
        .build()
    )

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("privacy", privacy_command))

    # on non-command messages - handle reel links, but only if not rate-limited
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reel_links))
    # Add a handler for messages that *are* rate-limited
    application.add_handler(TypeHandler(Update, rate_limit_exceeded))


    # Run the bot until the user presses Ctrl-C
    logger.info("Bot started. Press Ctrl-C to stop.")
    try:
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Ensure the bot is stopped gracefully
        if application.running:
            await application.stop()

if __name__ == "__main__":
    main()
