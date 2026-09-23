import math
import re
import time
import heapq

SENTENCE_TIMEOUT_MS = 10000.0
TOP_SENTENCE_LIMIT = 2001
MAX_SUBSTRING_LEN = 8
MAX_CANDIDATES = 500000
TIME_CHECK_MASK = 1023

_KANJI_RANGES = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF))
_QUOTE_CLOSE = {"「": "」", "『": "』", "“": "”", '"': '"'}
_SPECIAL_END = {".", "!", "?", ";", ":", "。", "！", "？", "〕", "』", "）"}

def _is_kanji(cp):
    return (0x3400 <= cp <= 0x4DBF) or (0x4E00 <= cp <= 0x9FFF) or (0xF900 <= cp <= 0xFAFF)

def _is_katakana(cp):
    return (0x30A0 <= cp <= 0x30FF) or (0x31F0 <= cp <= 0x31FF)

def _is_japanese(cp):
    return _is_kanji(cp) or (0x3040 <= cp <= 0x309F) or _is_katakana(cp) or (0x3000 <= cp <= 0x303F)

def _is_upper(cp):
    return 65 <= cp <= 90

def _is_digit(cp):
    return 48 <= cp <= 57

def _timeout(start):
    return (time.perf_counter() * 1000.0 - start) >= SENTENCE_TIMEOUT_MS

def _add_candidate(table, text, weight, type_mask, sentence_id, max_candidates=MAX_CANDIDATES):
    if not text:
        return None

    item = table.get(text)

    if item is not None:
        item[0] += weight
        item[1] |= type_mask
        sentences = item[2]
        if not sentences or sentences[-1] != sentence_id:
            sentences.append(sentence_id)
        return item

    if len(table) >= max_candidates:
        return None

    table[text] = [weight, type_mask, [sentence_id]]
    return table[text]

def _add_substrings(table, text, start, end, min_len, max_len, type_mask, sentence_id, start_time):
    run_len = end - start

    if run_len < min_len:
        return True

    if run_len > MAX_SUBSTRING_LEN:
        end = start + MAX_SUBSTRING_LEN
        run_len = MAX_SUBSTRING_LEN

    max_len = min(max_len, run_len)

    # 길이별 substring을 직접 slicing.
    # bytes 변환이나 list/join을 사용하지 않는다.
    for i in range(start, end - min_len + 1):
        last = min(end, i + max_len)

        for j in range(i + min_len, last + 1):
            _add_candidate(table, text[i:j], 1, type_mask, sentence_id)

        if ((i - start) & TIME_CHECK_MASK) == 0 and _timeout(start_time):
            return False

    return True

def _split_sentences_fast(text):
    sentences = []
    start = 0
    line = 0
    p = 0
    n = len(text)

    while p < n:
        ch = text[p]

        if ch == "\n":
            if p > start:
                sentences.append((start, p, line))
            p += 1
            start = p
            line += 1
            continue

        if ch == "\r":
            if p > start:
                sentences.append((start, p, line))
            p += 1
            if p < n and text[p] == "\n":
                p += 1
            start = p
            line += 1
            continue

        if ch in _SPECIAL_END:
            p += 1
            if p > start:
                sentences.append((start, p, line))
            start = p
            continue

        p += 1

    if start < n:
        sentences.append((start, n, line))

    return sentences, line

def _sentence_score(text):
    kanji = 0
    kata = 0
    digit = 0
    upper = 0
    jp = 0

    for ch in text:
        cp = ord(ch)

        if _is_kanji(cp):
            kanji += 1
            jp += 1
        elif _is_katakana(cp):
            kata += 1
            jp += 1
        elif 0x3040 <= cp <= 0x309F:
            jp += 1
        elif 0x3000 <= cp <= 0x303F:
            jp += 1
        elif cp < 128:
            if 48 <= cp <= 57:
                digit += 1
            elif 65 <= cp <= 90:
                upper += 1

    total = len(text)

    if not total:
        return -1e9

    return kanji * 2.4 + kata * 2.0 + digit * 0.8 + upper * 0.5 + (3.0 if jp and kanji else 0.0) + math.log(total + 1.0)

def _extract_candidates(text, sentences, start_time):
    candidates = {}
    sentence_count = len(sentences)

    # sentence별 후보를 별도 객체로 만들지 않고
    # sentence index -> candidate 문자열 목록만 유지한다.
    sentence_candidates = [[] for _ in range(sentence_count)]

    for sid, (ss, se, line) in enumerate(sentences):
        p = ss

        while p < se:
            cp = ord(text[p])

            # -------------------------------------------------
            # 한자
            # -------------------------------------------------
            if _is_kanji(cp):
                run_start = p
                p += 1

                while p < se and _is_kanji(ord(text[p])):
                    p += 1

                run_end = p

                if run_end - run_start >= 2:
                    run = text[run_start:run_end]
                    item = _add_candidate(candidates, run, 2 if len(run) >= 3 else 1, 32, sid)

                    if item is not None:
                        sentence_candidates[sid].append(run)

                    if not _add_substrings(candidates, text, run_start, run_end, 2, 8, 1, sid, start_time):
                        return None, None

            # -------------------------------------------------
            # 가타카나
            # -------------------------------------------------
            elif _is_katakana(cp):
                run_start = p
                p += 1

                while p < se and _is_katakana(ord(text[p])):
                    p += 1

                run_end = p

                if run_end - run_start >= 2:
                    run = text[run_start:run_end]
                    item = _add_candidate(candidates, run, 2, 32, sid)

                    if item is not None:
                        sentence_candidates[sid].append(run)

                    if not _add_substrings(candidates, text, run_start, run_end, 2, 8, 2, sid, start_time):
                        return None, None

            # -------------------------------------------------
            # 영문 대문자 단어
            # -------------------------------------------------
            elif _is_upper(cp):
                run_start = p
                p += 1

                while p < se:
                    c = text[p]

                    if ord(c) < 128 and (c.isalnum() or c in "_-"):
                        p += 1
                    else:
                        break

                if p - run_start >= 2:
                    run = text[run_start:p]
                    item = _add_candidate(candidates, run, 2, 4, sid)

                    if item is not None:
                        sentence_candidates[sid].append(run)

            # -------------------------------------------------
            # 숫자 + 일본어
            # -------------------------------------------------
            elif _is_digit(cp):
                run_start = p
                p += 1

                while p < se and text[p] in ".,%-+":
                    p += 1

                jp_start = p

                while p < se:
                    x = ord(text[p])

                    if _is_japanese(x) or x == 0x30FC:
                        p += 1
                    else:
                        break

                if p > jp_start:
                    run = text[run_start:p]
                    item = _add_candidate(candidates, run, 2, 8, sid)

                    if item is not None:
                        sentence_candidates[sid].append(run)

            # -------------------------------------------------
            # ・ 연결 표현
            # -------------------------------------------------
            elif cp == 0x30FB:
                run_start = p
                p += 1
                count = 1

                while p < se:
                    x = ord(text[p])

                    if x == 0x30FB:
                        count += 1
                        p += 1
                    elif _is_japanese(x) or _is_upper(x) or _is_digit(x):
                        p += 1
                    else:
                        break

                if p > run_start + 1:
                    run = text[run_start:p]
                    item = _add_candidate(candidates, run, 2, 64, sid)

                    if item is not None:
                        sentence_candidates[sid].append(run)

            else:
                p += 1

            if (p & TIME_CHECK_MASK) == 0 and _timeout(start_time):
                return None, None

        # -----------------------------------------------------
        # 따옴표 내부
        # -----------------------------------------------------
        p = ss

        while p < se:
            ch = text[p]

            if ch in _QUOTE_CLOSE:
                close = _QUOTE_CLOSE[ch]
                q = p + 1

                while q < se and text[q] != close:
                    q += 1

                if q < se and q > p + 1:
                    content = text[p + 1:q]

                    if len(content) >= 2:
                        item = _add_candidate(candidates, content, 3, 16, sid)

                        if item is not None:
                            sentence_candidates[sid].append(content)

                    p = q + 1
                else:
                    p += 1
            else:
                p += 1

            if (p & TIME_CHECK_MASK) == 0 and _timeout(start_time):
                return None, None

        # -----------------------------------------------------
        # 일본어 전체 연속 구간
        # -----------------------------------------------------
        p = ss

        while p < se:
            cp = ord(text[p])

            if _is_japanese(cp):
                run_start = p
                p += 1

                while p < se:
                    x = ord(text[p])

                    if _is_japanese(x) or x == 0x30FC:
                        p += 1
                    else:
                        break

                run_end = p
                count = run_end - run_start

                if count >= 2:
                    run = text[run_start:run_end]
                    item = _add_candidate(candidates, run, 2 if count >= 3 else 1, 32, sid)

                    if item is not None:
                        sentence_candidates[sid].append(run)

                    if count >= 3:
                        if not _add_substrings(candidates, text, run_start, run_end, 2, 5, 32, sid, start_time):
                            return None, None
            else:
                p += 1

            if (p & TIME_CHECK_MASK) == 0 and _timeout(start_time):
                return None, None

    return candidates, sentence_candidates

def _candidate_score(item, sentence_count):
    weight, type_mask, sentence_ids = item

    spread = len(sentence_ids) / sentence_count if sentence_count else 0.0
    length_score = math.log(len(sentence_ids) + 2.0)

    type_bonus = 0.0

    if type_mask & 1:
        type_bonus += 1.5
    if type_mask & 2:
        type_bonus += 1.2
    if type_mask & 4:
        type_bonus += 0.8
    if type_mask & 8:
        type_bonus += 1.0
    if type_mask & 16:
        type_bonus += 1.3
    if type_mask & 32:
        type_bonus += 1.4
    if type_mask & 64:
        type_bonus += 1.0

    return weight * 1.5 + spread * 12.0 + length_score + type_bonus

def extract_glossary_sample(all_text, paserent):
    if not all_text:
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

    text_len = len(all_text.encode("utf-8"))
    budget = int(text_len * percent / 100.0)

    if budget <= 0:
        budget = 1

    # 너무 짧은 경우
    if text_len <= budget:
        return all_text

    start_time = time.perf_counter() * 1000.0

    sentences, max_line = _split_sentences_fast(all_text)

    if not sentences:
        return ""

    candidates, sentence_candidates = _extract_candidates(all_text, sentences, start_time)

    if candidates is None:
        # 10초 timeout이면 지금까지 얻은 데이터를 이용해 계속 진행하지 않고
        # 안전하게 빈 결과를 반환한다.
        return ""

    sentence_count = len(sentences)

    # candidate score를 미리 계산
    candidate_scores = {}

    for text, item in candidates.items():
        candidate_scores[text] = _candidate_score(item, sentence_count)

    # 문장별 score
    sentence_scores = [0.0] * sentence_count

    for sid, (ss, se, line) in enumerate(sentences):
        sentence_scores[sid] = _sentence_score(all_text[ss:se])

    # candidate spread를 이용한 문장 보정값.
    # 모든 candidate를 다시 순회하지 않고 candidate가 등장한 sentence에 직접 더한다.
    candidate_bonus = [0.0] * sentence_count

    for text, item in candidates.items():
        score = candidate_scores[text]
        sentence_ids = item[2]

        # 후보가 여러 문장에 등장할수록 가치가 높음
        bonus = min(score * 0.25, 8.0)

        for sid in sentence_ids:
            candidate_bonus[sid] += bonus

    # 최종 정렬 점수
    ranking = []

    for sid in range(sentence_count):
        score = sentence_scores[sid] + candidate_bonus[sid]
        ranking.append((score, -sid, sid))

    # 전체 문장을 정렬하지 않고 상위 2001개만 가져온다.
    if sentence_count > TOP_SENTENCE_LIMIT:
        top = heapq.nlargest(TOP_SENTENCE_LIMIT, ranking)
        top.sort(reverse=True)
        ranked = [x[2] for x in top]
    else:
        ranking.sort(reverse=True)
        ranked = [x[2] for x in ranking]

    selected = []
    selected_flags = bytearray(sentence_count)
    selected_lines = bytearray(max_line + 4)
    used_candidates = set()

    used_bytes = 0

    while used_bytes < budget and len(selected) < sentence_count:
        best_sid = -1
        best_score = -1e100

        for sid in ranked:
            if selected_flags[sid]:
                continue

            ss, se, line = sentences[sid]
            sentence_bytes = len(all_text[ss:se].encode("utf-8"))

            if used_bytes + sentence_bytes > budget:
                continue

            nearby = False

            if line >= 2 and selected_lines[line - 2]:
                nearby = True

            if selected_lines[line - 1]:
                nearby = True

            if selected_lines[line]:
                nearby = True

            if line + 1 < len(selected_lines) and selected_lines[line + 1]:
                nearby = True

            if line + 2 < len(selected_lines) and selected_lines[line + 2]:
                nearby = True

            score = sentence_scores[sid] + candidate_bonus[sid]

            if nearby:
                score -= 5.0

            if score > best_score:
                best_score = score
                best_sid = sid

        if best_sid < 0:
            break

        selected_flags[best_sid] = 1
        selected.append(best_sid)

        ss, se, line = sentences[best_sid]
        used_bytes += len(all_text[ss:se].encode("utf-8"))

        if line < len(selected_lines):
            selected_lines[line] = 1

        # 사용된 candidate 기록
        for candidate_text in sentence_candidates[best_sid]:
            if candidate_text in used_candidates:
                continue

            used_candidates.add(candidate_text)

    selected.sort()

    return "\n".join(
        all_text[sentences[sid][0]:sentences[sid][1]]
        for sid in selected
    )