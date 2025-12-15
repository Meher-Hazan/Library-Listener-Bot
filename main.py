import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from thefuzz import process, fuzz

# --- CONFIGURATION ---
BOT_TOKEN = "8431621681:AAEfrtw9mvHIazZaZUZtjWEGRoavXfmCisk"
DATA_URL = "https://raw.githubusercontent.com/Meher-Hazan/Darrusunnat-PDF-Library/main/books_data.json"
BOOK_NAME_KEY = "title"
BOOK_LINK_KEY = "link"

# --- LOGIC ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Fetch books once on startup to make it faster
# (Optional: You can move this inside the function if you update books often)
try:
    print("Fetching book database...")
    response = requests.get(DATA_URL)
    if response.status_code == 200:
        BOOKS_DB = response.json()
        print(f"Loaded {len(BOOKS_DB)} books.")
    else:
        BOOKS_DB = []
        print("Failed to load books.")
except Exception as e:
    BOOKS_DB = []
    print(f"Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Safety checks: ignore if no message or no text
    if not update.message or not update.message.text:
        return

    # 2. Get the user's message
    user_text = update.message.text

    # 3. Prepare titles for searching
    # We ignore books that have empty titles
    book_map = {b[BOOK_NAME_KEY]: b for b in BOOKS_DB if b.get(BOOK_NAME_KEY)}
    titles = list(book_map.keys())

    if not titles:
        return

    # 4. Smart Search (Token Set Ratio)
    # This scorer is best for finding a short string (book title) inside a longer string (user sentence).
    # Example: User says "Please upload Sahih Bukhari pdf" -> Matches "Sahih Bukhari" with score 100.
    result = process.extractOne(user_text, titles, scorer=fuzz.token_set_ratio)

    if result:
        best_match, score = result
        
        # CONFIDENCE CHECK:
        # We use a higher threshold (80-85) to prevent wrong answers if people are just chatting.
        if score > 82: 
            found_book = book_map[best_match]
            link = found_book.get(BOOK_LINK_KEY, "No link available")
            
            # Create a nice reply
            reply_text = (
                f"📚 **I found that book!**\n\n"
                f"📖 **Title:** {best_match}\n"
                f"🔗 [Click to Download]({link})"
            )
            
            # Reply to the specific message that asked for it
            await update.message.reply_markdown(
                reply_text,
                reply_to_message_id=update.message.message_id,
                disable_web_page_preview=False
            )

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Listen to ALL text messages in Groups (and Private)
    # We do NOT use filters.Command, so it reads natural chat
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(echo_handler)
    
    print("Bot is listening to all messages...")
    application.run_polling()
