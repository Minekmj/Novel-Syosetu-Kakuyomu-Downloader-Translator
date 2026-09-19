import os
import re
import random
import unicodedata
from ahocorasick_rs import AhoCorasick, MatchKind
from google.genai import types
from src.trans.trans import Translator

try:
    from src.system.src import get_resource_path
except ImportError:
    def get_resource_path(*p): return p


class FastPromptSanitizer:
    def __init__(self, dict_files=["Sexual.txt", "Offensive.txt"], custom_banned=None, whitelist=None):
        words = set()
        for fname in dict_files:
            path = get_resource_path(f"trans/txt/{fname}")
            if os.path.exists(path):
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

        words.update(unicodedata.normalize("NFKC", w) for w in default_danger_words)

        if custom_banned:
            words.update(unicodedata.normalize("NFKC", w) for w in custom_banned)

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

    def _get_matches(self, text: str):
        return self.ac.find_matches_as_indexes(text)

    def sanitize(self, text: str) -> str:
        text = self.normalize(text)
        matches = self._get_matches(text)
        if not matches:
            return text

        result = []
        last_idx = 0

        for _, start, end in matches:
            result.append(text[last_idx:start])
            result.append(self.censor_word(text[start:end]))
            last_idx = end

        result.append(text[last_idx:])
        return "".join(result)

    def _translate_papago(self, text, papago):
        if not papago or not text:
            return None
        try:
            return Translator(text, True)
        except Exception:
            return None

    def make_statrt_stain(self, text: str, shuffle=True, extract_mode="word", papago=False):
        text = self.normalize(text)

        if extract_mode not in ("word", "sentence"):
            raise ValueError("extract_mode는 'word' 또는 'sentence'만 사용할 수 있습니다.")

        if not text:
            return {"data": [], "censor": [], "mode": extract_mode, "layout": []}, ""

        censor_data = {
            "data": [],
            "censor": [],
            "mode": extract_mode,
            "layout": [] 
        }

        raw_lines = text.splitlines()
        changed_items = []
        next_id = 0

        for raw_line in raw_lines:
            line = re.sub(r"[\r\n]+", "", raw_line).strip()

            if not line:
                censor_data["layout"].append(("empty", ""))
                continue

            line_id = next_id
            next_id += 1
            censor_data["layout"].append(("content", line_id))

            matches = self._get_matches(line)
            
            if extract_mode == "word":
                censor_data["data"].append(line_id)
                result = []
                last_idx = 0

                for _, start, end in matches:
                    result.append(line[last_idx:start])

                    word_id = next_id
                    next_id += 1
                    original = line[start:end]
                    token = f"{{{{data={word_id}}}}}"

                    censor_data["censor"].append({
                        "id": word_id,
                        "type": "word",
                        "original": original,
                        "translated": self._translate_papago(original, papago) if papago else None,
                        "papago": bool(papago),
                        "line_id": line_id
                    })

                    result.append(token)
                    last_idx = end

                result.append(line[last_idx:])
                processed_line = "".join(result)
                changed_items.append((line_id, f"<data={line_id}>{processed_line}"))

            else:
                if matches:
                    censor_data["censor"].append({
                        "id": line_id,
                        "type": "sentence",
                        "original": line,
                        "translated": self._translate_papago(line, papago) if papago else None,
                        "papago": bool(papago)
                    })
                else:
                    censor_data["data"].append(line_id)
                    changed_items.append((line_id, f"<data={line_id}>{line}"))

        if shuffle:
            random.shuffle(changed_items)

        changed_text = "\n".join(item for _, item in changed_items)
        return censor_data, changed_text

    def check_statrt_stain(self, censor_data, translated_text):
        if not isinstance(censor_data, dict):
            return False, "censor_data 형식이 올바르지 않습니다."

        if not isinstance(translated_text, str):
            return False, "번역 결과가 문자열이 아닙니다."

        expected_data = censor_data.get("data", [])
        expected_set = set(int(x) for x in expected_data)

        line_matches = re.findall(r"<data=(\d+)>", translated_text)
        word_matches = re.findall(r"\{\{data=(\d+)\}\}", translated_text)

        found_line_set = set(int(x) for x in line_matches)
        found_word_set = set(int(x) for x in word_matches)
        found_all = found_line_set | found_word_set

        missing_ids = expected_set - found_all
        if missing_ids:
            return False, f"태그가 번역 결과에서 누락되었습니다: data={sorted(missing_ids)}"

        return True, ""

    def prepare_for_ratio_check(self, translated_text, censor_data):
        if not translated_text:
            return ""

        lines = translated_text.splitlines()
        pure_ai_lines = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = re.match(r"^<data=(\d+)>(.*)$", line_str)
            if match:
                content = match.group(2).strip()
                if content:
                    clean_content = re.sub(r"\{\{data=\d+\}\}", "", content).strip()
                    if clean_content:
                        pure_ai_lines.append(clean_content)
            else:
                pure_ai_lines.append(line_str)

        return "\n".join(pure_ai_lines)

    def assemble_final_text(self, translated_text, censor_data, use_translated=False):
        if not translated_text or not isinstance(censor_data, dict):
            return translated_text

        mode = censor_data.get("mode", "word")
        layout = censor_data.get("layout", [])
        censor_list = censor_data.get("censor", [])
        censor_map = {int(item["id"]): item for item in censor_list if isinstance(item, dict) and "id" in item}

        lines = translated_text.splitlines()
        ai_translated_map = {}
        unindexed = []
        current_id = None

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            match = re.match(r"^<data=(\d+)>(.*)$", line_str)
            if match:
                current_id = int(match.group(1))
                content = match.group(2).strip()
                if current_id not in ai_translated_map:
                    ai_translated_map[current_id] = []
                if content:
                    ai_translated_map[current_id].append(content)
            else:
                if current_id is not None:
                    ai_translated_map[current_id].append(line_str)
                else:
                    unindexed.append(line_str)

        restored_lines = []

        for item_type, val in layout:
            if item_type == "empty":
                restored_lines.append("")
            else:
                line_id = val
                if mode == "sentence" and line_id in censor_map:
                    item = censor_map[line_id]
                    if use_translated and item.get("translated"):
                        restored_lines.append(item["translated"])
                    else:
                        restored_lines.append(item["original"])
                elif line_id in ai_translated_map:
                    restored_lines.append(" ".join(ai_translated_map[line_id]))

        restored_lines.extend(unindexed)
        final_text = "\n".join(restored_lines)

        if mode == "word":
            def replace_word(match):
                data_id = int(match.group(1))
                item = censor_map.get(data_id)
                if not item:
                    return match.group(0)
                if use_translated and item.get("translated"):
                    return item["translated"]
                return item["original"]

            final_text = re.sub(r"\{\{data=(\d+)\}\}", replace_word, final_text)

        final_text = re.sub(r"<data=\d+>", "", final_text)
        return final_text


sanitizer = FastPromptSanitizer()


def x_making(text: str) -> str:
    return sanitizer.sanitize(text)


def make_statrt_stain(text: str, shuffle=True, extract_mode="word", papago=False):
    return sanitizer.make_statrt_stain(text, shuffle=shuffle, extract_mode=extract_mode, papago=papago)


def check_statrt_stain(censor_data, translated_text):
    return sanitizer.check_statrt_stain(censor_data, translated_text)


def prepare_for_ratio_check(translated_text, censor_data):
    return sanitizer.prepare_for_ratio_check(translated_text, censor_data)


def assemble_final_text(translated_text, censor_data, use_translated=False):
    return sanitizer.assemble_final_text(translated_text, censor_data, use_translated=use_translated)


def get_safety_settings():
    return [
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    ]