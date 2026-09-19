from datetime import datetime, timedelta, timezone
import re


EXPORT_TEXT = False
CONCURRENCY_LIMIT = 5
CONCURRENCY_LIMIT_H = 15
DELAY = 0.1
DELAY_H = 2.8
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ja,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

OUTFOLDER = "./out"

def normalize_date(date_str):
    if not date_str:
        return None
    
    date_str = date_str.strip()
    jst = timezone(timedelta(hours=9))

    if "T" in date_str:
        try:
            clean_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(jst)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    m = re.search(r"(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})(?:日)?(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?", date_str)
    if m:
        year, month, day = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        hour = m.group(4).zfill(2) if m.group(4) else "00"
        minute = m.group(5).zfill(2) if m.group(5) else "00"
        second = m.group(6).zfill(2) if m.group(6) else "00"
        return f"{year}-{month}-{day} {hour}:{minute}:{second}"

    return date_str