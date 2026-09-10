import os
import re
import unicodedata
from ahocorasick_rs import AhoCorasick, MatchKind
from google.genai import types

# 프로젝트 환경에 따라 get_resource_path import
try:
    from src.system.src import get_resource_path
except ImportError:
    def get_resource_path(p): return p


class FastPromptSanitizer:
    def __init__(self, dict_files=["Sexual.txt", "Offensive.txt"], custom_banned=None, whitelist=None):
        words = set()

        for fname in dict_files:
            path = get_resource_path(f"trans/txt/{fname}")
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    w = unicodedata.normalize("NFKC", line.strip())
                    if w and not w.startswith("#"):
                        words.add(w)

        default_danger_words = [
            "自傷", "自殺", "リスカ", "リストカット", "首吊り", "首吊る",
            "ロリコン", "おねショタ", "ショタおね", "レイプ", "強姦", "輪姦",
            "逆レイプ", "睡姦", "性奴隷", "屍姦", "獣姦", "食糞", "飲尿",
            "援助交際", "援交", "円光", "催眠", "エッチないたずら", "舐め回す"
        ]
        words.update([unicodedata.normalize("NFKC", w) for w in default_danger_words])

        if custom_banned:
            words.update([unicodedata.normalize("NFKC", w) for w in custom_banned])

        self.whitelist = set(whitelist) if whitelist else {
            "触る", "制服", "生徒", "ほっぺ", "太もも", "胸元", "ゴム"
        }
        filtered_words = [w for w in words if w and w not in self.whitelist]

        if not filtered_words:
            filtered_words = ["__DUMMY_KEYWORD__"]

        self.ac = AhoCorasick(filtered_words, matchkind=MatchKind.LeftmostLongest)

    def normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        return "".join(c for c in text if c not in ["\u200b", "\u200c", "\u200d", "\ufeff"])

    def censor_word(self, word: str) -> str:
        return "〇" * len(word)

    def sanitize(self, text: str) -> str:
        text = self.normalize(text)
        matches = self.ac.find_matches_as_indexes(text)
        if not matches:
            return text

        result = []
        last_idx = 0
        for _, start, end in matches:
            result.append(text[last_idx:start])
            bad_word = text[start:end]
            result.append(self.censor_word(bad_word))
            last_idx = end

        result.append(text[last_idx:])
        return "".join(result)

    def mask_with_placeholders(self, text: str):
        text = self.normalize(text)
        matches = self.ac.find_matches_as_indexes(text)
        if not matches:
            return text, {}

        result = []
        last_idx = 0
        mapping = {}
        for i, (_, start, end) in enumerate(matches):
            token = f"[T_{i}]"
            bad_word = text[start:end]
            mapping[token] = bad_word

            result.append(text[last_idx:start])
            result.append(token)
            last_idx = end

        result.append(text[last_idx:])
        return "".join(result), mapping


sanitizer = FastPromptSanitizer()

def x_making(text: str) -> str:
    return sanitizer.sanitize(text)

def get_safety_settings():
    return [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]