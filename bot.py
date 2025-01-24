from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import subprocess
import os
import re
import asyncio
import random

# Replace with your Bot API token
BOT_TOKEN = "7625156217:AAFYPOan4H-XRIM4R_P_CCmdjqyQwIdxZOM"

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, "bin")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

# Path to executables
YT_DLP_PATH = os.path.join(BIN_DIR, "yt-dlp")
FFMPEG_PATH = "/usr/bin/ffmpeg"

# Ensure the downloads directory exists
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Install FFmpeg if not already installed
if not os.path.exists(FFMPEG_PATH):
    subprocess.run(["sudo", "apt-get", "update"])
    subprocess.run(["sudo", "apt-get", "install", "-y", "ffmpeg"])

# Conversation states
WAITING_FOR_URL, WAITING_FOR_CHOICE = range(2)

# Validate YouTube URL
def is_valid_youtube_url(url):
    youtube_regex = re.compile(r'(https?://)?(www\.)?(youtube|youtu)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return bool(youtube_regex.match(url))

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to YouTube Downloader Bot!\n"
        "Send me a YouTube link, and I'll help you download it."
    )
    return WAITING_FOR_URL

# Handle URL input
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not is_valid_youtube_url(url):
        await update.message.reply_text("Please send a valid YouTube link.")
        return WAITING_FOR_URL

    # Save the URL in the context
    context.user_data['url'] = url

    # Create inline keyboard for video/audio choice
    keyboard = [
        [InlineKeyboardButton("Download Video", callback_data='video')],
        [InlineKeyboardButton("Download Audio (MP3)", callback_data='audio')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("What would you like to download?", reply_markup=reply_markup)
    return WAITING_FOR_CHOICE

# Handle inline button callbacks
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    url = context.user_data.get('url')

    if not url:
        await query.edit_message_text("Please send a YouTube link first.")
        return WAITING_FOR_URL

    if choice == 'video':
        await query.edit_message_text("Downloading video...")
        await download_video(update, context)
    elif choice == 'audio':
        await query.edit_message_text("Downloading audio...")
        await download_audio(update, context)

    # Reset the conversation state to WAITING_FOR_URL
    return WAITING_FOR_URL

# Download Video
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get('url')

    try:
        # Use yt-dlp as a subprocess
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        ]
        user_agent = random.choice(user_agents)

        command = [
            YT_DLP_PATH,
            '--cookies', os.path.join(BASE_DIR, 'cookies.txt'),
            '--add-header', f'User-Agent:{user_agent}',
            '--ffmpeg-location', FFMPEG_PATH,
            '-f', 'b',
            '-o', os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
            '--write-thumbnail',
            url
        ]

        # Run the command and capture output
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Command output:", result.stdout)
        print("Command error:", result.stderr)

        # Find the downloaded file
        downloaded_files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith(('.mp4', '.mkv', '.webm'))]
        if not downloaded_files:
            await update.callback_query.edit_message_text("Error: No video file found.")
            return

        file_path = os.path.join(DOWNLOADS_DIR, downloaded_files[0])
        thumbnail_path = os.path.join(DOWNLOADS_DIR, downloaded_files[0].rsplit('.', 1)[0] + '.webp')

        # Send the video to the user
        await update.callback_query.edit_message_text(f"Uploading video: {downloaded_files[0]}...")
        await send_large_file(update, context, file_path, thumbnail_path, is_video=True)

        # Clean up
        try:
            os.remove(file_path)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    except subprocess.CalledProcessError as e:
        print("Command failed with error:", e.stderr)
        await update.callback_query.edit_message_text(f"Error: {e.stderr}")

# Download Audio
async def download_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = context.user_data.get('url')

    try:
        # Use yt-dlp as a subprocess
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        ]
        user_agent = random.choice(user_agents)

        command = [
            YT_DLP_PATH,
            '--cookies', os.path.join(BASE_DIR, 'cookies.txt'),
            '--add-header', f'User-Agent:{user_agent}',
            '--ffmpeg-location', FFMPEG_PATH,
            '-f', 'bestaudio',
            '--extract-audio',
            '--audio-format', 'mp3',
            '-o', os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
            url
        ]

        # Run the command and capture output
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Command output:", result.stdout)
        print("Command error:", result.stderr)

        # Find the downloaded file
        downloaded_files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith('.mp3')]
        if not downloaded_files:
            await update.callback_query.edit_message_text("Error: No audio file found.")
            return

        file_path = os.path.join(DOWNLOADS_DIR, downloaded_files[0])

        # Send the audio to the user
        await update.callback_query.edit_message_text(f"Uploading audio: {downloaded_files[0]}...")
        await send_large_file(update, context, file_path, is_video=False)

        # Clean up
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    except subprocess.CalledProcessError as e:
        print("Command failed with error:", e.stderr)
        await update.callback_query.edit_message_text(f"Error: {e.stderr}")

# Send large files with retries
async def send_large_file(update, context, file_path, thumbnail_path=None, is_video=True):
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as file:
                if is_video:
                    await context.bot.send_video(
                        chat_id=update.callback_query.message.chat_id,
                        video=file,
                        thumbnail=open(thumbnail_path, 'rb') if thumbnail_path and os.path.exists(thumbnail_path) else None,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60
                    )
                else:
                    await context.bot.send_audio(
                        chat_id=update.callback_query.message.chat_id,
                        audio=file,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60
                    )
            break  # Success, exit the retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"All attempts failed: {e}")
                raise e

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Operation canceled.")
    return ConversationHandler.END

# Main Function
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url)],
            WAITING_FOR_CHOICE: [CallbackQueryHandler(handle_choice)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Start bot
    application.run_polling()

if __name__ == "__main__":
    main()