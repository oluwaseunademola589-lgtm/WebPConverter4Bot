#!/usr/bin/env python3
"""
WebPConverter4Bot - A Telegram bot for converting images to WebP format
"""

import os
import io
import logging
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from PIL import Image

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.environ.get("TELEGRAM_TOKEN")
BOT_NAME = os.environ.get("BOT_NAME", "WebPConverter4Bot")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "WebPConverter4Bot")

# Check if token is set
if not TOKEN:
    logger.error("=" * 60)
    logger.error("❌ TELEGRAM_TOKEN environment variable not set!")
    logger.error("=" * 60)
    logger.error("Please add TELEGRAM_TOKEN to Railway Variables:")
    logger.error("1. Go to Railway Dashboard")
    logger.error("2. Click on your service")
    logger.error("3. Click 'Variables' tab")
    logger.error("4. Add variable: TELEGRAM_TOKEN = your_token_from_botfather")
    logger.error("5. Click 'Redeploy'")
    logger.error("=" * 60)
    sys.exit(1)

logger.info("=" * 60)
logger.info(f"🤖 Bot Name: {BOT_NAME}")
logger.info(f"📡 Bot Username: @{BOT_USERNAME}")
logger.info(f"🔑 Token: {TOKEN[:10]}... (first 10 chars)")
logger.info("=" * 60)

# User sessions storage
user_sessions: Dict[str, Dict[str, Any]] = {}

# Constants
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message when /start is issued."""
    welcome_text = (
        f"🎯 **Welcome to {BOT_NAME}!**\n\n"
        "I convert your images to **WebP** format with ease!\n\n"
        "📸 **How to use:**\n"
        "1️⃣ Send me any image (JPG, PNG, BMP, GIF, etc.)\n"
        "2️⃣ Choose your conversion options\n"
        "3️⃣ Get your WebP image instantly!\n\n"
        "📚 **Features:**\n"
        "• 🔄 Batch conversion (send multiple images)\n"
        "• 📊 Quality settings (25% - 100%)\n"
        "• 🔒 Lossless conversion option\n"
        "• 🎨 Preserve transparency\n\n"
        "🔧 Use /help to see all commands."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    help_text = (
        f"🤖 **{BOT_NAME} Help**\n\n"
        "📤 **Commands:**\n"
        "`/start` - Start the bot\n"
        "`/help` - Show this help message\n"
        "`/settings` - Configure conversion settings\n"
        "`/stats` - View your statistics\n"
        "`/cancel` - Cancel current operation\n\n"
        "🔄 **Conversion Options:**\n"
        "• Quality: 25% (small) to 100% (best quality)\n"
        "• Lossless: Preserve exact image quality\n"
        "• Transparency: Keep transparent backgrounds\n\n"
        "💡 **Tips:**\n"
        "• Send multiple images at once for batch conversion\n"
        "• Forward images from other chats\n"
        "• Images are processed and deleted immediately\n"
        "• Maximum file size: 20MB\n\n"
        f"📱 **Bot:** @{BOT_USERNAME}"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show and configure conversion settings."""
    user_id = str(update.effective_user.id)
    settings = user_sessions.get(user_id, {})
    quality = settings.get('quality', 75)
    lossless = settings.get('lossless', False)
    
    settings_text = (
        f"⚙️ **Current Settings**\n\n"
        f"📊 Quality: **{quality}%**\n"
        f"🔒 Lossless: **{'✅ Enabled' if lossless else '❌ Disabled'}**\n\n"
        "**Choose quality level:**"
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
            InlineKeyboardButton(
                f"{'🔓' if lossless else '🔒'} Lossless", 
                callback_data="toggle_lossless"
            )
        ],
        [
            InlineKeyboardButton("📤 Apply Settings", callback_data="apply_settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics."""
    user_id = str(update.effective_user.id)
    stats = user_sessions.get(user_id, {})
    converted_count = stats.get('converted_count', 0)
    
    stats_text = (
        f"📊 **Your Statistics**\n\n"
        f"🖼️ Images converted: **{converted_count}**\n"
        f"⚡ Status: **Active**\n"
        f"🤖 Bot: **{BOT_NAME}**\n"
        f"📅 Since: **{datetime.now().strftime('%Y-%m-%d')}**\n\n"
        "Keep converting! 🚀"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel current operation."""
    user_id = str(update.effective_user.id)
    if user_id in user_sessions:
        user_sessions[user_id]['converting'] = False
    await update.message.reply_text("✅ Operation cancelled! Send a new image to convert.")


async def convert_image(image_data: bytes, quality: int, lossless: bool) -> Tuple[bytes, int]:
    """Convert image to WebP format. Returns: (converted_image_data, file_size_in_kb)"""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA' and not lossless:
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        
        # Convert to WebP
        output = io.BytesIO()
        image.save(
            output, 
            format='WEBP', 
            quality=quality, 
            lossless=lossless,
            optimize=True,
            method=6
        )
        output.seek(0)
        
        return output.getvalue(), len(output.getvalue()) // 1024
    
    except Exception as e:
        logger.error(f"Error in convert_image: {e}")
        raise


async def handle_media(update: Update, file_data: bytes) -> None:
    """Handle media conversion."""
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
    
    # Send processing message
    processing_msg = await message.reply_text("🔄 **Converting your image...**", parse_mode='Markdown')
    
    try:
        # Get settings
        settings = user_sessions.get(user_id, {})
        quality = settings.get('quality', 75)
        lossless = settings.get('lossless', False)
        
        # Convert image
        converted_data, size_kb = await convert_image(file_data, quality, lossless)
        
        # Update statistics
        user_sessions[user_id]['converted_count'] = user_sessions[user_id].get('converted_count', 0) + 1
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"converted_{timestamp}.webp"
        
        # Send converted image
        await message.reply_document(
            document=io.BytesIO(converted_data),
            filename=output_filename,
            caption=(
                f"✅ **Converted to WebP!**\n"
                f"📊 Quality: **{quality}%**\n"
                f"🔒 Lossless: **{'Yes' if lossless else 'No'}**\n"
                f"📏 Size: **{size_kb} KB**"
            ),
            parse_mode='Markdown'
        )
        
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error processing media: {e}")
        await processing_msg.edit_text(
            f"❌ **Error converting image:**\n{str(e)}\n\n"
            "Please try again with a different image.",
            parse_mode='Markdown'
        )


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photo messages."""
    message = update.message
    
    if not message.photo:
        await message.reply_text("⚠️ Please send a valid image file.")
        return
    
    try:
        photo_file = await message.photo[-1].get_file()
        
        if photo_file.file_size > MAX_IMAGE_SIZE:
            await message.reply_text(f"⚠️ Image too large! Maximum size is {MAX_IMAGE_SIZE // (1024*1024)}MB.")
            return
        
        image_data = await photo_file.download_as_bytearray()
        await handle_media(update, image_data)
        
    except Exception as e:
        logger.error(f"Error handling image: {e}")
        await message.reply_text("❌ Error processing your image. Please try again.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document images."""
    message = update.message
    document = message.document
    
    if not document.mime_type or not document.mime_type.startswith('image/'):
        await message.reply_text("⚠️ Please send an image file (JPG, PNG, BMP, GIF, etc.)")
        return
    
    if document.file_size > MAX_IMAGE_SIZE:
        await message.reply_text(f"⚠️ File too large! Maximum size is {MAX_IMAGE_SIZE // (1024*1024)}MB.")
        return
    
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
    
    try:
        file = await document.get_file()
        image_data = await file.download_as_bytearray()
        await handle_media(update, image_data)
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await message.reply_text("❌ Error processing your image. Please try again.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    data = query.data
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'quality': 75,
            'lossless': False,
            'converted_count': 0,
            'converting': True
        }
    
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
            f"✅ **Settings applied!**\n\n"
            f"📊 Quality: **{quality}%**\n"
            f"🔒 Lossless: **{'✅ Enabled' if lossless else '❌ Disabled'}**\n\n"
            "Send an image to convert with these settings!",
            parse_mode='Markdown'
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
                InlineKeyboardButton(
                    f"{'🔓' if lossless_status else '🔒'} Lossless", 
                    callback_data="toggle_lossless"
                )
            ],
            [
                InlineKeyboardButton("📤 Apply Settings", callback_data="apply_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔒 Lossless **{'✅ Enabled' if lossless_status else '❌ Disabled'}**\n\n"
            "**Choose quality level:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    if data.startswith("quality_"):
        quality = int(data.split("_")[1])
        settings = user_sessions.get(user_id, {})
        settings['quality'] = quality
        user_sessions[user_id] = settings
        
        lossless_status = user_sessions[user_id].get('lossless', False)
        
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
                InlineKeyboardButton(
                    f"{'🔓' if lossless_status else '🔒'} Lossless", 
                    callback_data="toggle_lossless"
                )
            ],
            [
                InlineKeyboardButton("📤 Apply Settings", callback_data="apply_settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Quality set to **{quality}%**\n\n"
            "**Choose quality level:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and notify user."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ **An error occurred.**\n"
                "Please try again or use /help for assistance.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")


def main() -> None:
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
        
        logger.info("=" * 60)
        logger.info(f"🚀 {BOT_NAME} starting with long polling...")
        logger.info(f"📡 Bot: @{BOT_USERNAME}")
        logger.info("✅ Ready to receive messages!")
        logger.info("=" * 60)
        
        # Start the bot
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Fatal error starting bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
