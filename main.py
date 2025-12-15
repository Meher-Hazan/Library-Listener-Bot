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

# Fetch books on startup
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
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    
    # Ignore very short messages (prevents replying to "Hi", "Ok", "No")
    if len(user_text) < 4:
        return

    # Prepare titles
    book_map = {b[BOOK_NAME_KEY]: b for b in BOOKS_DB if b.get(BOOK_NAME_KEY)}
    titles = list(book_map.keys())
    
    if not titles:
        return

    # 1. SEARCH: Get the top 3 best matches
    # limit=3 means we get the top 3 candidates
    # scorer=fuzz.token_set_ratio is best for finding words inside sentences
    matches = process.extract(user_text, titles, scorer=fuzz.token_set_ratio, limit=3)

    # matches looks like: [('Book Name A', 95), ('Book Name B', 80), ...]
    best_match_name = matches[0][0]
    best_match_score = matches[0][1]

    # --- DECISION LOGIC ---

    # CASE A: Match is WEAK (Score < 65) -> Ignore completely
    if best_match_score < 65:
        return  # Bot stays silent

    # CASE B: Match is VERY STRONG (Score > 90) -> Send link immediately
    elif best_match_score > 90:
        book = book_map[best_match_name]
        link = book.get(BOOK_LINK_KEY, "No link")
        await update.message.reply_markdown(
            f"📚 **Found it!**\n\n📖 {best_match_name}\n🔗 [Download Here]({link})",
            reply_to_message_id=update.message.message_id
        )

    # CASE C: Match is AMBIGUOUS (Score 65-90) -> Show options
    # This happens if there are similar books or the user made a typo
    else:
        # Create a list of the top 3 books found
        reply_text = "📚 **I found a few similar books. Did you mean one of these?**\n\n"
        
        for name, score in matches:
            if score > 60:  # Only show relevant ones
                book = book_map[name]
                link = book.get(BOOK_LINK_KEY, "#")
                reply_text += f"🔹 [{name}]({link})\n"
        
        await update.message.reply_markdown(
            reply_text,
            reply_to_message_id=update.message.message_id,
            disable_web_page_preview=True
        )

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(echo_handler)
    application.run_polling()

