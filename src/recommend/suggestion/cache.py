import sqlite3
from src.system.config import DB_FILE_WORKED

def init_db():
    with sqlite3.connect(DB_FILE_WORKED) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS WorkDataCache (
                src_text TEXT PRIMARY KEY,
                dst_text TEXT
            )
        """)

init_db()

def get_cached(text):
    with sqlite3.connect(DB_FILE_WORKED) as conn:
        cur = conn.cursor()
        cur.execute("SELECT dst_text FROM WorkDataCache WHERE src_text = ?", (text,))
        row = cur.fetchone()
        return row[0] if row else None

def set_cached(src_text, dst_text):
    with sqlite3.connect(DB_FILE_WORKED) as conn:
        conn.execute("INSERT OR REPLACE INTO WorkDataCache VALUES (?, ?)", (src_text, dst_text))