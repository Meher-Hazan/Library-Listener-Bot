import os

# --- SECURITY ---
BOT_TOKEN = os.getenv("BOT_TOKEN") 
DATA_URL = "https://raw.githubusercontent.com/Meher-Hazan/Darrusunnat-PDF-Library/main/books_data.json"
RENDER_URL = "https://library-bot-amuk.onrender.com" 

# --- SETTINGS ---
ADMIN_ID = 123456789  # <--- REPLACE WITH YOUR NUMERIC ID
GROUP_ID = -1001234567890 # <--- REPLACE WITH YOUR GROUP ID

# TIMERS (In Seconds)
# 4 Hours = 14400 seconds
RANDOM_BOOK_INTERVAL = 14400 
# Check for new books every 30 minutes
DB_REFRESH_INTERVAL = 1800

# JSON KEYS (What your database uses)
KEY_TITLE = "title"
KEY_LINK = "link"
KEY_IMAGE = "image" # <--- New Key for Pictures

# --- FILES ---
STATS_FILE = "stats.json"
USERS_FILE = "user_database.json"

# --- LOGIC ---
SYNONYMS = {
    "biography": "jiboni", "history": "itihas", "prayer": "namaz",
    "fasting": "roza", "prophet": "nabi", "messenger": "rasul",
    "life": "jibon", "rules": "masala", "dream": "shopno",
    "women": "nari", "paradise": "jannat", "hell": "jahannam"
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