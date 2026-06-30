import os
import io
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from PIL import Image
import tempfile

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.environ.get("TELEGRAM_TOKEN")
BOT_NAME = os.environ.get("BOT_NAME", "WebPConverter4Bot")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "WebPConverter4Bot")

if not TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable not set!")
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

logger.info(f"🤖 Bot Name: {BOT_NAME}")
logger.info(f"📡 Bot Username: @{BOT_USERNAME}")
logger.info(f"🔑 Token: {TOKEN[:10]}... (first 10 chars)")

# Store user session data
user_sessions = {}

# Supported formats for conversion
SUPPORTED_FORMATS = ['jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'webp']
QUALITY_OPTIONS = [25, 50, 75, 90, 100]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    welcome_text = (
        f"🎯 Welcome to {BOT_NAME}!\n\n"
        "I can convert your images to WebP format with ease!\n\n"
        "📸 How to use:\n"
        "1️⃣ Send me any image (JPG, PNG, BMP, GIF, etc.)\n"
        "2️⃣ Choose your conversion options\n"
        "3️⃣ Get your WebP image instantly!\n\n"
        "📚 Features:\n"
        "• Batch conversion (send multiple images)\n"
        "• Quality settings (25% - 100%)\n"
        "• Lossless conversion option\n"
        "• Preserve transparency\n\n"
        "🔧 Use /help to see all commands."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = (
        f"🤖 {BOT_NAME} Help:\n\n"
        "📤 Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/settings - Configure conversion settings\n"
        "/stats - View your statistics\n"
        "/cancel - Cancel current operation\n\n"
        "🔄 Conversion Options:\n"
        "• Quality: 25% (small) to 100% (best quality)\n"
        "• Lossless: Preserve exact image quality\n"
        "• Transparency: Keep transparent backgrounds\n\n"
        "💡 Tips:\n"
        "• Send multiple images at once for batch conversion\n"
        "• Forward images from other chats\n"
        "• Images are processed and deleted immediately\n\n"
        f"📱 Bot: @{BOT_USERNAME}"
    )
    await update.message.reply_text(help_text)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show and configure conversion settings."""
    user_id = str(update.effective_user.id)
    settings = user_sessions.get(user_id, {})
    quality = settings.get('quality', 75)
    lossless = settings.get('lossless', False)
    
    settings_text = (
        f"⚙️ Current Settings:\n\n"
        f"📊 Quality: {quality}%\n"
        f"🔒 Lossless: {'✅ Enabled' if lossless else '❌ Disabled'}\n"
        f"📏 Max Dimensions: 4096x4096\n\n"
        "Choose quality level:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("25% (Small)", callback_data="quality_25"),
            InlineKeyboardButton("50% (Medium)", callback_data="quality_50")
        ],
        [
            InlineKeyboardButton("75% (Good)", callback_data="quality_75"),
            InlineKeyboardButton("100% (Best)", callback_data="quality_100")
        ],
        [
            InlineKeyboardButton(f"{'🔓' if lossless else '🔒'} Lossless", callback_data="toggle_lossless")
        ],
        [
            InlineKeyboardButton("📤 Apply Settings", callback_data="apply_settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(settings_text, reply_markup=reply_markup)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics."""
    user_id = str(update.effective_user.id)
    stats = user_sessions.get(user_id, {})
    converted_count = stats.get('converted_count', 0)
    
    stats_text = (
        f"📊 Your Statistics:\n\n"
        f"🖼️ Images converted: {converted_count}\n"
        f"⚡ Status: Active\n"
        f"🤖 Bot: {BOT_NAME}\n"
        f"📅 Since: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        "Keep converting! 🚀"
    )
    await update.message.reply_text(stats_text)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation."""
    user_id = str(update.effective_user.id)
    if user_id in user_sessions:
        user_sessions[user_id]['converting'] = False
    await update.message.reply_text("✅ Operation cancelled! Send a new image to convert.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming images."""
    user_id = str(update.effective_user.id)
    message = update.message
    
    # Initialize user session
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'quality': 75,
            'lossless': False,
            'converted_count': 0,
            'converting': True
        }
    
    user_sessions[user_id]['converting'] = True
    
    if not message.photo:
        await message.reply_text("⚠️ Please send a valid image file.")
        return
    
    # Send processing message
    processing_msg = await message.reply_text("🔄 Processing your image...")
    
    try:
        # Get photo
        photo_file = await message.photo[-1].get_file()
        image_data = await photo_file.download_as_bytearray()
        
        # Open image
        image = Image.open(io.BytesIO(image_data))
        
        # Get settings
        settings = user_sessions.get(user_id, {})
        quality = settings.get('quality', 75)
        lossless = settings.get('lossless', False)
        
        # Convert to WebP
        output = io.BytesIO()
        image.save(output, format='WEBP', quality=quality, lossless=lossless, optimize=True)
        output.seek(0)
        
        # Update statistics
        user_sessions[user_id]['converted_count'] = user_sessions[user_id].get('converted_count', 0) + 1
        
        # Get file size
        size_kb = len(output.getvalue()) // 1024
        
        # Send converted image
        await message.reply_document(
            document=output,
            filename=f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webp",
            caption=f"✅ Converted to WebP!\n"
                   f"📊 Quality: {quality}%\n"
                   f"🔒 Lossless: {'Yes' if lossless else 'No'}\n"
                   f"📏 Size: {size_kb} KB"
        )
        
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        await processing_msg.edit_text(
            f"❌ Error converting image: {str(e)}\n"
            "Please try again with a different image."
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document images."""
    user_id = str(update.effective_user.id)
    message = update.message
    document = message.document
    
    # Initialize user session
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'quality': 75,
            'lossless': False,
            'converted_count': 0,
            'converting': True
        }
    
    user_sessions[user_id]['converting'] = True
    
    if not document.mime_type or not document.mime_type.startswith('image/'):
        await message.reply_text("⚠️ Please send an image file (JPG, PNG, BMP, GIF, etc.)")
        return
    
    # Check if it's already WebP
    if document.mime_type == 'image/webp':
        keyboard = [
            [InlineKeyboardButton("🔄 Convert Anyway", callback_data="convert_anyway")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_conversion")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(
            "⚠️ This image is already in WebP format.\n"
            "Do you want to convert it anyway?",
            reply_markup=reply_markup
        )
        return
    
    # Send processing message
    processing_msg = await message.reply_text("🔄 Processing your image...")
    
    try:
        # Get file
        file = await document.get_file()
        image_data = await file.download_as_bytearray()
        
        # Open image
        image = Image.open(io.BytesIO(image_data))
        
        # Get settings
        settings = user_sessions.get(user_id, {})
        quality = settings.get('quality', 75)
        lossless = settings.get('lossless', False)
        
        # Convert to WebP
        output = io.BytesIO()
        image.save(output, format='WEBP', quality=quality, lossless=lossless, optimize=True)
        output.seek(0)
        
        # Update statistics
        user_sessions[user_id]['converted_count'] = user_sessions[user_id].get('converted_count', 0) + 1
        
        # Get file size
        size_kb = len(output.getvalue()) // 1024
        
        # Send converted image
        await message.reply_document(
            document=output,
            filename=f"converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webp",
            caption=f"✅ Converted to WebP!\n"
                   f"📊 Quality: {quality}%\n"
                   f"🔒 Lossless: {'Yes' if lossless else 'No'}\n"
                   f"📏 Size: {size_kb} KB"
        )
        
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await processing_msg.edit_text(
            f"❌ Error converting image: {str(e)}\n"
            "Please try again with a different image."
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = query.data
    
    if data == "cancel_conversion":
        user_sessions[user_id]['converting'] = False
        await query.edit_message_text("❌ Conversion cancelled.")
        return
    
    if data == "convert_anyway":
        await query.edit_message_text("🔄 Please send the image again to convert it.")
        return
    
    if data == "apply_settings":
        settings = user_sessions.get(user_id, {})
        quality = settings.get('quality', 75)
        lossless = settings.get('lossless', False)
        
        await query.edit_message_text(
            f"✅ Settings applied!\n\n"
            f"📊 Quality: {quality}%\n"
            f"🔒 Lossless: {'✅ Enabled' if lossless else '❌ Disabled'}\n\n"
            "Send an image to convert with these settings!"
        )
        return
    
    if data == "toggle_lossless":
        settings = user_sessions.get(user_id, {})
        settings['lossless'] = not settings.get('lossless', False)
        user_sessions[user_id] = settings
        
        lossless_status = settings['lossless']
        
        keyboard = [
            [
                InlineKeyboardButton("25% (Small)", callback_data="quality_25"),
                InlineKeyboardButton("50% (Medium)", callback_data="quality_50")
            ],
            [
                InlineKeyboardButton("75% (Good)", callback_data="quality_75"),
                InlineKeyboardButton("100% (Best)", callback_data="quality_100")
            ],
            [
                InlineKeyboardButton(f"{'🔓' if lossless_status else '🔒'} Lossless", callback_data="toggle_lossless")
            ],
            [
                InlineKeyboardButton("📤 Apply Settings", callback_data="apply_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔒 Lossless {'✅ Enabled' if lossless_status else '❌ Disabled'}\n\n"
            "Choose quality level:",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("quality_"):
        quality = int(data.split("_")[1])
        settings = user_sessions.get(user_id, {})
        settings['quality'] = quality
        user_sessions[user_id] = settings
        
        keyboard = [
            [
                InlineKeyboardButton("25% (Small)", callback_data="quality_25"),
                InlineKeyboardButton("50% (Medium)", callback_data="quality_50")
            ],
            [
                InlineKeyboardButton("75% (Good)", callback_data="quality_75"),
                InlineKeyboardButton("100% (Best)", callback_data="quality_100")
            ],
            [
                InlineKeyboardButton(f"{'🔓' if user_sessions[user_id].get('lossless', False) else '🔒'} Lossless", callback_data="toggle_lossless")
            ],
            [
                InlineKeyboardButton("📤 Apply Settings", callback_data="apply_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Quality set to {quality}%\n\n"
            "Choose quality level:",
            reply_markup=reply_markup
        )
        return

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and notify user."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again.\n"
                "If the problem persists, use /help for assistance."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def main():
    """Start the bot."""
    try:
        # Create application
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("settings", settings_command))
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CommandHandler("cancel", cancel_command))
        
        # Add message handlers
        app.add_handler(MessageHandler(filters.PHOTO, handle_image))
        app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
        
        # Add callback query handler
        app.add_handler(CallbackQueryHandler(handle_callback))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        logger.info(f"🤖 {BOT_NAME} starting with long polling...")
        logger.info(f"📡 Bot: @{BOT_USERNAME}")
        
        # Start the bot
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        raise

if __name__ == "__main__":
    main()
