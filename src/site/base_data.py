EXPORT_TEXT = False
CONCURRENCY_LIMIT = 5
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,ko-KR;q=0.9,ko;q=0.8,en-US;q=0.7,en;q=0.6"
}

OUTFOLDER = "./out"

def set_start(data:dict):
    for n, d in data.items():
        exec(f"global {n}; {n} = {d if type(d) != str else f'"{d}"' }")
