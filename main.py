import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, filters
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
except Exception as e:
    BOOKS_DB = []
    print(f"Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.lower() # Convert to lowercase for better matching
    
    # IGNORE very short messages (e.g. "hi", "salam", "ok")
    if len(user_text) < 4:
        return

    # Prepare titles
    book_map = {b[BOOK_NAME_KEY]: b for b in BOOKS_DB if b.get(BOOK_NAME_KEY)}
    titles = list(book_map.keys())
    
    if not titles:
        return

    # --- SEARCH ALGORITHM ---
    # We get top 3 matches. 
    # scorer=fuzz.token_set_ratio is good for "partial" matches (finding book name inside a sentence)
    matches = process.extract(user_text, titles, scorer=fuzz.token_set_ratio, limit=5)

    # Filter out bad matches (Keep only score > 75)
    valid_matches = [m for m in matches if m[1] > 75]

    # IF NO GOOD MATCHES FOUND:
    if not valid_matches:
        # We generally stay silent so we don't annoy the group.
        # But if the user EXPLICITLY asked "book", maybe reply? 
        # For now: Silence is golden in groups.
        return 

    # IF EXACT MATCH FOUND (Score > 90):
    best_match = valid_matches[0]
    if best_match[1] > 90:
        book = book_map[best_match[0]]
        link = book.get(BOOK_LINK_KEY, "#")
        
        # Create a "Download" button
        keyboard = [[InlineKeyboardButton("📥 Download PDF", url=link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📖 **{best_match[0]}**\n\nI found this book for you!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    # IF AMBIGUOUS MATCHES (Score 75-90):
    # Send a list of buttons so the user can choose
    keyboard = []
    for name, score in valid_matches[:3]: # limit to top 3
        book = book_map[name]
        link = book.get(BOOK_LINK_KEY, "#")
        # Add a button for each book found
        keyboard.append([InlineKeyboardButton(f"📖 {name}", url=link)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 **I found a few books similar to your request:**",
        reply_markup=reply_markup
    )

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handle text messages
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(echo_handler)
    
    application.run_polling()
