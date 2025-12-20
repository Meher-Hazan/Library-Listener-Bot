import logging
import threading
import time
import requests
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, CommandHandler, InlineQueryHandler, filters

# IMPORT MODULES
from modules import config, admin_police, search_engine, stats

# --- GLOBAL MEMORY ---
USER_SEARCHES = {} 

# --- SERVER & KEEP ALIVE ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.wfile.write(b"Bot Active")

def start_server(): HTTPServer(("0.0.0.0", 8080), SimpleHandler).serve_forever()

def keep_alive():
    while True:
        time.sleep(600)
        try: requests.get(config.RENDER_URL)
        except: pass

# --- HELPER: PAGINATION ---
def get_pagination_keyboard(results, page, total_pages):
    kb = []
    start = page * 5
    current_books = results[start:start+5]
    
    for book in current_books:
        title = book.get("title", "Book")[:30] + ('..' if len(book.get("title", "")) > 30 else '')
        kb.append([InlineKeyboardButton(f"📖 {title}", url=book.get("link", "#"))])
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}"))
    
    kb.append(nav)
    return InlineKeyboardMarkup(kb)

# --- HANDLERS ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Police & Logging
    stats.log_user(update.effective_user.id)
    if await admin_police.check_and_moderate(update, context): return 
    if not update.message or not update.message.text: return

    # 2. Search
    user_text = update.message.text
    stats.log_search(user_text) # Log for analytics
    matches = search_engine.search_book(user_text)

    # 3. No Matches -> Request Button
    if not matches:
        kb = [[InlineKeyboardButton("📝 Request to Admin", callback_data=f"req_{user_text[:20]}")]]
        await update.message.reply_text(
            f"❌ **No books found for '{user_text}'.**\nWant to request it?",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown"
        )
        return

    # 4. Matches -> Pagination
    USER_SEARCHES[update.effective_user.id] = matches
    total_pages = (len(matches) + 4) // 5
    keyboard = get_pagination_keyboard(matches, 0, total_pages)
    
    await update.message.reply_text(
        f"🔍 **Found {len(matches)} books matching '{user_text}':**",
        reply_markup=keyboard, parse_mode="Markdown"
    )

# --- BUTTON HANDLER (Next/Prev + Requests) ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # HANDLE REQUESTS
    if data.startswith("req_"):
        book_name = data.split("req_")[1]
        await query.edit_message_text(f"✅ **Request Sent!**\nAdmin notified for: `{book_name}`")
        
        # Send to Admin
        admin_msg = (f"🔔 **New Book Request!**\n👤 {query.from_user.mention_html()}\n📖 `{book_name}`")
        try: await context.bot.send_message(chat_id=config.ADMIN_ID, text=admin_msg, parse_mode="HTML")
        except: pass
        return

    # HANDLE PAGINATION
    if data == "ignore": return
    if "page_" in data:
        user_id = update.effective_user.id
        if user_id not in USER_SEARCHES:
            await query.edit_message_text("⚠️ **Session expired. Search again.**")
            return
        
        new_page = int(data.split("_")[1])
        matches = USER_SEARCHES[user_id]
        total_pages = (len(matches) + 4) // 5
        await query.edit_message_reply_markup(reply_markup=get_pagination_keyboard(matches, new_page, total_pages))

# --- INLINE SEARCH (Viral Feature) ---
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query: return
    
    results = search_engine.search_book(query)[:10] # Top 10 for inline
    articles = []
    
    for book in results:
        title = book.get("title", "Book")
        link = book.get("link", "#")
        
        articles.append(InlineQueryResultArticle(
            id=str(uuid4()),
            title=title,
            description="Click to send PDF link",
            input_message_content=InputTextMessageContent(f"📖 **{title}**\n🔗 [Download PDF]({link})", parse_mode="Markdown")
        ))
    
    await update.inline_query.answer(articles)

# --- ADMIN COMMANDS ---
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID: return
    await update.message.reply_text(stats.get_stats(), parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID: return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("⚠️ Usage: `/broadcast Hello everyone!`")
        return
    
    users = stats.get_all_users()
    count = 0
    await update.message.reply_text(f"📢 Sending to {len(users)} users...")
    
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **Announcement:**\n\n{msg}", parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05) # Prevent flood limits
        except: pass
        
    await update.message.reply_text(f"✅ Broadcast complete. Sent to {count} users.")

# --- JOB: BOOK OF THE DAY ---
async def send_daily_book(context: ContextTypes.DEFAULT_TYPE):
    book = search_engine.get_random_book()
    if not book: return
    
    msg = (f"📅 **Book of the Day**\n\n📖 **{book['title']}**\n\n🔗 [Read Now]({book['link']})")
    
    # Send to Group (if set) and Admin
    try: await context.bot.send_message(chat_id=config.GROUP_ID, text=msg, parse_mode="Markdown")
    except: pass

# --- MAIN ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    search_engine.refresh_database()
    
    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    
    if config.BOT_TOKEN:
        app = ApplicationBuilder().token(config.BOT_TOKEN).build()
        
        # Handlers
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(InlineQueryHandler(inline_query))
        
        # Admin Commands
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CommandHandler("broadcast", broadcast_command))
        
        # Daily Job (Every 24 Hours)
        if app.job_queue:
            app.job_queue.run_repeating(send_daily_book, interval=86400, first=10)
        
        print("Ultimate Bot Live...")
        app.run_polling()
    else:
        print("Error: BOT_TOKEN is missing.")