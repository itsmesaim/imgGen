# AI Image Generator Telegram Bot

A Telegram bot that generates and transforms images using OpenAI's DALL-E 3.

## Features

- **Text to Image Generation** - Create images from text descriptions
- **Image Transformation** - Upload images and transform them with text prompts
- **Auto-Save** - All generated and uploaded images are automatically saved
- **Personal Gallery** - Each user gets their own organized image collection
- **Rate Limiting** - Built-in cooldown to prevent abuse
- **Comprehensive Logging** - All activities logged for debugging

## Requirements

- Python 3.8+
- OpenAI API Key
- Telegram Bot Token

## Installation

### 1. Clone or Download
```bash
git clone <your-repo-url>
cd telegram-image-bot
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

Create a `.env` file:
```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Get Telegram Bot Token:**
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the token provided

**Get OpenAI API Key:**
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create new secret key
3. Copy the key (starts with `sk-`)

### 5. Run the Bot
```bash
python3 bot.py
```

## Usage

### Text to Image Generation

Simply send a text description:
```
A futuristic cyberpunk city at night with neon lights
```

### Image Transformation

**Method 1:** Send image, then send transformation prompt:
```
1. [Upload image]
2. Make it anime style
```

**Method 2:** Send image with caption:
```
[Upload image with caption: "convert to watercolor painting"]
```

## Commands

- `/start` - Show welcome message
- `/help` - Learn prompt techniques
- `/stats` - View your statistics
- `/gallery` - View saved images info
- `/clear` - Clear uploaded image

## Example Prompts

**Generation:**
- "A serene mountain landscape at sunrise"
- "Modern minimalist office with natural lighting"
- "Abstract watercolor art with blue and gold tones"

**Transformation:**
- "Make it anime style"
- "Convert to watercolor painting"
- "Turn into cyberpunk version"
- "Make it look vintage and nostalgic"

## Directory Structure
```
telegram-image-bot/
├── venv/
├── logs/                    # Daily log files
├── generated_images/        # All generated images by user
│   └── {user_id}/
├── uploaded_images/         # All uploaded images by user
│   └── {user_id}/
├── .env                     # API keys (create this)
├── .gitignore
├── requirements.txt
├── bot.py
└── README.md
```

## Configuration

Edit these values in `bot.py` if needed:
```python
REQUEST_COOLDOWN = 10  # Seconds between requests (default: 10)
```

## Logging

Logs are saved in `logs/bot_YYYYMMDD.log`

View logs:
```bash
tail -f logs/bot_*.log
```

## Troubleshooting

**Bot won't start:**
- Check `.env` file has correct API keys
- Ensure virtual environment is activated
- Check internet connection

**Timeout errors:**
- Increase timeout values in `bot.py`
- Check firewall/proxy settings
- Verify Telegram API is accessible

**Images not saving:**
- Check disk space
- Verify write permissions on directories
- Check logs for specific errors

## License

MIT License

## Author

Saim - [GitHub](https://github.com/itsmesaim)