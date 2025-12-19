import os
import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError, NetworkError, TimedOut
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# Create directories
os.makedirs("logs", exist_ok=True)
os.makedirs("generated_images", exist_ok=True)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Rate limiting dictionary
user_last_request = {}
REQUEST_COOLDOWN = 10  # seconds between requests


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot")

    welcome_message = f"""
Welcome to AI Image Generator Bot, {user.first_name}!

Transform your ideas into stunning visuals using OpenAI's DALL-E 3.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Quick Start Guide**

Send me any text description and I'll create an image for you.

**Example Prompts:**

1. "Mountain landscape with aurora borealis at night"
2. "Modern minimalist office space with natural lighting"
3. "Steampunk robot in a Victorian library"
4. "Abstract watercolor art with blue and gold tones"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Features:**
- 1024x1024 high-resolution images
- DALL-E 3 powered generation
- Fast processing (10-30 seconds)
- Unlimited creativity

**Available Commands:**
/start - Show this welcome message
/help - Learn how to write better prompts
/stats - View your generation statistics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ready to create? Just type your idea below.
    """

    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} requested help")

    help_text = """
**Prompt Writing Guide**

Learn how to create the best prompts for amazing results.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**1. Be Descriptive**

Bad: "a cat"
Good: "a fluffy orange cat sitting by a window with rain drops"

**2. Specify Art Style**

- "Oil painting of..."
- "Digital art featuring..."
- "Photorealistic shot of..."
- "Minimalist illustration of..."
- "Watercolor painting showing..."

**3. Add Details**

Include these elements for better results:
- Lighting: "golden hour lighting", "soft ambient light"
- Mood: "peaceful", "dramatic", "mysterious"
- Colors: "warm tones", "vibrant colors", "pastel palette"
- Composition: "close-up", "wide angle", "bird's eye view"

**4. Strong Example Prompts**

"A cozy bookstore cafe with wooden shelves, warm lighting, people reading by the window, autumn afternoon atmosphere"

"Futuristic cityscape at sunset, flying cars, neon signs, cyberpunk aesthetic, purple and blue color scheme"

"Serene Japanese garden with cherry blossoms, koi pond, stone bridge, soft morning mist, traditional architecture"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Pro Tips:**

- More details = better results
- Combine multiple concepts creatively
- Experiment with different art styles
- Specify the mood and atmosphere

Start creating your masterpiece now!
    """

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data

    images_generated = user_data.get("images_generated", 0)
    last_prompt = user_data.get("last_prompt", "None")

    logger.info(f"User {user.id} requested stats")

    stats_text = f"""
**Your Statistics**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Generation Count:** {images_generated}
**User ID:** {user.id}
**Last Prompt:** {last_prompt[:50]}...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keep creating amazing images!
    """

    await update.message.reply_text(stats_text, parse_mode="Markdown")


def check_rate_limit(user_id: int) -> tuple[bool, int]:
    """Check if user has exceeded rate limit"""
    current_time = datetime.now().timestamp()

    if user_id in user_last_request:
        time_elapsed = current_time - user_last_request[user_id]
        if time_elapsed < REQUEST_COOLDOWN:
            wait_time = int(REQUEST_COOLDOWN - time_elapsed)
            return False, wait_time

    user_last_request[user_id] = current_time
    return True, 0


async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    user = update.effective_user
    user_data = context.user_data

    # Rate limiting
    can_proceed, wait_time = check_rate_limit(user.id)
    if not can_proceed:
        await update.message.reply_text(
            f"**Rate Limit**\n\n"
            f"Please wait {wait_time} seconds before generating another image.\n\n"
            f"This helps prevent server overload.",
            parse_mode="Markdown",
        )
        logger.warning(f"Rate limit hit for user {user.id}")
        return

    logger.info(f"User {user.id} ({user.first_name}) requested image: '{prompt}'")

    # Send generating message
    status_message = await update.message.reply_text(
        f"**Creating Your Image**\n\n"
        f"Prompt: _{prompt}_\n\n"
        f"Processing... This typically takes 10-30 seconds.",
        parse_mode="Markdown",
    )

    try:
        # Generate image with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                break
            except APIConnectionError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Connection error, retrying... (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(2)
                    continue
                else:
                    raise

        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt

        # Send image
        await update.message.reply_photo(
            photo=image_url,
            caption=f"**Image Generated Successfully**\n\n"
            f"Your prompt: _{prompt}_\n\n"
            f"Enhanced by AI: _{revised_prompt[:100]}..._",
            parse_mode="Markdown",
        )

        # Delete status message
        try:
            await status_message.delete()
        except:
            pass

        # Update stats
        user_data["images_generated"] = user_data.get("images_generated", 0) + 1
        user_data["last_prompt"] = prompt

        logger.info(
            f"Successfully generated image for user {user.id}. Total: {user_data['images_generated']}"
        )

    except RateLimitError as e:
        error_msg = "OpenAI API rate limit reached. Please try again in a few moments."
        logger.error(f"Rate limit error for user {user.id}: {str(e)}")

        await status_message.edit_text(
            f"**Rate Limit Exceeded**\n\n"
            f"{error_msg}\n\n"
            f"The service is experiencing high demand. Please wait a minute and try again.",
            parse_mode="Markdown",
        )

    except APIConnectionError as e:
        error_msg = (
            "Connection to OpenAI failed. Please check your internet connection."
        )
        logger.error(f"Connection error for user {user.id}: {str(e)}")

        await status_message.edit_text(
            f"**Connection Error**\n\n"
            f"{error_msg}\n\n"
            f"Please try again in a moment.",
            parse_mode="Markdown",
        )

    except APIError as e:
        error_code = getattr(e, "status_code", "unknown")
        logger.error(f"OpenAI API error for user {user.id}: {str(e)}")

        if "content_policy_violation" in str(e).lower():
            await status_message.edit_text(
                f"**Content Policy Violation**\n\n"
                f"Your prompt violates OpenAI's content policy.\n\n"
                f"Please try a different prompt that:\n"
                f"• Avoids violence or explicit content\n"
                f"• Doesn't reference real people\n"
                f"• Follows community guidelines",
                parse_mode="Markdown",
            )
        else:
            await status_message.edit_text(
                f"**API Error**\n\n"
                f"Error code: {error_code}\n\n"
                f"An error occurred while processing your request. Please try:\n"
                f"• Simplifying your prompt\n"
                f"• Trying again in a few moments\n"
                f"• Using different wording",
                parse_mode="Markdown",
            )

    except TelegramError as e:
        logger.error(f"Telegram error for user {user.id}: {str(e)}")

        try:
            await status_message.edit_text(
                f"**Telegram Error**\n\n"
                f"Failed to send the image. This might be due to:\n"
                f"• Network connectivity issues\n"
                f"• Telegram server problems\n\n"
                f"Please try again.",
                parse_mode="Markdown",
            )
        except:
            pass

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error for user {user.id}: {error_msg}", exc_info=True)

        try:
            await status_message.edit_text(
                f"**Unexpected Error**\n\n"
                f"An unexpected error occurred.\n\n"
                f"Error details: {error_msg[:100]}\n\n"
                f"Please try:\n"
                f"• Using a different prompt\n"
                f"• Waiting a moment before trying again\n"
                f"• Contacting support if the issue persists",
                parse_mode="Markdown",
            )
        except:
            logger.error(f"Failed to send error message to user {user.id}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors caused by updates"""
    logger.error(
        f"Update {update} caused error {context.error}", exc_info=context.error
    )

    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "**System Error**\n\n"
                "An error occurred while processing your request.\n"
                "Please try again or contact support if the issue persists.",
                parse_mode="Markdown",
            )
        except:
            pass


def main():
    logger.info("Initializing bot...")

    # Validate environment variables
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        logger.error("Missing API keys in .env file!")
        print("\nError: Please set TELEGRAM_TOKEN and OPENAI_API_KEY in your .env file")
        return

    try:
        # Build application with extended timeouts
        app = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .pool_timeout(30.0)
            .get_updates_connect_timeout(30.0)
            .get_updates_read_timeout(30.0)
            .build()
        )

        # Command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("stats", stats_command))

        # Message handler
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))

        # Error handler
        app.add_error_handler(error_handler)

        logger.info("Bot started successfully!")
        print("\n" + "=" * 50)
        print("AI Image Generator Bot is ACTIVE")
        print("=" * 50)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to stop\n")

        # Run polling with retry settings
        app.run_polling(
            allowed_updates=Update.ALL_TYPES, drop_pending_updates=True, timeout=30
        )

    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
        print(f"\nFailed to start bot: {str(e)}")
        print("Please check your .env file and network connection")


if __name__ == "__main__":
    main()
