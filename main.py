import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from thefuzz import process, fuzz

# --- CONFIGURATION ---
# WE DO NOT PASTE THE TOKEN HERE ANYMORE
# The bot will read it from Render's settings safely.
BOT_TOKEN = os.getenv("BOT_TOKEN") 

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

    user_text = update.message.text.lower().strip()
    
    # 1. SMART FILTER: Ignore short msg & common words
    if len(user_text) < 4:
        return

    # Prepare titles
    book_map = {b[BOOK_NAME_KEY]: b for b in BOOKS_DB if b.get(BOOK_NAME_KEY)}
    titles = list(book_map.keys())
    
    if not titles:
        return

    # 2. SMART SEARCH: Use token_sort_ratio 
    # This prevents matching "er" (of) to every book title.
    # It focuses on the unique words in the book title.
    matches = process.extract(user_text, titles, scorer=fuzz.token_sort_ratio, limit=5)

    # 3. STRICT FILTER: Only accept matches > 65% similarity
    valid_matches = [m for m in matches if m[1] > 65]

    if not valid_matches:
        return # Stay silent if it's just random chat

    # --- INTERACTIVE REPLY ---
    
    # A. Perfect Match (> 88%) -> Show Download Button
    best_match = valid_matches[0]
    if best_match[1] > 88:
        book = book_map[best_match[0]]
        link = book.get(BOOK_LINK_KEY, "#")
        
        keyboard = [[InlineKeyboardButton("📥 Download PDF", url=link)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Found it!**\n\n📖 {best_match[0]}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    # B. Close Match -> Show Options
    keyboard = []
    for name, score in valid_matches[:3]: # Top 3
        book = book_map[name]
        link = book.get(BOOK_LINK_KEY, "#")
        keyboard.append([InlineKeyboardButton(f"📖 {name}", url=link)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤔 **Did you mean one of these?**",
        reply_markup=reply_markup
    )

if __name__ == '__main__':
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing! Add it to Render Environment Variables.")
    else:
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        application.add_handler(echo_handler)
        print("Bot is secure and running...")
        application.run_polling()
