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
BOT_VERSION = "5.2"  # Updated version

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Health check server handler"""
    server_version = "TelegramQuizBot/5.2"
    
    def do_GET(self):
        try:
            # [Previous health check implementation remains the same]
            pass
        except Exception as e:
            logger.error(f"Health check error: {e}")
            self.send_error(500)

def get_db():
    """Get MongoDB database connection"""
    try:
        client = MongoClient(os.getenv('MONGO_URI'))
        client.admin.command('ping')
        return client.telegram_bot
    except Exception as e:
        logger.error(f"MongoDB error: {e}")
        return None

async def record_user_interaction(update: Update):
    """Record user activity in database"""
    try:
        db = get_db()
        if db is None:
            return
            
        user = update.effective_user
        if not user:
            return
            
        db.users.update_one(
            {"user_id": user.id},
            {"$set": {
                "username": user.username,
                "last_interaction": datetime.utcnow()
            }},
            upsert=True
        )
    except Exception as e:
        logger.error(f"User recording error: {e}")

# [Previous command handlers (start, help, createquiz) remain the same]

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate broadcast by replying to a message"""
    await record_user_interaction(update)
    
    # Owner check
    if str(update.effective_user.id) != os.getenv('OWNER_ID'):
        await update.message.reply_text("🚫 Owner only command")
        return
        
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "📢 Reply to a message with /broadcast to send it to all users\n"
            "Then confirm with /confirm_broadcast",
            reply_to_message_id=update.message.message_id
        )
        return
        
    replied_msg = update.message.reply_to_message
    broadcast_text = replied_msg.text or replied_msg.caption
    
    if not broadcast_text:
        await update.message.reply_text("⚠️ Only text messages can be broadcasted")
        return
        
    db = get_db()
    if db is None:
        await update.message.reply_text("⚠️ Database unavailable")
        return
        
    try:
        user_ids = [u["user_id"] for u in db.users.find({}, {"user_id": 1})]
        if not user_ids:
            await update.message.reply_text("⚠️ No users in database")
            return
            
        context.user_data["broadcast_data"] = {
            "text": broadcast_text,
            "user_ids": user_ids,
            "original_msg_id": replied_msg.message_id
        }
        
        await update.message.reply_text(
            f"⚠️ Confirm broadcast to {len(user_ids)} users?\n"
            f"Message: {broadcast_text[:200]}...\n\n"
            f"Type /confirm_broadcast to send or /cancel to abort",
            reply_to_message_id=replied_msg.message_id
        )
    except Exception as e:
        logger.error(f"Broadcast setup error: {e}")
        await update.message.reply_text("⚠️ Broadcast setup failed")

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute the broadcast"""
    await record_user_interaction(update)
    
    if str(update.effective_user.id) != os.getenv('OWNER_ID'):
        return
        
    data = context.user_data.get("broadcast_data")
    if not data:
        await update.message.reply_text("⚠️ No pending broadcast")
        return
        
    try:
        status_msg = await update.message.reply_text(
            f"📤 Broadcasting to {len(data['user_ids'])} users...\n0 sent"
        )
        
        success = 0
        for i, user_id in enumerate(data['user_ids'], 1):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=data['text']
                )
                success += 1
                
                if i % 10 == 0:
                    await status_msg.edit_text(
                        f"📤 Broadcasting...\n{success} sent"
                    )
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Broadcast failed for {user_id}: {e}")
                
        await status_msg.edit_text(
            f"✅ Broadcast complete!\n"
            f"• Success: {success}\n"
            f"• Failed: {len(data['user_ids']) - success}"
        )
        del context.user_data["broadcast_data"]
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text("⚠️ Broadcast failed")

# [Rest of the handlers and main function remain the same]

def main():
    """Start the bot"""
    PORT = int(os.getenv('PORT', 10000))
    
    # Start health server
    threading.Thread(
        target=run_http_server,
        args=(PORT,),
        daemon=True
    ).start()
    
    # Create bot application
    application = Application.builder() \
        .token(os.getenv('TELEGRAM_TOKEN')) \
        .build()
    
    # Add handlers
    handlers = [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("createquiz", create_quiz),
        CommandHandler("broadcast", broadcast_command),
        CommandHandler("confirm_broadcast", confirm_broadcast),
        MessageHandler(filters.Document.TEXT, handle_document)
    ]
    for handler in handlers:
        application.add_handler(handler)
    
    # Start polling
    application.run_polling()

if __name__ == '__main__':
    main()