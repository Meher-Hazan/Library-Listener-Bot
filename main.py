import logging
import os
import requests
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from thefuzz import process, fuzz

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN") 
DATA_URL = "https://raw.githubusercontent.com/Meher-Hazan/Darrusunnat-PDF-Library/main/books_data.json"
BOOK_NAME_KEY = "title"
BOOK_LINK_KEY = "link"

# --- PART 1: THE FAKE WEB SERVER (Fixes Render Timeout) ---
# This tricks Render into thinking we are a website so it doesn't kill the bot.
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_web_server():
    # Render assigns a port automatically in the environment variable "PORT"
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    print(f"Fake Web Server listening on port {port}")
    server.serve_forever()

# --- PART 2: BOT LOGIC ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# GLOBAL VARIABLES
BOOKS_DB = []
SEARCH_INDEX = {} 

def normalize_text(text):
    """
    MASTER CLEANER: Removes numbers, underscores, extensions, and Bangla junk words.
    """
    if not text: return ""
    text = text.lower()
    text = text.replace(".pdf", "")
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r'\d+', '', text) # Remove numbers
    
    stop_words = [
        "pdf", "book", "link", "download", "dao", "chai", "plz", "admin", "er",
        "বই", "এর", "পিডিএফ", "লিংক", "দাও", "চাই", "আছে", "কি", "সাহায্য", "করুন", "ভাই", "প্লিজ"
    ]
    for word in stop_words:
        text = re.sub(r'\b' + word + r'\b', '', text)
    
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Fetch and Index Books
try:
    print("Fetching and Indexing Library...")
    response = requests.get(DATA_URL)
    if response.status_code == 200:
        BOOKS_DB = response.json()
        SEARCH_INDEX = {}
        for book in BOOKS_DB:
            raw_title = book.get(BOOK_NAME_KEY, "")
            clean_title = normalize_text(raw_title)
            if clean_title:
                SEARCH_INDEX[clean_title] = book
        print(f"Indexed {len(SEARCH_INDEX)} books.")
    else:
        print("Failed to load books.")
except Exception as e:
    print(f"Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    cleaned_query = normalize_text(user_text)
    
    if len(cleaned_query) < 2:
        return

    clean_titles = list(SEARCH_INDEX.keys())
    if not clean_titles:
        return

    matches = process.extract(cleaned_query, clean_titles, scorer=fuzz.WRatio, limit=5)
    valid_matches = [m for m in matches if m[1] > 75]

    if not valid_matches:
        return 

    # SMART REPLY
    best_clean_name, best_score = valid_matches[0]
    best_book_obj = SEARCH_INDEX[best_clean_name]
    real_title = best_book_obj.get(BOOK_NAME_KEY, "Unknown Title")
    link = best_book_obj.get(BOOK_LINK_KEY, "#")

    if best_score > 90:
        keyboard = [[InlineKeyboardButton("📥 Download PDF", url=link)]]
        await update.message.reply_text(
            f"✅ **বইটি খুঁজে পেয়েছি!**\n\n📖 {real_title}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    keyboard = []
    for clean_name, score in valid_matches[:3]:
        if score > (best_score - 10): 
            book_obj = SEARCH_INDEX[clean_name]
            r_title = book_obj.get(BOOK_NAME_KEY, "Book")
            r_link = book_obj.get(BOOK_LINK_KEY, "#")
            btn_text = (r_title[:30] + '..') if len(r_title) > 30 else r_title
            keyboard.append([InlineKeyboardButton(f"📖 {btn_text}", url=r_link)])

    if keyboard:
        await update.message.reply_text(
            f"🔍 **আপনি কি এই বইগুলোর একটি খুঁজছেন?**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

if __name__ == '__main__':
    # 1. Start the Fake Web Server in the background
    threading.Thread(target=start_web_server, daemon=True).start()
    
    # 2. Check for Token and Start Bot
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing! Check Render Environment Variables.")
    else:
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        application.add_handler(echo_handler)
        print("Bot Started...")
        application.run_polling()
