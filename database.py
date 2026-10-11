import os
import sqlite3

DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fsub_channels (
            channel TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value INTEGER DEFAULT 1
        )
    """)
    # Set default global pm_search_enabled to ON (1) if not exists
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('global_pm_search', 1)")
    conn.commit()
    conn.close()

def get_global_pm_search():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'global_pm_search'")
        row = cursor.fetchone()
        conn.close()
        if row is not None:
            return bool(row[0])
        return True
    except Exception:
        return True

def set_global_pm_search(enabled):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('global_pm_search', ?)", (1 if enabled else 0,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def add_user(user_id, first_name):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
        cursor.execute("UPDATE users SET first_name = ? WHERE user_id = ?", (first_name, user_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_all_users():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, first_name FROM users")
        users = cursor.fetchall()
        conn.close()
        return users
    except Exception:
        return []

def is_banned(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
        banned = cursor.fetchone() is not None
        conn.close()
        return banned
    except Exception:
        return False

def ban_user(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def unban_user(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_banned_users():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM banned_users")
        banned = [row[0] for row in cursor.fetchall()]
        conn.close()
        return banned
    except Exception:
        return []

def get_fsub_channels():
    env_channels = os.environ.get("FORCE_SUB_CHANNELS", "")
    channels = [ch.strip() for ch in env_channels.split(",") if ch.strip()]
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT channel FROM fsub_channels")
        db_channels = [row[0] for row in cursor.fetchall()]
        conn.close()
        for ch in db_channels:
            if ch not in channels:
                channels.append(ch)
    except Exception:
        pass
    return channels

def add_fsub_channel(channel):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO fsub_channels (channel) VALUES (?)", (channel,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def remove_fsub_channel(channel):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fsub_channels WHERE channel = ?", (channel,))
        conn.commit()
        conn.close()
    except Exception:
        pass
