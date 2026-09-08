import re
import unicodedata
from google.genai import types

class PromptSanitizer:
    def __init__(self):
        self.rules = [
            "いやらし[いくさ]",
            "エロ(?:い|チック|ティック)?",
            "スケベ(?:な|そう)?",
            "エッチ(?:な|する|した)?",
            "淫ら(?:な|に)?",
            "性的(?:な)?",
            "卑猥(?:な)?",
            "猥褻",
            "セックス(?:する|した)?",
            "本番",
            "3P",
            "起た(?:ない|なくて|つ|ち)",
            "大きくな(?:る|った|って)",
            "ゴム",
            "バイ〇グラ",
            "バイアグラ",
            "イチャイチャ",
            "一線越え(?:る|た)?",
            "浮気",
            "二股",
            "NTR",
            "押し倒(?:す|した|して|され)",
            "抱きしめ(?:る|た|て|返した)",
            "抱きつ(?:く|いた|いて|かれ)",
            "体を重ね(?:る|た|て)",
            "触(?:る|った|れて|れた)",
            "撫で(?:る|た|て)",
            "キス(?:した)?",
            "股間",
            "アレ",
            "胸元",
            "太もも",
            "裸体",
            "裸(?:の|で)?",
            "下半身",
            "ほっぺ",
            "高校(?:の|生)?",
            "理事長(?:室)?",
            "生徒",
            "制服",
            "無理やり",
            "強引(?:に|な)?",
            "襲(?:う|った|われ)",
            "奪(?:い返しても|った|い)",
            "騙(?:してる|して|す)",
            "告げ口",
            "脅迫",
            "自傷",
            "自殺",
            "リスカ",
            "首吊(?:り|る)",
            "殺(?:す|した|せ|そう)",
            "死ね",
        ]

        self.compiled = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.rules
        ]

    def normalize(self, text):
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

    def censor_match(self, match):
        word = match.group()

        if len(word) <= 2:
            return "〇" * len(word)

        return word[0] + "〇" * (len(word) - 1)

    def sanitize(self, text):
        text = self.normalize(text)

        for pattern in self.compiled:
            text = pattern.sub(self.censor_match, text)

        return text


_sanitizer = PromptSanitizer()


def x_making(text):
    return _sanitizer.sanitize(text)

def get_safety_settings():
    return [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
        ),
    ]