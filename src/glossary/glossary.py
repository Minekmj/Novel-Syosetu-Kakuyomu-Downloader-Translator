import math
import re
import time
import heapq

SENTENCE_TIMEOUT_MS = 10000.0
TIME_CHECK_MASK = 1023
SECTION_COUNT = 20

_OPEN_TO_CLOSE = {
    "「": "」",
    "『": "』",
    "（": "）",
    "(": ")",
    "【": "】",
    "《": "》",
    "〈": "〉",
    "“": "”",
    '"': '"',
}
_CLOSE_CHARS = set(_OPEN_TO_CLOSE.values())
_SENTENCE_END = {".", "!", "?", "。", "！", "？"}

_RE_BRACKET_TERM = re.compile(r"[『【《〈≪]([^』】》〉≫\r\n]{2,20})[』】》〉≫]")
_RE_DOT_TERM = re.compile(r"[一-龠々ヶァ-ヶーA-Za-z0-9]+(?:・[一-龠々ヶァ-ヶーA-Za-z0-9]+)+")
_RE_KATA_TERM = re.compile(r"[ァ-ヶー]{2,}")
_RE_KANJI_TERM = re.compile(r"[一-龠々ヶ]{2,12}")
_RE_ALPHA_RANK = re.compile(r"(?:[A-Z]{2,}[0-9]*|[A-Za-z0-9]+級|[Ll][Vv]\.?\s*[0-9]+)")

_SAMPLE_STOPWORDS = {
    "自分", "彼女", "言葉", "時間", "気持ち", "本当", "大丈夫", "一番", "一緒",
    "全然", "突然", "最初", "最後", "場所", "理由", "意味", "方法", "状態",
    "様子", "視線", "笑顔", "表情", "声音", "空気", "空間", "存在", "能力",
    "関係", "問題", "結果", "状況", "記憶", "意識", "感覚", "想像", "確認",
    "説明", "納得", "理解", "反応", "質問", "返事", "会話", "約束", "準備",
    "行動", "移動", "到着", "出発", "開始", "終了", "成功", "失敗", "無理",
    "必要", "可能", "普通", "特別", "当然", "実際", "絶対", "完全", "一応",
    "少し", "沢山", "色々", "今日", "昨日", "明日", "毎日", "今回", "次回",
    "前回", "最近", "現在", "過去", "未来", "午前", "午後", "部屋", "天井",
    "地面", "景色", "太陽", "相手", "他人", "仲間", "家族", "両親", "母親",
    "父親", "先生", "先輩", "後輩", "友達", "子供", "大人", "男性", "女性",
    "少年", "少女", "青年", "物語", "小説", "人間", "世界", "学校", "学園",
    "教室", "自宅", "玄関", "窓辺", "階段", "廊下", "屋根", "建物", "生活",
    "日常", "瞬間", "程度", "以上", "以下", "以外", "以内", "途中", "以前",
    "以後", "同時", "早速", "結局", "適当", "テレビ", "スマホ", "トイレ",
    "ベッド", "ドア", "テーブル", "ショック", "チャンス", "イメージ", "タイミング",
    "バランス", "パターン", "ポイント", "ダメージ", "スタート", "ストップ",
    "スピード", "パワー", "レベル",
}


def _is_kanji(cp):
    return (0x3400 <= cp <= 0x4DBF) or (0x4E00 <= cp <= 0x9FFF) or (0xF900 <= cp <= 0xFAFF)


def _is_katakana(cp):
    return (0x30A0 <= cp <= 0x30FF) or (0x31F0 <= cp <= 0x31FF)


def _is_hiragana(cp):
    return 0x3040 <= cp <= 0x309F


def _timeout(start):
    return (time.perf_counter() * 1000.0 - start) >= SENTENCE_TIMEOUT_MS


def _split_sentences_fast(text):
    sentences = []
    n = len(text)
    p = 0
    start = 0
    line = 0
    stack = []

    while p < n:
        ch = text[p]

        if ch == "\n" or ch == "\r":
            if p > start:
                seg = text[start:p]
                if seg.strip():
                    sentences.append((start, p, line))
            if ch == "\r" and p + 1 < n and text[p + 1] == "\n":
                p += 2
            else:
                p += 1
            start = p
            line += 1
            stack.clear()
            continue

        if stack and ch == stack[-1]:
            stack.pop()
            p += 1
            if not stack and p > start and p - 2 >= start and text[p - 2] in _SENTENCE_END:
                if text[start:p].strip():
                    sentences.append((start, p, line))
                start = p
            continue

        if ch in _OPEN_TO_CLOSE:
            if not stack or ch != _OPEN_TO_CLOSE[ch]:
                stack.append(_OPEN_TO_CLOSE[ch])
            p += 1
            continue

        if ch in _SENTENCE_END and not stack:
            if ch == ".":
                prev_ch = text[p - 1] if p > 0 else ""
                next_ch = text[p + 1] if p + 1 < n else ""
                if prev_ch == "." or next_ch == "." or (prev_ch.isalnum() and next_ch.isalnum()):
                    p += 1
                    continue
            p += 1
            while p < n and text[p] in _SENTENCE_END:
                p += 1
            while p < n and text[p] in _CLOSE_CHARS:
                p += 1
            if p > start and text[start:p].strip():
                sentences.append((start, p, line))
            start = p
            continue

        p += 1

    if start < n and text[start:n].strip():
        sentences.append((start, n, line))

    return sentences, line


def _sentence_base_score(seg):
    kanji = 0
    kata = 0
    hira = 0

    for ch in seg:
        cp = ord(ch)
        if _is_kanji(cp):
            kanji += 1
        elif _is_katakana(cp):
            kata += 1
        elif _is_hiragana(cp):
            hira += 1

    jp_content = kanji + kata + hira
    length = len(seg)

    if jp_content < 4 or length < 5:
        return -5.0

    return (
        min(kanji, 20) * 0.25
        + min(kata, 20) * 0.25
        + min(math.log(length + 1.0), 4.0) * 0.4
    )


def _extract_candidates(text, sentences, start_time):
    term_info = {}
    sentence_terms = [[] for _ in range(len(sentences))]

    def register(term, bonus, sid, local_seen):
        term = term.strip()
        if len(term) < 2 or term in _SAMPLE_STOPWORDS or term in local_seen:
            return
        local_seen.add(term)
        entry = term_info.get(term)
        if entry is None:
            term_info[term] = [bonus, [sid]]
        else:
            if bonus > entry[0]:
                entry[0] = bonus
            sids = entry[1]
            if sids[-1] != sid:
                sids.append(sid)
        sentence_terms[sid].append(term)

    for sid, (ss, se, _) in enumerate(sentences):
        seg = text[ss:se]
        local_seen = set()

        for m in _RE_BRACKET_TERM.finditer(seg):
            register(m.group(1), 3.0, sid, local_seen)

        for m in _RE_DOT_TERM.finditer(seg):
            register(m.group(0), 2.8, sid, local_seen)

        for m in _RE_KATA_TERM.finditer(seg):
            term = m.group(0)
            bonus = 2.4 if len(term) >= 3 else 1.4
            register(term, bonus, sid, local_seen)

        for m in _RE_KANJI_TERM.finditer(seg):
            term = m.group(0)
            bonus = 2.2 if len(term) >= 3 else 1.2
            register(term, bonus, sid, local_seen)

        for m in _RE_ALPHA_RANK.finditer(seg):
            register(m.group(0), 1.5, sid, local_seen)

        if (sid & TIME_CHECK_MASK) == 0 and _timeout(start_time):
            break

    return term_info, sentence_terms


def _compute_term_scores(term_info, sentence_count):
    term_scores = {}
    max_df = max(10, int(sentence_count * 0.25))
    log_total = max(math.log(sentence_count + 1.0), 1.0)

    for term, (type_bonus, sids) in term_info.items():
        df = len(sids)
        if df > max_df:
            continue

        if df == 1:
            freq_weight = 0.7
        else:
            freq_weight = 1.0 + math.log(min(df, 20))

        idf_norm = (math.log((sentence_count + 1.0) / (df + 1.0)) + 0.5) / log_total
        term_scores[term] = freq_weight * type_bonus * idf_norm

    return term_scores


def extract_glossary_sample(all_text, paserent):
    if not all_text or not all_text.strip():
        return ""

    try:
        percent = float(paserent)
    except (TypeError, ValueError):
        percent = 10.0

    if percent < 0.1:
        percent = 0.1
    elif percent > 100.0:
        percent = 100.0

    if percent >= 100.0:
        return all_text

    total_chars = len(all_text)
    budget = max(1, int(total_chars * percent / 100.0))

    if total_chars <= budget:
        return all_text

    start_time = time.perf_counter() * 1000.0
    sentences, _ = _split_sentences_fast(all_text)

    if not sentences:
        return ""

    sentence_count = len(sentences)
    term_info, sentence_terms = _extract_candidates(all_text, sentences, start_time)
    term_scores = _compute_term_scores(term_info, sentence_count)

    filtered_sentence_terms = []
    for terms in sentence_terms:
        filtered = [t for t in terms if t in term_scores]
        filtered_sentence_terms.append(filtered)

    base_scores = [
        _sentence_base_score(all_text[ss:se])
        for ss, se, _ in sentences
    ]

    num_sections = min(SECTION_COUNT, max(1, sentence_count // 10))
    section_budget = max(1.0, budget / num_sections)
    section_used = [0] * num_sections
    sentence_sections = [(sid * num_sections) // sentence_count for sid in range(sentence_count)]

    term_covered = {}
    selected_flags = bytearray(sentence_count)

    def current_score(sid):
        ss, se, _ = sentences[sid]
        seg_len = se - ss
        term_gain = 0.0

        for t in filtered_sentence_terms[sid]:
            cov = term_covered.get(t, 0)
            if cov == 0:
                term_gain += term_scores[t]
            elif cov == 1:
                term_gain += term_scores[t] * 0.35
            elif cov == 2:
                term_gain += term_scores[t] * 0.10

        denom = 1.0 + max(seg_len, 15) / 100.0
        score = base_scores[sid] + (term_gain / denom) * 4.0

        sec = sentence_sections[sid]
        sec_ratio = section_used[sec] / section_budget
        if sec_ratio >= 1.8:
            score *= 0.25
        elif sec_ratio >= 1.2:
            score *= 0.55

        if (sid > 0 and selected_flags[sid - 1]) or (sid + 1 < sentence_count and selected_flags[sid + 1]):
            score -= 2.0

        return score

    heap = [(-current_score(sid), sid) for sid in range(sentence_count)]
    heapq.heapify(heap)

    selected = []
    used_chars = 0
    step = 0

    while heap and used_chars < budget:
        _, sid = heapq.heappop(heap)
        if selected_flags[sid]:
            continue

        ss, se, _ = sentences[sid]
        seg_len = se - ss
        added_chars = seg_len + (1 if selected else 0)

        if used_chars + added_chars > budget:
            continue

        updated = current_score(sid)
        if heap and updated < -heap[0][0]:
            heapq.heappush(heap, (-updated, sid))
            step += 1
            if (step & TIME_CHECK_MASK) == 0 and _timeout(start_time):
                break
            continue

        selected_flags[sid] = 1
        selected.append(sid)
        used_chars += added_chars
        section_used[sentence_sections[sid]] += seg_len

        for t in filtered_sentence_terms[sid]:
            term_covered[t] = term_covered.get(t, 0) + 1

        step += 1
        if (step & TIME_CHECK_MASK) == 0 and _timeout(start_time):
            break

    if not selected:
        best_sid = max(range(sentence_count), key=lambda i: base_scores[i])
        ss, se, _ = sentences[best_sid]
        return all_text[ss:min(se, ss + budget)]

    selected.sort()
    return "\n".join(all_text[sentences[sid][0]:sentences[sid][1]] for sid in selected)