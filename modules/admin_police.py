import re
import unicodedata
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
import datetime
from modules.config import BAD_WORDS

LINK_PATTERN = r"(t\.me\/|telegram\.me\/)"

def normalize_text(text):
    if not text: return ""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower()

async def check_and_moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return False
    clean_text = normalize_text(update.message.text)
    should_ban = False

    for word in BAD_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', clean_text):
            should_ban = True; break

    if re.search(LINK_PATTERN, clean_text): should_ban = True

    if should_ban:
        try:
            await update.message.delete()
            user = update.message.from_user
            chat_member = await context.bot.get_chat_member(update.message.chat_id, user.id)
            if chat_member.status not in ["administrator", "creator"]:
                perms = ChatPermissions(can_send_messages=False)
                until = datetime.datetime.now() + datetime.timedelta(hours=24)
                await context.bot.restrict_chat_member(update.message.chat_id, user.id, perms, until_date=until)
            return True
        except: pass
    return False