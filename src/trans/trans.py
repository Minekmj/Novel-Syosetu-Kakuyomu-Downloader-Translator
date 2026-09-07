import requests

session = requests.Session()

session.headers.update({
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://papago.naver.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
})

def Translator(text):
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
                translated_text = (
                    data.get("message", {})
                    .get("result", {})
                    .get("translatedText")
                )
            return translated_text
        else:
            print(f"요청 실패 (상태 코드: {response.status_code})")
            print("응답 내용:", response.text)
            return "error"

    except Exception as e:
        print(f"에러 발생: {e}")
        return "error"