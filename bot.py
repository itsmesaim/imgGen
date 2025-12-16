import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot")

    welcome_message = f"""
**AI Image Generator Bot**

Welcome, {user.first_name}!

This bot generates high-quality images from text descriptions using OpenAI's DALL-E 3.

**How to use:**
Simply send me a text prompt and I'll generate an image for you.

**Examples:**
- A serene mountain landscape at sunrise
- Futuristic cyberpunk city with neon lights
- Cute robot reading a book in a library
- Abstract art with vibrant colors and geometric shapes

**Features:**
- High-quality 1024x1024 images
- Powered by DALL-E 3
- Fast generation

**Commands:**
/start - Show this message
/help - Get help and tips
/stats - View your usage statistics

Ready to start? Send me your first prompt.
    """

    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} requested help")

    help_text = """
**Help & Tips**

**Writing effective prompts:**

1. Be specific and descriptive
   Good: "A golden retriever playing in a flower field at sunset"
   Bad: "A dog"

2. Include style and mood
   - Oil painting style
   - Digital art style
   - Photorealistic
   - Minimalist design

3. Describe details
   - Colors, lighting, atmosphere
   - Composition and perspective
   - Emotions and actions

4. Example prompts:
   - "A cozy coffee shop interior, warm lighting, vintage furniture, plants on windowsill"
   - "Astronaut floating in space, Earth in background, cinematic lighting"
   - "Fantasy forest with glowing mushrooms, mystical atmosphere, moonlight filtering through trees"

Describe what you imagine and I'll generate it for you.
    """

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data

    images_generated = user_data.get("images_generated", 0)

    logger.info(f"User {user.id} requested stats")

    stats_text = f"""
**Your Statistics**

Images Generated: {images_generated}
User ID: {user.id}

Total images created: {images_generated}
    """

    await update.message.reply_text(stats_text, parse_mode="Markdown")


async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    user = update.effective_user
    user_data = context.user_data

    logger.info(f"User {user.id} ({user.first_name}) requested image: '{prompt}'")

    # Send "generating" message
    status_message = await update.message.reply_text(
        f"**Generating image...**\n\n"
        f"Prompt: _{prompt}_\n\n"
        f"This usually takes 10-30 seconds.",
        parse_mode="Markdown",
    )

    try:
        # Generate image
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt

        # Send image
        await update.message.reply_photo(
            photo=image_url,
            caption=f"**Generated Successfully**\n\n"
            f"Your prompt: _{prompt}_\n\n"
            f"Enhanced prompt: _{revised_prompt}_",
            parse_mode="Markdown",
        )

        # Delete status message
        await status_message.delete()

        # Update stats
        user_data["images_generated"] = user_data.get("images_generated", 0) + 1

        logger.info(
            f"Successfully generated image for user {user.id}. Total: {user_data['images_generated']}"
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error generating image for user {user.id}: {error_msg}")

        await status_message.edit_text(
            f"**Error generating image**\n\n"
            f"Error: {error_msg}\n\n"
            f"Please try:\n"
            f"- Using a different prompt\n"
            f"- Making your prompt more specific\n"
            f"- Avoiding prohibited content",
            parse_mode="Markdown",
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


def main():
    logger.info("Starting bot...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("Bot is running! Press Ctrl+C to stop.")
    print("\n" + "=" * 50)
    print("Telegram Image Generator Bot is ACTIVE")
    print("=" * 50 + "\n")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
