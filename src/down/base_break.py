import re

from src.system.load_save import load_data

def fallback_breaks(lines):
    cfg_data = load_data()
    ep = cfg_data.get("epub_data", cfg_data) if isinstance(cfg_data, dict) else {}
    b_conf = ep.get("body", ep) if isinstance(ep, dict) else {}
    transition_words = (
        "어느 날", "어느날", "그날", "다음 날", "다음날", "며칠 후", "며칠 뒤",
        "그 후", "잠시 후", "한편", "그때", "얼마 후", "얼마 뒤", "다음 순간", "그 순간",
    )
    back_start_marks = -1
    end = True
    end_in = True
    dialogue_context = False
    data = []
    for line in lines:
        cleaned = line.replace('「', '“').replace('」', '”').replace("｢","“").replace("｣","”").replace("<","〈").replace(">","〉").strip()
        if not cleaned:
            data.append(False)
            continue
        stripped_for_check = re.sub(r'\s+', '', cleaned)
        start = False
        if end and end_in:
            if cleaned[0] == '「' or cleaned[0] == '“' or cleaned[0] == '"' or cleaned[0] == "『":
                if back_start_marks == 1:
                    if b_conf.get("spacing_dialogue_continuous", False):
                        start = True
                elif back_start_marks == 3 and dialogue_context:
                    if b_conf.get("spacing_dialogue_continuous", False):
                        start = True
                else:
                    if b_conf.get("spacing_dialogue", True):
                        start = True
                if not ('」' in cleaned or '”' in cleaned or '"' in cleaned[1:] or "』" in cleaned):
                    end = False
                back_start_marks = 1
                dialogue_context = True
            elif cleaned[0] == "-" or cleaned[0] == "—" or cleaned[0] == "―":
                if back_start_marks != 2:
                    if b_conf.get("spacing_dash", True):
                        start = True
                back_start_marks = 2
                dialogue_context = False
            elif cleaned[0] == '(' or cleaned[0] =='（':
                if back_start_marks != 3:
                    if dialogue_context:
                        if b_conf.get("spacing_dialogue_parenthesis", False):
                            start = True
                    else:
                        if b_conf.get("spacing_parenthesis", True):
                            start = True
                if not (')' in cleaned or '）' in cleaned):
                    end_in = False
                back_start_marks = 3
            else:
                dialogue_context = False
                if cleaned[:1] in transition_words or cleaned[:2] in transition_words or cleaned[:3] in transition_words or cleaned[:4] in transition_words:
                    if b_conf.get("spacing_transition", True):
                        start = True
                if back_start_marks != 0:
                    if b_conf.get("spacing_general", True):
                        start = True
                back_start_marks = 0
        else:
            if not end:
                if '」' in cleaned or '”' in cleaned or '"' in cleaned or "』" in cleaned:
                    end = True
            if not end_in:
                if ')' in cleaned or '）' in cleaned:
                    end_in = True
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', cleaned)
        if re.fullmatch(r'''[^\w.\"'\'「」『』“”‘’!?。…]{1,}''', stripped_for_check):
            sep = b_conf.get("separator", {})
            start = sep.get("spacing", True) if isinstance(sep, dict) else False
            back_start_marks = -1
            dialogue_context = False
        data.append(start)
    return data