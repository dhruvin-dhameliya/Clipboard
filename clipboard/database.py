import sqlite3
import os

HOME_DIR = os.path.expanduser("~")
DB_DIR = os.path.join(HOME_DIR, ".clipboard")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, ".clipboard.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clipboard (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL COLLATE NOCASE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_clipboard_item(content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO clipboard (content) VALUES (?)", (content,))
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM clipboard")
    item_count = cursor.fetchone()[0]
    
    if item_count > 30:
        cursor.execute("DELETE FROM clipboard WHERE id = (SELECT MIN(id) FROM clipboard)")
        conn.commit()

    conn.close()

def get_clipboard_items():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, content FROM clipboard ORDER BY timestamp DESC")
    items = cursor.fetchall()
    conn.close()
    return items

def clear_clipboard():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clipboard")
    conn.commit()
    conn.close()