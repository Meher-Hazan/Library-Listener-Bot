import ujson
import os
from modules import config

# Initialize Files
if not os.path.exists(config.USERS_FILE):
    with open(config.USERS_FILE, 'w') as f: ujson.dump([], f)

if not os.path.exists(config.STATS_FILE):
    with open(config.STATS_FILE, 'w') as f: ujson.dump({"searches": 0, "top_terms": {}}, f)

def log_user(user_id):
    """Saves User ID so we can broadcast to them later"""
    try:
        with open(config.USERS_FILE, 'r') as f: users = ujson.load(f)
        if user_id not in users:
            users.append(user_id)
            with open(config.USERS_FILE, 'w') as f: ujson.dump(users, f)
    except: pass

def get_all_users():
    """Returns list of all user IDs"""
    try:
        with open(config.USERS_FILE, 'r') as f: return ujson.load(f)
    except: return []

def log_search(term):
    """Tracks what people search for"""
    if len(term) < 3: return
    try:
        with open(config.STATS_FILE, 'r') as f: data = ujson.load(f)
        data["searches"] += 1
        data["top_terms"][term] = data["top_terms"].get(term, 0) + 1
        with open(config.STATS_FILE, 'w') as f: ujson.dump(data, f)
    except: pass

def get_stats():
    """Returns formatted stats string"""
    try:
        with open(config.USERS_FILE, 'r') as f: users = len(ujson.load(f))
        with open(config.STATS_FILE, 'r') as f: data = ujson.load(f)
        
        # Sort top searches
        top = sorted(data["top_terms"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_str = "\n".join([f"• {k}: {v}" for k,v in top])
        
        return (
            f"📊 **Bot Statistics**\n\n"
            f"👥 Total Users: `{users}`\n"
            f"🔎 Total Searches: `{data['searches']}`\n\n"
            f"🔥 **Top Searches:**\n{top_str}"
        )
    except: return "No stats available yet."