import os

# --- SECURITY ---
BOT_TOKEN = os.getenv("BOT_TOKEN") 
DATA_URL = "https://raw.githubusercontent.com/Meher-Hazan/Darrusunnat-PDF-Library/main/books_data.json"
RENDER_URL = "https://library-bot-amuk.onrender.com" # REPLACE WITH YOUR URL

# --- ADMIN SETTINGS ---
# 1. Get your ID from @userinfobot
ADMIN_ID = 1280989150  
# 2. Get your Group ID (Type /id in your group) - Used for Daily Book
GROUP_ID = -1001585388329 

# --- FILES ---
STATS_FILE = "stats.json"
USERS_FILE = "user_database.json"

# --- LOGIC SETTINGS ---
SYNONYMS = {
    "biography": "jiboni", "history": "itihas", "prayer": "namaz",
    "fasting": "roza", "prophet": "nabi", "messenger": "rasul",
    "life": "jibon", "rules": "masala", "dream": "shopno",
    "women": "nari", "paradise": "jannat", "hell": "jahannam",
    "vol": "khondo", "part": "part"
}

BAD_WORDS = [
    "scam", "bitcoin", "investment", "crypto", "sex", "porn", "xxx", 
    "fucker", "bitch", "whore", "asshole", "casino", "betting",
    "কুত্তা", "হারামি", "সোনা", "বাল", "চুদ", "খানকি", "মাগি"
]

STOP_WORDS = {
    "pdf", "book", "link", "download", "dao", "chai", "plz", "admin", "er", "ar", "boi", 
    "the", "please", "give", "me", "koto", "dam", "ace", "ase", "ki",
    "বই", "এর", "পিডিএফ", "লিংক", "দাও", "চাই", "আছে", "কি", "সাহায্য", "করুন", "ভাই", "প্লিজ"
}