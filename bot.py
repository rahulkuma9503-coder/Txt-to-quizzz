import os
import logging
import threading
import time
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from pymongo import MongoClient
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
bot_start_time = time.time()
BOT_VERSION = "5.1"

class HealthCheckHandler(BaseHTTPRequestHandler):
    # ... (existing HealthCheckHandler remains unchanged) ...

def run_http_server(port=8080):
    # ... (existing run_http_server remains unchanged) ...

# MongoDB connection function
def get_db():
    try:
        client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'))
        return client.telegram_bot
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        return None

# Record user interaction
async def record_user_interaction(update: Update):
    db = get_db()
    if not db:
        return
        
    user = update.effective_user
    if not user:
        return
        
    users = db.users
    user_data = {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "last_interaction": datetime.utcnow()
    }
    
    try:
        users.update_one(
            {"user_id": user.id},
            {"$set": user_data},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await record_user_interaction(update)
    # ... (existing start function remains unchanged) ...

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await record_user_interaction(update)
    # ... (existing help_command remains unchanged) ...

async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await record_user_interaction(update)
    # ... (existing create_quiz remains unchanged) ...

def parse_quiz_file(content: str) -> tuple:
    # ... (existing parse_quiz_file remains unchanged) ...

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await record_user_interaction(update)
    # ... (existing handle_document remains unchanged) ...

# New stats command
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await record_user_interaction(update)
    
    # Check if user is owner
    owner_id = os.getenv('OWNER_ID')
    if not owner_id or str(update.effective_user.id) != owner_id:
        await update.message.reply_text("🚫 This command is only available to the bot owner.")
        return

    db = get_db()
    if not db:
        await update.message.reply_text("⚠️ Database connection error. Stats unavailable.")
        return
        
    try:
        # Calculate stats
        users = db.users
        total_users = users.count_documents({})
        
        # Ping calculation
        start_time = time.time()
        ping_msg = await update.message.reply_text("🏓 Pong!")
        ping_time = (time.time() - start_time) * 1000
        
        # Uptime calculation
        uptime_seconds = int(time.time() - bot_start_time)
        uptime = str(timedelta(seconds=uptime_seconds))
        
        # Format stats message
        stats_message = (
            f"📊 *Bot Statistics*\n\n"
            f"• Total Users: `{total_users}`\n"
            f"• Current Ping: `{ping_time:.2f} ms`\n"
            f"• Uptime: `{uptime}`\n"
            f"• Version: `{BOT_VERSION}`\n\n"
            f"_Updated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_"
        )
        
        # Edit the ping message with full stats
        await ping_msg.edit_text(stats_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Stats command error: {e}")
        await update.message.reply_text("⚠️ Error retrieving statistics. Please try again later.")

# New broadcast command
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await record_user_interaction(update)
    
    # Check if user is owner
    owner_id = os.getenv('OWNER_ID')
    if not owner_id or str(update.effective_user.id) != owner_id:
        await update.message.reply_text("🚫 This command is only available to the bot owner.")
        return
        
    # Check if message text exists
    if not context.args:
        await update.message.reply_text(
            "📢 Usage: /broadcast <message>\n\n"
            "Example: /broadcast We've added new features! Use /help to learn more."
        )
        return
        
    db = get_db()
    if not db:
        await update.message.reply_text("⚠️ Database connection error. Broadcast unavailable.")
        return
        
    try:
        users = db.users
        user_ids = [user["user_id"] for user in users.find({}, {"user_id": 1})]
        total_users = len(user_ids)
        broadcast_text = " ".join(context.args)
        
        if not user_ids:
            await update.message.reply_text("⚠️ No users found in database.")
            return
            
        confirmation = await update.message.reply_text(
            f"⚠️ *Broadcast Confirmation*\n\n"
            f"Recipients: `{total_users}` users\n\n"
            f"Message:\n{broadcast_text}\n\n"
            f"Type /confirm_broadcast to send or /cancel to abort.",
            parse_mode='Markdown'
        )
        
        # Store broadcast data in context for confirmation
        context.user_data["broadcast_data"] = {
            "text": broadcast_text,
            "user_ids": user_ids,
            "confirmation_msg_id": confirmation.message_id
        }
        
    except Exception as e:
        logger.error(f"Broadcast preparation error: {e}")
        await update.message.reply_text("⚠️ Error preparing broadcast. Please try again later.")

# Broadcast confirmation handler
async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await record_user_interaction(update)
    
    # Check if user is owner
    owner_id = os.getenv('OWNER_ID')
    if not owner_id or str(update.effective_user.id) != owner_id:
        return
        
    broadcast_data = context.user_data.get("broadcast_data")
    if not broadcast_data:
        await update.message.reply_text("⚠️ No pending broadcast. Start with /broadcast.")
        return
        
    try:
        user_ids = broadcast_data["user_ids"]
        broadcast_text = broadcast_data["text"]
        total_users = len(user_ids)
        
        status_msg = await update.message.reply_text(
            f"📤 Broadcasting to {total_users} users...\n\n"
            f"0/{total_users} (0%)"
        )
        
        success = 0
        failed = 0
        
        # Send messages with rate limiting
        for i, user_id in enumerate(user_ids):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=broadcast_text
                )
                success += 1
            except Exception as e:
                logger.warning(f"Broadcast failed for {user_id}: {str(e)}")
                failed += 1
                
            # Update progress every 10 messages or last message
            if (i + 1) % 10 == 0 or (i + 1) == total_users:
                percent = (i + 1) * 100 // total_users
                await status_msg.edit_text(
                    f"📤 Broadcasting to {total_users} users...\n\n"
                    f"{i+1}/{total_users} ({percent}%)\n"
                    f"✅ Success: {success} | ❌ Failed: {failed}"
                )
                time.sleep(0.5)  # Rate limiting
        
        # Final status report
        await status_msg.edit_text(
            f"✅ *Broadcast Complete!*\n\n"
            f"• Total recipients: `{total_users}`\n"
            f"• Successfully sent: `{success}`\n"
            f"• Failed: `{failed}`\n\n"
            f"Message:\n{broadcast_text}",
            parse_mode='Markdown'
        )
        
        # Cleanup
        del context.user_data["broadcast_data"]
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text("⚠️ Error during broadcast. Operation aborted.")

# Broadcast cancellation handler
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await record_user_interaction(update)
    
    # Check if user is owner
    owner_id = os.getenv('OWNER_ID')
    if not owner_id or str(update.effective_user.id) != owner_id:
        return
        
    if "broadcast_data" in context.user_data:
        del context.user_data["broadcast_data"]
        await update.message.reply_text("✅ Broadcast canceled.")
    else:
        await update.message.reply_text("ℹ️ No pending broadcast to cancel.")

def main() -> None:
    # ... (existing main function code until token check) ...
    
    # Create Telegram application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("createquiz", create_quiz))
    application.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
    
    # Add new command handlers
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("confirm_broadcast", confirm_broadcast))
    application.add_handler(CommandHandler("cancel", cancel_broadcast))
    
    # ... (rest of main function remains unchanged) ...

if __name__ == '__main__':
    main()
