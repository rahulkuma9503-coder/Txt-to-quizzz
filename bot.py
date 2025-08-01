import os
import logging
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext
)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "🌟 Welcome to Quiz Bot! 🌟\n\n"
        "I turn text files into interactive quizzes!\n\n"
        "🔹 Use /createquiz to start making quizzes\n"
        "🔹 Use /help for formatting instructions\n\n"
        "Let's create some fun quizzes together!"
    )

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "📝 Quiz File Format:\n\n"
        "What is 2+2?\n"
        "A. 3\n"
        "B. 4\n"
        "C. 5\n"
        "D. 6\n"
        "Answer: 2\n\n"
        "Rules:\n"
        "• Separate questions with blank lines\n"
        "• Exactly 4 options (A, B, C, D)\n"
        "• Answer format: 'Answer: <1-4>'"
    )

def create_quiz(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "📤 Ready to create a quiz!\n\n"
        "Please send me a .txt file with your quiz questions.\n\n"
        "Need format help? Use /help"
    )

def parse_quiz_file(content: str):
    blocks = [b.strip() for b in content.split('\n\n') if b.strip()]
    valid_questions = []
    errors = []
    
    for i, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        # Validate block structure
        if len(lines) < 6:
            errors.append(f"❌ Question {i}: Insufficient lines (expected 6, got {len(lines)})")
            continue
        
        question = lines[0]
        options = lines[1:5]
        answer_line = lines[5]
        
        # Validate options format
        option_errors = []
        for j, prefix in enumerate(['A', 'B', 'C', 'D']):
            if not options[j].startswith(f"{prefix}."):
                option_errors.append(f"Option {prefix} missing/invalid")
        
        # Validate answer format
        answer_error = None
        if not answer_line.lower().startswith('answer:'):
            answer_error = "Answer line missing"
        else:
            try:
                answer_num = int(answer_line.split(':')[1].strip())
                if not (1 <= answer_num <= 4):
                    answer_error = f"Invalid answer number ({answer_num})"
            except (ValueError, IndexError):
                answer_error = "Answer format invalid"
        
        # Collect errors or add valid question
        if option_errors or answer_error:
            error_msgs = []
            if option_errors:
                error_msgs.append(" | ".join(option_errors))
            if answer_error:
                error_msgs.append(answer_error)
            errors.append(f"❌ Question {i}: {'; '.join(error_msgs)}")
        else:
            # Extract option texts
            option_texts = [opt[2:].strip() for opt in options]
            # Convert answer to 0-based index
            correct_id = int(answer_line.split(':')[1].strip()) - 1
            valid_questions.append((question, option_texts, correct_id))
    
    return valid_questions, errors

def handle_document(update: Update, context: CallbackContext) -> None:
    document = update.message.document
    
    # Validate file type
    if not document.file_name.endswith('.txt'):
        update.message.reply_text("❌ Please send a .txt file")
        return
    
    # Download file
    file = context.bot.get_file(document.file_id)
    file.download('quiz.txt')
    
    try:
        with open('quiz.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse and validate
        valid_questions, errors = parse_quiz_file(content)
        
        # Report errors
        if errors:
            error_msg = "\n".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                error_msg += f"\n\n...and {len(errors) - 5} more errors"
            update.message.reply_text(f"⚠️ Found {len(errors)} error(s):\n\n{error_msg}")
        
        # Send valid quizzes
        if valid_questions:
            update.message.reply_text(f"✅ Sending {len(valid_questions)} quiz question(s)...")
            for question, options, correct_id in valid_questions:
                try:
                    context.bot.send_poll(
                        chat_id=update.effective_chat.id,
                        question=question,
                        options=options,
                        type='quiz',
                        correct_option_id=correct_id,
                        is_anonymous=False,
                        open_period=10  # Quiz lasts 10 seconds
                    )
                except Exception as e:
                    logger.error(f"Failed to send poll: {e}")
                    update.message.reply_text("⚠️ Failed to send one quiz. Continuing...")
        else:
            update.message.reply_text("❌ No valid questions found in file")
            
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        update.message.reply_text("⚠️ Error processing file. Please check format and try again.")

def main() -> None:
    # Get token from environment variable
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        return
    
    # Create bot
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("createquiz", create_quiz))
    dispatcher.add_handler(MessageHandler(Filters.document, handle_document))
    
    # Start polling
    updater.start_polling()
    logger.info("Bot is running...")
    updater.idle()

if __name__ == '__main__':
    main()
