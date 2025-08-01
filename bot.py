import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and instructions"""
    await update.message.reply_text(
        "🌟 *Welcome to Quiz Bot!* 🌟\n\n"
        "I can turn your text files into interactive 10-second quizzes!\n\n"
        "🔹 Use /createquiz - Start quiz creation\n"
        "🔹 Use /help - Show formatting guide\n\n"
        "Let's make learning fun!",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed formatting instructions"""
    await update.message.reply_text(
        "📝 *Quiz File Format Guide:*\n\n"
        "```\n"
        "What is 2+2?\n"
        "A. 3\n"
        "B. 4\n"
        "C. 5\n"
        "D. 6\n"
        "Answer: 2\n\n"
        "Python is a...\n"
        "A. Snake\n"
        "B. Programming language\n"
        "C. Coffee brand\n"
        "D. Movie\n"
        "Answer: 2\n"
        "```\n\n"
        "📌 *Rules:*\n"
        "• One question per block (separated by blank lines)\n"
        "• Exactly 4 options (A, B, C, D)\n"
        "• Answer format: 'Answer: <1-4>' (1=A, 2=B, etc.)",
        parse_mode='Markdown'
    )

async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initiate quiz creation process"""
    await update.message.reply_text(
        "📤 *Ready to create your quiz!*\n\n"
        "Please send me a .txt file containing your questions.\n\n"
        "Need format help? Use /help",
        parse_mode='Markdown'
    )

def parse_quiz_file(content: str) -> tuple:
    """Parse and validate quiz content"""
    blocks = [b.strip() for b in content.split('\n\n') if b.strip()]
    valid_questions = []
    errors = []
    
    for i, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        # Basic validation
        if len(lines) < 6:
            errors.append(f"❌ Question {i}: Not enough lines (need 6, got {len(lines)})")
            continue
            
        question = lines[0]
        options = lines[1:5]
        answer_line = lines[5]
        
        # Validate options
        option_errors = []
        for idx, prefix in enumerate(['A', 'B', 'C', 'D']):
            if not options[idx].startswith(f"{prefix}."):
                option_errors.append(prefix)
        
        # Validate answer
        answer_error = None
        if not answer_line.lower().startswith('answer:'):
            answer_error = "Missing 'Answer:' prefix"
        else:
            try:
                answer_num = int(answer_line.split(':')[1].strip())
                if not 1 <= answer_num <= 4:
                    answer_error = f"Invalid answer number {answer_num}"
            except (ValueError, IndexError):
                answer_error = "Malformed answer line"
        
        # Compile errors or add valid question
        if option_errors or answer_error:
            error_parts = []
            if option_errors:
                error_parts.append(f"Bad options: {', '.join(option_errors)}")
            if answer_error:
                error_parts.append(answer_error)
            errors.append(f"❌ Q{i}: {'; '.join(error_parts)}")
        else:
            option_texts = [opt[2:].strip() for opt in options]
            correct_id = int(answer_line.split(':')[1].strip()) - 1
            valid_questions.append((question, option_texts, correct_id))
    
    return valid_questions, errors

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process uploaded quiz file"""
    if not update.message.document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please send a .txt file")
        return
    
    try:
        # Download file
        file = await context.bot.get_file(update.message.document.file_id)
        await file.download_to_drive('quiz.txt')
        
        with open('quiz.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse and validate
        valid_questions, errors = parse_quiz_file(content)
        
        # Report errors
        if errors:
            error_msg = "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n\n...and {len(errors)-5} more errors"
            await update.message.reply_text(
                f"⚠️ Found {len(errors)} error(s):\n\n{error_msg}"
            )
        
        # Send quizzes
        if valid_questions:
            await update.message.reply_text(
                f"✅ Sending {len(valid_questions)} quiz question(s)..."
            )
            for question, options, correct_id in valid_questions:
                try:
                    await context.bot.send_poll(
                        chat_id=update.effective_chat.id,
                        question=question,
                        options=options,
                        type='quiz',
                        correct_option_id=correct_id,
                        is_anonymous=False,
                        open_period=10,  # 10-second quiz
                        explanation="Check /help for formatting"
                    )
                except Exception as e:
                    logger.error(f"Poll send error: {str(e)}")
                    await update.message.reply_text("⚠️ Failed to send one quiz. Continuing...")
        else:
            await update.message.reply_text("❌ No valid questions found in file")
            
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        await update.message.reply_text("⚠️ Error processing file. Please check format and try again.")

def main() -> None:
    """Run the bot"""
    # Get token from environment
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("No TELEGRAM_TOKEN found in environment!")
        return
    
    # Create Application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("createquiz", create_quiz))
    application.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
    
    # Start polling
    logger.info("Starting bot in polling mode...")
    application.run_polling()

if __name__ == '__main__':
    main()
