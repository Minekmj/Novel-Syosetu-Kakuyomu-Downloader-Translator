import sqlite3
import requests

DB_FILE = "./trans.db"
session = requests.Session()
session.headers.update({
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://papago.naver.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
})

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                src_text TEXT PRIMARY KEY,
                dst_text TEXT
            )
        """)
init_db()

def get_cached(text):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT dst_text FROM translations WHERE src_text = ?", (text,))
        row = cur.fetchone()
        return row[0] if row else None

def set_cached(src_text, dst_text):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT OR REPLACE INTO translations VALUES (?, ?)", (src_text, dst_text))

def Translator(text, cache=False):
    if cache:
        cached = get_cached(text)
        if cached:
            return cached

    url = "https://papago.naver.com/api/text/translation"
    payload = {
        "source": "ja",
        "target": "ko",
        "text": text,
        "dict": "true",
        "useGlossary": "false",
        "honorific": "false",
        "dictDisplay": "30",
    }

    try:
        response = session.post(url, data=payload)
        if response.status_code == 200:
            data = response.json()
            translated_text = data.get("translatedText")
            if not translated_text and "message" in data:
                translated_text = data.get("message", {}).get("result", {}).get("translatedText")
            
            if translated_text:
                if cache:
                    set_cached(text, translated_text)
                return translated_text
        return "error"
    except Exception as e:
        print(f"에러 발생: {e}")
        return "error"