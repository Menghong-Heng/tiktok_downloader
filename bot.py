from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import logging
from downloader import fetch_video, fetch_photos
import asyncio

# Load token from .env
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    welcome_text = """🎵 Welcome to TikTok Downloader Bot!

Send me any TikTok link and I'll download the video without watermark for you.

Commands:
/start - Show this message
/help - Show help information

Features:
✅ No watermark videos
✅ HD quality when available
✅ Fast downloads
✅ Works with all TikTok URLs

Just paste a TikTok link and I'll handle the rest! 🚀"""
    await update.message.reply_text(welcome_text)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    help_text = """📖 How to use this bot:

1. Copy a TikTok video link (any format works)
2. Paste it in this chat
3. Wait a few seconds for processing
4. Receive your watermark-free video!

Supported URL formats:
• https://www.tiktok.com/@user/video/1234567890
• https://vt.tiktok.com/xxxxx/
• https://vm.tiktok.com/xxxxx/

The bot will automatically:
• Resolve short URLs
• Extract video ID
• Download in best available quality
• Remove watermarks

If you encounter any issues, try again or contact support."""
    await update.message.reply_text(help_text)

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    
    text = update.message.text
    if text is None:
        await update.message.reply_text("Please send a text message.")
        return
    
    text = text.strip()
    chat_id = update.message.chat.id
    logger.info(f"Received from {chat_id}: {text}")

    # Check if it's a TikTok URL
    if "tiktok.com" not in text:
        await update.message.reply_text("❌ Please send a valid TikTok link.\n\nI can only process TikTok videos and photos. Make sure the link contains 'tiktok.com'")
        return

    # Send initial response
    status_message = await update.message.reply_text("🔄 Processing your TikTok link...\n\nThis may take a few seconds.")

    try:
        # Try photo post first
        await status_message.edit_text("🔄 Checking if this is a TikTok photo post...")
        photo_buffers, photo_caption = await fetch_photos(text)
        if photo_buffers:
            await status_message.edit_text("📸 Downloading TikTok photo post...\n\n📤 Uploading to Telegram...")
            for idx, img_buffer in enumerate(photo_buffers):
                await update.message.reply_photo(
                    photo=InputFile(img_buffer, filename=f"tiktok_photo_{idx+1}.jpg"),
                    caption=photo_caption if idx == 0 else None
                )
            await status_message.edit_text("✅ TikTok photo post downloaded successfully!\n\n🎉 Enjoy your TikTok photos!")
            await asyncio.sleep(5)
            await status_message.delete()
            return

        # Not a photo post, try video as before
        await status_message.edit_text("🔄 Processing your TikTok video...\n\n⏳ Resolving URL and extracting video...")
        video_bytes, caption = await fetch_video(text)
        if video_bytes:
            file_size = len(video_bytes.getvalue())
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                await status_message.edit_text(f"❌ Video too large ({file_size // (1024*1024)}MB)\n\nTelegram bot limit is 50MB. Try a shorter video.")
                return
            await status_message.edit_text("🔄 Processing your TikTok video...\n\n📤 Uploading to Telegram...")
            await update.message.reply_video(
                video=InputFile(video_bytes, filename="tiktok_video.mp4"), 
                caption=caption,
                supports_streaming=True
            )
            await status_message.edit_text("✅ Video downloaded successfully!\n\n🎉 Enjoy your watermark-free TikTok video!")
            await asyncio.sleep(5)
            await status_message.delete()
        else:
            await status_message.edit_text("❌ Failed to download video or photo.\n\nPossible reasons:\n• Video/photo is private or deleted\n• Region restrictions\n• Network issues\n\nTry again or use a different link.")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        await status_message.edit_text("❌ Something went wrong while downloading the video or photo.\n\nError: " + str(e)[:100] + "\n\nPlease try again or contact support.")

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# Main bot runner
def main():
    if not TOKEN:
        raise RuntimeError("TOKEN is missing from .env")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot started successfully! 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
