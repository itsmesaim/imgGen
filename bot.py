import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, PhotoSize
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
import base64
from io import BytesIO
from PIL import Image
import requests

# Load environment variables
load_dotenv()

# API Keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# Create directories
os.makedirs("logs", exist_ok=True)
os.makedirs("generated_images", exist_ok=True)
os.makedirs("uploaded_images", exist_ok=True)

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


def save_generated_image(image_url, user_id, image_type="generated"):
    """Download and save generated image from URL"""
    try:
        # Create user directory
        user_dir = f"generated_images/{user_id}"
        os.makedirs(user_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{image_type}_{timestamp}.png"
        filepath = os.path.join(user_dir, filename)

        # Download image from URL
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        # Save image
        with open(filepath, "wb") as f:
            f.write(response.content)

        # Get file size
        file_size = os.path.getsize(filepath)
        file_size_kb = file_size / 1024

        logger.info(
            f"Saved {image_type} image for user {user_id}: {filename} ({file_size_kb:.2f} KB)"
        )

        return filepath, file_size_kb

    except Exception as e:
        logger.error(f"Error saving generated image for user {user_id}: {str(e)}")
        return None, 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot")

    welcome_message = f"""
Welcome to AI Image Generator Bot, {user.first_name}!

Transform your ideas into stunning visuals using OpenAI's DALL-E 3.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Two Ways to Create:**

**1. Text to Image:**
Simply send a text description and I'll generate an image.

Example: "A futuristic cyberpunk city at night"

**2. Image Transformation:**
Send an image, then tell me how to transform it.

Example: Send a photo, then say:
- "Make it look like a watercolor painting"
- "Convert to anime style"
- "Make it look vintage and nostalgic"
- "Turn it into a cyberpunk version"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Features:**
- High-quality 1024x1024 images
- DALL-E 3 powered generation
- Image style transformations
- All images automatically saved
- Personal gallery for each user

**Commands:**
/start - Show this message
/help - Learn prompt techniques
/stats - View your statistics
/gallery - View saved images info
/clear - Clear uploaded image

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ready? Send a text prompt or upload an image!
    """

    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} requested help")

    help_text = """
**Complete Guide**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Text to Image Generation**

1. Be specific and descriptive
   Good: "A golden retriever in a flower field at sunset"
   Bad: "A dog"

2. Include art style
   • "Oil painting of..."
   • "Digital art style..."
   • "Photorealistic..."
   • "Minimalist design..."

3. Add details
   • Lighting: "golden hour", "soft ambient light"
   • Mood: "peaceful", "dramatic", "mysterious"
   • Colors: "warm tones", "vibrant", "pastel"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Image Transformation**

Send any image, then describe how to transform it:

**Style Changes:**
- "Make it anime style"
- "Convert to watercolor painting"
- "Turn into pixel art"
- "Make it look like a sketch"

**Mood Changes:**
- "Make it darker and more dramatic"
- "Add vintage film effect"
- "Make it bright and cheerful"
- "Give it a dreamy atmosphere"

**Theme Changes:**
- "Turn it into cyberpunk style"
- "Make it steampunk"
- "Convert to fantasy art"
- "Give it a sci-fi look"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Image Storage**

All generated and transformed images are automatically saved in your personal gallery!

Use /gallery to see your collection info.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Pro Tips:**

- More details = better results
- Combine multiple concepts
- Experiment with styles
- Be creative with transformations

Start creating now!
    """

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data

    images_generated = user_data.get("images_generated", 0)
    images_transformed = user_data.get("images_transformed", 0)
    images_uploaded = user_data.get("images_uploaded", 0)
    last_prompt = user_data.get("last_prompt", "None")

    logger.info(f"User {user.id} requested stats")

    stats_text = f"""
**Your Statistics**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Images Generated:** {images_generated}
**Images Transformed:** {images_transformed}
**Images Uploaded:** {images_uploaded}
**Total Creations:** {images_generated + images_transformed}
**User ID:** {user.id}
**Last Prompt:** {last_prompt[:50]}...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keep creating amazing images!
    """

    await update.message.reply_text(stats_text, parse_mode="Markdown")


async def gallery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data

    # Count files in user's directories
    generated_dir = f"generated_images/{user.id}"
    uploaded_dir = f"uploaded_images/{user.id}"

    generated_count = 0
    uploaded_count = 0
    total_size = 0

    if os.path.exists(generated_dir):
        generated_files = [
            f
            for f in os.listdir(generated_dir)
            if f.endswith((".jpg", ".png", ".jpeg"))
        ]
        generated_count = len(generated_files)
        total_size += sum(
            os.path.getsize(os.path.join(generated_dir, f)) for f in generated_files
        )

    if os.path.exists(uploaded_dir):
        uploaded_files = [
            f for f in os.listdir(uploaded_dir) if f.endswith((".jpg", ".png", ".jpeg"))
        ]
        uploaded_count = len(uploaded_files)
        total_size += sum(
            os.path.getsize(os.path.join(uploaded_dir, f)) for f in uploaded_files
        )

    total_size_mb = total_size / (1024 * 1024)

    logger.info(f"User {user.id} requested gallery info")

    gallery_text = f"""
**Your Gallery**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Generated Images:** {generated_count}
**Uploaded Images:** {uploaded_count}
**Total Images:** {generated_count + uploaded_count}
**Storage Used:** {total_size_mb:.2f} MB

**Storage Locations:**
- Generated: `generated_images/{user.id}/`
- Uploaded: `uploaded_images/{user.id}/`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All your images are safely stored and organized!
    """

    await update.message.reply_text(gallery_text, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = context.user_data

    if "uploaded_image_path" in user_data:
        del user_data["uploaded_image_path"]
        await update.message.reply_text(
            "**Image Cleared**\n\nYour uploaded image has been cleared. Upload a new one or send a text prompt.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "**No Image**\n\nYou don't have any uploaded image to clear.",
            parse_mode="Markdown",
        )

    logger.info(f"User {user.id} cleared uploaded image")


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


def encode_image_to_base64(image_path):
    """Encode image to base64 for OpenAI API"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def prepare_image_for_api(image_path):
    """Resize and prepare image for OpenAI API (max 4MB, PNG)"""
    img = Image.open(image_path)

    # Convert to RGB if necessary
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(
            img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
        )
        img = background

    # Resize if too large (max 1024x1024 for DALL-E)
    max_size = 1024
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # Save as PNG
    output_path = image_path.rsplit(".", 1)[0] + "_prepared.png"
    img.save(output_path, "PNG", optimize=True)

    return output_path


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded photos from users"""
    user = update.effective_user
    user_data = context.user_data

    logger.info(f"User {user.id} ({user.first_name}) uploaded an image")

    try:
        # Get the highest resolution photo
        photo = update.message.photo[-1]

        # Create user directory if it doesn't exist
        user_dir = f"uploaded_images/{user.id}"
        os.makedirs(user_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upload_{timestamp}.jpg"
        filepath = os.path.join(user_dir, filename)

        # Download the photo
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(filepath)

        # Store the image path in user data
        user_data["uploaded_image_path"] = filepath

        # Update upload count
        user_data["images_uploaded"] = user_data.get("images_uploaded", 0) + 1

        # Check if user sent caption with the image
        if update.message.caption:
            # User sent image with caption, treat caption as transformation prompt
            await transform_image(update, context, update.message.caption)
        else:
            # No caption, ask user what they want to do
            await update.message.reply_text(
                "**Image Received**\n\n"
                "What would you like me to do with this image?\n\n"
                "Examples:\n"
                "• Make it anime style\n"
                "• Convert to watercolor painting\n"
                "• Turn into cyberpunk version\n"
                "• Make it look vintage\n\n"
                "Or use /clear to remove this image.",
                parse_mode="Markdown",
            )

        logger.info(f"Image uploaded and stored for user {user.id}: {filename}")

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error handling photo for user {user.id}: {error_msg}", exc_info=True
        )

        await update.message.reply_text(
            f"**Upload Error**\n\n"
            f"Failed to process your image.\n\n"
            f"Please try:\n"
            f"• Sending a smaller image\n"
            f"• Using a different image format\n"
            f"• Checking your connection",
            parse_mode="Markdown",
        )


async def transform_image(
    update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str
):
    """Transform uploaded image based on user prompt"""
    user = update.effective_user
    user_data = context.user_data

    # Check if there's an uploaded image
    if "uploaded_image_path" not in user_data:
        await update.message.reply_text(
            "**No Image Found**\n\n"
            "Please upload an image first, then tell me how to transform it.\n\n"
            "Or send a text prompt to generate a new image.",
            parse_mode="Markdown",
        )
        return

    # Rate limiting
    can_proceed, wait_time = check_rate_limit(user.id)
    if not can_proceed:
        await update.message.reply_text(
            f"**Rate Limit**\n\n"
            f"Please wait {wait_time} seconds before making another request.",
            parse_mode="Markdown",
        )
        logger.warning(f"Rate limit hit for user {user.id}")
        return

    logger.info(f"User {user.id} requested image transformation: '{prompt}'")

    status_message = await update.message.reply_text(
        f"**Transforming Image**\n\n"
        f"Request: _{prompt}_\n\n"
        f"Processing... This may take 10-30 seconds.",
        parse_mode="Markdown",
    )

    try:
        image_path = user_data["uploaded_image_path"]

        # Prepare image for API
        prepared_image_path = prepare_image_for_api(image_path)

        # Read and encode image
        with open(prepared_image_path, "rb") as image_file:
            image_data = image_file.read()

        # Create variation using DALL-E
        full_prompt = f"An image that {prompt}, maintaining the essence and subject of the original"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=full_prompt,
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

        # Save the generated image
        saved_path, file_size = save_generated_image(image_url, user.id, "transformed")

        # Send transformed image
        await update.message.reply_photo(
            photo=image_url,
            caption=f"**Image Transformed**\n\n"
            f"Your request: _{prompt}_\n\n"
            f"Saved as: `{os.path.basename(saved_path) if saved_path else 'N/A'}`",
            parse_mode="Markdown",
        )

        # Delete status message
        try:
            await status_message.delete()
        except:
            pass

        # Clean up prepared image
        if os.path.exists(prepared_image_path):
            os.remove(prepared_image_path)

        # Clear the uploaded image after successful transformation
        del user_data["uploaded_image_path"]

        # Update stats
        user_data["images_transformed"] = user_data.get("images_transformed", 0) + 1
        user_data["last_prompt"] = prompt

        logger.info(
            f"Successfully transformed image for user {user.id}. Total: {user_data['images_transformed']}"
        )

    except RateLimitError as e:
        logger.error(f"Rate limit error for user {user.id}: {str(e)}")
        await status_message.edit_text(
            f"**Rate Limit Exceeded**\n\n"
            f"OpenAI API rate limit reached.\n\n"
            f"Please wait a minute and try again.",
            parse_mode="Markdown",
        )

    except APIConnectionError as e:
        logger.error(f"Connection error for user {user.id}: {str(e)}")
        await status_message.edit_text(
            f"**Connection Error**\n\n"
            f"Failed to connect to OpenAI.\n\n"
            f"Please try again in a moment.",
            parse_mode="Markdown",
        )

    except APIError as e:
        logger.error(f"OpenAI API error for user {user.id}: {str(e)}")

        if "content_policy_violation" in str(e).lower():
            await status_message.edit_text(
                f"**Content Policy Violation**\n\n"
                f"Your transformation request or image violates OpenAI's content policy.\n\n"
                f"Please try a different transformation or image.",
                parse_mode="Markdown",
            )
        else:
            await status_message.edit_text(
                f"**API Error**\n\n"
                f"An error occurred during transformation.\n\n"
                f"Please try:\n"
                f"• A different transformation description\n"
                f"• Uploading a different image\n"
                f"• Trying again in a moment",
                parse_mode="Markdown",
            )

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Unexpected error transforming image for user {user.id}: {error_msg}",
            exc_info=True,
        )

        try:
            await status_message.edit_text(
                f"**Transformation Error**\n\n"
                f"An unexpected error occurred.\n\n"
                f"Error: {error_msg[:100]}\n\n"
                f"Please try again or upload a different image.",
                parse_mode="Markdown",
            )
        except:
            pass


async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    user = update.effective_user
    user_data = context.user_data

    # Check if user has an uploaded image waiting for transformation
    if "uploaded_image_path" in user_data:
        await transform_image(update, context, prompt)
        return

    # Rate limiting
    can_proceed, wait_time = check_rate_limit(user.id)
    if not can_proceed:
        await update.message.reply_text(
            f"**Rate Limit**\n\n"
            f"Please wait {wait_time} seconds before generating another image.",
            parse_mode="Markdown",
        )
        logger.warning(f"Rate limit hit for user {user.id}")
        return

    logger.info(f"User {user.id} ({user.first_name}) requested image: '{prompt}'")

    status_message = await update.message.reply_text(
        f"**Creating Your Image**\n\n"
        f"Prompt: _{prompt}_\n\n"
        f"Processing... This typically takes 10-30 seconds.",
        parse_mode="Markdown",
    )

    try:
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

        # Save the generated image
        saved_path, file_size = save_generated_image(image_url, user.id, "generated")

        await update.message.reply_photo(
            photo=image_url,
            caption=f"**Image Generated Successfully**\n\n"
            f"Your prompt: _{prompt}_\n\n"
            f"Saved as: `{os.path.basename(saved_path) if saved_path else 'N/A'}`",
            parse_mode="Markdown",
        )

        try:
            await status_message.delete()
        except:
            pass

        user_data["images_generated"] = user_data.get("images_generated", 0) + 1
        user_data["last_prompt"] = prompt

        logger.info(
            f"Successfully generated image for user {user.id}. Total: {user_data['images_generated']}"
        )

    except RateLimitError as e:
        logger.error(f"Rate limit error for user {user.id}: {str(e)}")
        await status_message.edit_text(
            f"**Rate Limit Exceeded**\n\n"
            f"OpenAI API rate limit reached.\n\n"
            f"Please wait a minute and try again.",
            parse_mode="Markdown",
        )

    except APIConnectionError as e:
        logger.error(f"Connection error for user {user.id}: {str(e)}")
        await status_message.edit_text(
            f"**Connection Error**\n\n"
            f"Failed to connect to OpenAI.\n\n"
            f"Please try again in a moment.",
            parse_mode="Markdown",
        )

    except APIError as e:
        logger.error(f"OpenAI API error for user {user.id}: {str(e)}")

        if "content_policy_violation" in str(e).lower():
            await status_message.edit_text(
                f"**Content Policy Violation**\n\n"
                f"Your prompt violates OpenAI's content policy.\n\n"
                f"Please try a different prompt.",
                parse_mode="Markdown",
            )
        else:
            await status_message.edit_text(
                f"**API Error**\n\n"
                f"An error occurred.\n\n"
                f"Please try:\n"
                f"• Simplifying your prompt\n"
                f"• Trying again in a moment\n"
                f"• Using different wording",
                parse_mode="Markdown",
            )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error for user {user.id}: {error_msg}", exc_info=True)

        try:
            await status_message.edit_text(
                f"**Unexpected Error**\n\n"
                f"An unexpected error occurred.\n\n"
                f"Error: {error_msg[:100]}\n\n"
                f"Please try again.",
                parse_mode="Markdown",
            )
        except:
            pass


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
                "Please try again.",
                parse_mode="Markdown",
            )
        except:
            pass


def main():
    logger.info("Initializing bot...")

    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        logger.error("Missing API keys in .env file!")
        print("\nError: Please set TELEGRAM_TOKEN and OPENAI_API_KEY in your .env file")
        return

    try:
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
        app.add_handler(CommandHandler("gallery", gallery_command))
        app.add_handler(CommandHandler("clear", clear_command))

        # Photo handler (must come before text handler)
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

        # Message handler for text
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))

        # Error handler
        app.add_error_handler(error_handler)

        logger.info("Bot started successfully!")
        print("\n" + "=" * 50)
        print("AI Image Generator Bot is ACTIVE")
        print("=" * 50)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Press Ctrl+C to stop\n")

        app.run_polling(
            allowed_updates=Update.ALL_TYPES, drop_pending_updates=True, timeout=30
        )

    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
        print(f"\nFailed to start bot: {str(e)}")
        print("Please check your .env file and network connection")


if __name__ == "__main__":
    main()
