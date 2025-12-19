import logging
import threading
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, filters

# IMPORT MODULES
from modules import config, admin_police, search_engine

# --- GLOBAL MEMORY (To store search results for pagination) ---
USER_SEARCHES = {} 

# --- SERVER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Bot Active")

def start_server():
    HTTPServer(("0.0.0.0", 8080), SimpleHandler).serve_forever()

def keep_alive():
    while True:
        time.sleep(600)
        try: requests.get(config.RENDER_URL)
        except: pass

# --- HELPER: KEYBOARD GENERATOR ---
def get_pagination_keyboard(results, page, total_pages):
    """Creates the list of books + Next/Prev buttons"""
    kb = []
    
    # 1. Determine which books to show (5 per page)
    start = page * 5
    end = start + 5
    current_books = results[start:end]
    
    # 2. Add Book Buttons
    for book in current_books:
        title = book.get("title", "Book")
        # Truncate title to keep it clean
        display = (title[:30] + '..') if len(title) > 30 else title
        link = book.get("link", "#")
        kb.append([InlineKeyboardButton(f"📖 {display}", url=link)])
    
    # 3. Add Navigation Buttons ( < 1/5 > )
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{page-1}"))
    
    nav_row.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
        
    kb.append(nav_row)
    return InlineKeyboardMarkup(kb)

# --- HANDLERS ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. POLICE CHECK
    if await admin_police.check_and_moderate(update, context): return 
    if not update.message or not update.message.text: return

    # 2. SEARCH
    user_text = update.message.text
    matches = search_engine.search_book(user_text)

    if not matches:
        return # Silent if no match (or add a "Not found" message if you prefer)

    # 3. SAVE RESULTS TO MEMORY
    user_id = update.effective_user.id
    USER_SEARCHES[user_id] = matches
    
    # 4. SHOW PAGE 0 (First 5 results)
    total_matches = len(matches)
    total_pages = (total_matches + 4) // 5 # Calculate pages needed
    
    keyboard = get_pagination_keyboard(matches, 0, total_pages)
    
    await update.message.reply_text(
        f"🔍 **Found {total_matches} books matching your request:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the Next/Prev buttons"""
    query = update.callback_query
    await query.answer() # Stop the loading animation
    
    data = query.data
    if data == "ignore": return

    # Parse request (e.g., "page_2")
    user_id = update.effective_user.id
    
    # Check if we have results for this user in memory
    if user_id not in USER_SEARCHES:
        await query.edit_message_text("⚠️ **Session expired. Please search again.**", parse_mode="Markdown")
        return

    # Calculate new page
    new_page = int(data.split("_")[1])
    matches = USER_SEARCHES[user_id]
    total_pages = (len(matches) + 4) // 5
    
    # Generate new buttons
    new_keyboard = get_pagination_keyboard(matches, new_page, total_pages)
    
    # Edit the message
    await query.edit_message_reply_markup(reply_markup=new_keyboard)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    search_engine.refresh_database()
    
    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    
    if config.BOT_TOKEN:
        app = ApplicationBuilder().token(config.BOT_TOKEN).build()
        
        # Add Handlers
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.add_handler(CallbackQueryHandler(handle_callback)) # <--- NEW HANDLER FOR BUTTONS
        
        print("Einstein Bot with Infinite Scrolling is Live...")
        app.run_polling()
    else:
        print("Error: BOT_TOKEN is missing.")
