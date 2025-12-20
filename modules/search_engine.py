import requests
import re
from rapidfuzz import fuzz
from modules.config import DATA_URL, SYNONYMS, STOP_WORDS

BOOKS_DB = []
SEARCH_INDEX = {}

# Words to ignore in "Conversational Check"
CHAT_PHRASES = {
    "hi", "hello", "salam", "assalamu", "alaikum", "kemon", "acho", 
    "how", "are", "you", "good", "morning", "night", "bot", "admin", 
    "help", "info", "start", "ok", "thanks", "thank", "you", "bye", "boi"
}

# --- COMPLEX CODING: THE BANGLA STEMMER ---
def get_root_word(word):
    """
    Intelligent Stemmer: Removes suffixes from Bangla & Banglish words
    so 'Imaner' matches 'Iman'.
    """
    if len(word) < 4: return word # Don't cut short words
    
    # 1. BANGLA SCRIPT SUFFIXES (The most common ones)
    # ের (er), ার (ar), য় (y), ে (e), তে (te), কে (ke), গুলো (gulo), রা (ra)
    bangla_suffixes = ["ের", "ার", "য়", "ে", "তে", "কে", "গুলো", "গুলা", "রা", "দের"]
    
    for suffix in bangla_suffixes:
        if word.endswith(suffix):
            return word[:-len(suffix)] # Chop it off

    # 2. BANGLISH (Phonetic) SUFFIXES
    # er, ar, te, ke, gulo, gula
    english_suffixes = ["er", "ar", "te", "ke", "gulo", "gula", "'s"]
    
    for suffix in english_suffixes:
        if word.endswith(suffix):
            # Only chop if the remaining word is still valid length
            root = word[:-len(suffix)]
            if len(root) > 2: 
                return root
            
    return word

def clean_query(text):
    if not text: return []
    text = text.lower()
    
    # Clean noise
    text = text.replace(".pdf", "").replace("_", " ").replace("-", " ")
    text = re.sub(r'[^\w\s\u0980-\u09FF]', '', text) # Keep English + Bangla Unicode
    text = re.sub(r'\d+', '', text)    
    
    words = text.split()
    processed_words = []
    
    for w in words:
        if w in STOP_WORDS: continue
        
        # 1. Apply Synonym (Biography -> Jiboni)
        if w in SYNONYMS: w = SYNONYMS[w]
        
        # 2. Apply Stemmer (Imaner -> Iman)
        root = get_root_word(w)
        processed_words.append(root)
            
    return processed_words

def is_conversational(words):
    if not words: return True
    # If more than 50% of words are chat phrases, ignore
    chat_count = sum(1 for w in words if w in CHAT_PHRASES)
    return (chat_count / len(words)) > 0.5

def refresh_database():
    global BOOKS_DB, SEARCH_INDEX
    try:
        resp = requests.get(DATA_URL)
        if resp.status_code == 200:
            BOOKS_DB = resp.json()
            SEARCH_INDEX = {}
            for book in BOOKS_DB:
                raw_title = book.get("title", "")
                
                # INDEXING STRATEGY:
                # We store the "Root Words" of the book title.
                # Book: "Imaner Shakhaprosakha" -> Index: {"iman", "shakhaprosakha"}
                clean_words = clean_query(raw_title)
                
                if clean_words:
                    SEARCH_INDEX[raw_title] = {
                        "words": set(clean_words), 
                        "data": book
                    }
            print(f"Database Updated: {len(SEARCH_INDEX)} books indexed with Stemming.")
        else: print("Database update failed.")
    except Exception as e: print(f"DB Error: {e}")

def search_book(user_sentence):
    # 1. Get Root Words from User Query
    # User: "Imaner boi dao" -> Cleaner -> "Iman" (boi/dao removed, er removed)
    query_words = clean_query(user_sentence)
    
    if not query_words or is_conversational(query_words):
        return []

    query_set = set(query_words)
    matches = []

    for raw_title, info in SEARCH_INDEX.items():
        book_words = info["words"]
        
        # 2. KEYWORD INTERSECTION
        # Now we compare Root vs Root. "Iman" == "Iman".
        common_words = query_set.intersection(book_words)
        
        if not common_words: continue

        # Scoring Logic
        matched_count = len(common_words)
        total_query = len(query_set)
        
        # Coverage: Did we find the main words the user asked for?
        coverage_score = matched_count / total_query
        
        # STRICT RULE: Must match at least 50% of keywords
        # Exception: If query is 1 word, must match 100%
        if (total_query == 1 and coverage_score == 1.0) or (total_query > 1 and coverage_score >= 0.5):
            
            # Tie-Breaker: RapidFuzz Partial Ratio on the full title
            # This helps rank "Sahih Bukhari" higher than "Bukhari History" if user typed "Sahih Bukhari"
            fuzz_score = fuzz.partial_ratio(" ".join(query_words), " ".join(book_words))
            
            final_score = (coverage_score * 100) + (fuzz_score * 0.2)
            
            matches.append({
                "book": info["data"],
                "score": final_score,
                "coverage": coverage_score
            })

    # 3. SORT & FILTER
    matches.sort(key=lambda x: x["score"], reverse=True)

    # If we have perfect keyword matches, show only those
    perfect_matches = [m["book"] for m in matches if m["coverage"] == 1.0]
    if perfect_matches:
        return perfect_matches
    
    # Otherwise return top partials
    return [m["book"] for m in matches[:20]]

def get_random_book():
    import random
    if not BOOKS_DB: return None
    return random.choice(BOOKS_DB)