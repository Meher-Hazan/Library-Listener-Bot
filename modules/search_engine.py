import requests
import re
import random
from rapidfuzz import fuzz
from modules.config import DATA_URL, SYNONYMS, STOP_WORDS, KEY_TITLE

BOOKS_DB = []
SEARCH_INDEX = {}

CHAT_PHRASES = {
    "hi", "hello", "salam", "assalamu", "alaikum", "kemon", "acho", 
    "how", "are", "you", "good", "morning", "night", "bot", "admin", 
    "help", "info", "start", "ok", "thanks", "thank", "you", "bye", "boi"
}

# --- BANGLA STEMMER (Kept the advanced one) ---
def get_root_word(word):
    if len(word) < 4: return word
    suffixes = ["ের", "ার", "য়", "ে", "তে", "কে", "গুলো", "গুলা", "রা", "দের", "er", "ar", "te", "ke", "gulo", "gula", "'s"]
    for s in suffixes:
        if word.endswith(s):
            return word[:-len(s)]
    return word

def clean_query(text):
    if not text: return []
    text = text.lower()
    text = text.replace(".pdf", "").replace("_", " ").replace("-", " ")
    text = re.sub(r'[^\w\s\u0980-\u09FF]', '', text) 
    text = re.sub(r'\d+', '', text)    
    words = text.split()
    processed = []
    for w in words:
        if w in STOP_WORDS: continue
        if w in SYNONYMS: w = SYNONYMS[w]
        processed.append(get_root_word(w))
    return processed

def is_conversational(words):
    if not words: return True
    count = sum(1 for w in words if w in CHAT_PHRASES)
    return (count / len(words)) > 0.5

# --- DATABASE MANAGEMENT ---
def refresh_database():
    """Downloads new books from GitHub"""
    global BOOKS_DB, SEARCH_INDEX
    try:
        # Add a random query param to bypass cache
        url = f"{DATA_URL}?t={random.randint(1, 10000)}"
        resp = requests.get(url)
        
        if resp.status_code == 200:
            new_db = resp.json()
            new_index = {}
            for book in new_db:
                raw_title = book.get(KEY_TITLE, "")
                clean_words = clean_query(raw_title)
                if clean_words:
                    new_index[raw_title] = {"words": set(clean_words), "data": book}
            
            # Atomic Update (Prevents bot from being empty during update)
            BOOKS_DB = new_db
            SEARCH_INDEX = new_index
            print(f"✅ Database Refreshed: {len(BOOKS_DB)} books.")
            return True
        else:
            print(f"❌ Database update failed: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return False

def count_books():
    return len(BOOKS_DB)

def get_random_book():
    if not BOOKS_DB: return None
    return random.choice(BOOKS_DB)

def search_book(user_sentence):
    query_words = clean_query(user_sentence)
    if not query_words or is_conversational(query_words): return []

    query_set = set(query_words)
    matches = []

    for raw_title, info in SEARCH_INDEX.items():
        book_words = info["words"]
        common = query_set.intersection(book_words)
        if not common: continue

        coverage = len(common) / len(query_set)
        if (len(query_set) == 1 and coverage == 1.0) or (len(query_set) > 1 and coverage >= 0.5):
            fuzz_score = fuzz.partial_ratio(" ".join(query_words), " ".join(book_words))
            final_score = (coverage * 100) + (fuzz_score * 0.2)
            matches.append({"book": info["data"], "score": final_score, "coverage": coverage})

    matches.sort(key=lambda x: x["score"], reverse=True)
    
    # Tier 1: Perfect Matches
    perfect = [m["book"] for m in matches if m["coverage"] == 1.0]
    if perfect: return perfect
    
    # Tier 2: Partial Matches
    return [m["book"] for m in matches[:20]]