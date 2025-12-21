import logging
import threading
import time
import requests
import asyncio
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, CommandHandler, InlineQueryHandler, filters

# IMPORT MODULES
from modules import config, admin_police, search_engine, stats

# --- MEMORY ---
USER_SEARCHES = {} 

# --- SERVER ---
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

# --- HELPERS ---
def escape_markdown(text):
    if not text: return ""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", r"\\\1", text)

def get_pagination_keyboard(results, page, total_pages):
    kb = []
    start = page * 5
    current_books = results[start:start+5]
    for book in current_books:
        title = book.get(config.KEY_TITLE, "Book")
        if len(title) > 30: title = title[:28] + ".."
        kb.append([InlineKeyboardButton(f"📖 {title}", url=book.get(config.KEY_LINK, "#"))])
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1: nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    kb.append(nav)
    return InlineKeyboardMarkup(kb)

# --- HANDLERS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats.log_user(update.effective_user.id)
    await update.message.reply_text(f"👋 **Hello!**\nI am updated with {search_engine.count_books()} books.\nType a name to search!", parse_mode="Markdown")

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually update the book list"""
    if update.effective_user.id != config.ADMIN_ID: return
    
    await update.message.reply_text("🔄 **Updating Database...**")
    success = search_engine.refresh_database()
    
    if success:
        count = search_engine.count_books()
        await update.message.reply_text(f"✅ **Update Complete!**\nTotal Books: {count}")
    else:
        await update.message.reply_text("❌ **Update Failed.** Check logs.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats.log_user(update.effective_user.id)
    if await admin_police.check_and_moderate(update, context): return 
    if not update.message or not update.message.text: return

    user_text = update.message.text
    matches = search_engine.search_book(user_text)

    if not matches:
        kb = [[InlineKeyboardButton("📝 Request Book", callback_data=f"req_{user_text[:20]}")]]
        await update.message.reply_text(f"❌ **No result for '{user_text}'.**\nRequest it?", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    USER_SEARCHES[update.effective_user.id] = matches
    total_pages = (len(matches) + 4) // 5
    await update.message.reply_text(f"🔍 **Found {len(matches)} books:**", reply_markup=get_pagination_keyboard(matches, 0, total_pages), parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    
    data = query.data
    if data.startswith("req_"):
        book_name = data.split("req_")[1]
        await query.edit_message_text(f"✅ **Request Sent!**")
        try: await context.bot.send_message(chat_id=config.ADMIN_ID, text=f"🔔 **Request:**\n📖 `{book_name}`", parse_mode="Markdown")
        except: pass
        return

    if "page_" in data:
        user_id = update.effective_user.id
        if user_id not in USER_SEARCHES:
            await query.edit_message_text("⚠️ **Session Expired.** Search again.")
            return
        new_page = int(data.split("_")[1])
        matches = USER_SEARCHES[user_id]
        total_pages = (len(matches) + 4) // 5
        try: await query.edit_message_reply_markup(reply_markup=get_pagination_keyboard(matches, new_page, total_pages))
        except: pass

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query or len(query) < 2: return
    results = search_engine.search_book(query)[:10]
    articles = []
    for book in results:
        title = escape_markdown(book.get(config.KEY_TITLE, "Book"))
        link = book.get(config.KEY_LINK, "#")
        articles.append(InlineQueryResultArticle(
            id=str(uuid4()), title=title, description="Click to send PDF",
            input_message_content=InputTextMessageContent(f"📖 *{title}*\n🔗 [Download PDF]({link})", parse_mode="MarkdownV2")
        ))
    await update.inline_query.answer(articles, cache_time=10)

# --- BROADCAST (Now supports Images) ---
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID: return

    # Check if admin is replying to a photo
    is_photo = False
    photo_id = None
    msg_text = " ".join(context.args)

    if update.message.reply_to_message:
        if update.message.reply_to_message.photo:
            is_photo = True
            photo_id = update.message.reply_to_message.photo[-1].file_id
            # Use caption if text not provided
            if not msg_text:
                msg_text = update.message.reply_to_message.caption or ""

    if not msg_text and not is_photo:
        await update.message.reply_text("⚠️ Usage: `/broadcast Message` OR Reply to a photo with `/broadcast`")
        return

    users = stats.get_all_users()
    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    count = 0
    for uid in users:
        try:
            if is_photo:
                await context.bot.send_photo(chat_id=uid, photo=photo_id, caption=msg_text, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=uid, text=f"📢 **Announcement:**\n\n{msg_text}", parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await update.message.reply_text(f"✅ Sent to {count} users.")

# --- AUTOMATION JOBS ---

# 1. Database Auto-Updater (Every 30 mins)
async def auto_update_db(context: ContextTypes.DEFAULT_TYPE):
    search_engine.refresh_database()

# 2. Random Book (Every 4 Hours)
async def send_random_book(context: ContextTypes.DEFAULT_TYPE):
    book = search_engine.get_random_book()
    if not book: return
    
    title = escape_markdown(book.get(config.KEY_TITLE, "Book"))
    link = book.get(config.KEY_LINK, "#")
    image = book.get(config.KEY_IMAGE) # Get Image URL if exists

    caption = f"✨ **Random Pick**\n\n📖 *{title}*\n\n🔗 [Read Now]({link})"

    try:
        if image and "http" in image:
            # Send Photo if valid image link exists
            await context.bot.send_photo(chat_id=config.GROUP_ID, photo=image, caption=caption, parse_mode="MarkdownV2")
        else:
            # Send Text only
            await context.bot.send_message(chat_id=config.GROUP_ID, text=caption, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"Daily Book Error: {e}")

# --- MAIN ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    search_engine.refresh_database() # Initial Load
    
    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    
    if config.BOT_TOKEN:
        app = ApplicationBuilder().token(config.BOT_TOKEN).build()
        
        # Commands & Messages
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("refresh", refresh_command)) # <--- NEW
        app.add_handler(CommandHandler("broadcast", broadcast_command))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(InlineQueryHandler(inline_query))
        
        # Job Queue (Timers)
        if app.job_queue:
            # Random Book every 4 hours (14400s)
            app.job_queue.run_repeating(send_random_book, interval=config.RANDOM_BOOK_INTERVAL, first=10)
            # Update DB every 30 mins (1800s)
            app.job_queue.run_repeating(auto_update_db, interval=config.DB_REFRESH_INTERVAL, first=1800)
        
        print("🚀 Ultimate Bot Started...")
        app.run_polling()
    else:
        print("Error: BOT_TOKEN missing")