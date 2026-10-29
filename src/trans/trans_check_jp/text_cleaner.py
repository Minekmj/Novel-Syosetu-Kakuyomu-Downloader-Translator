import re
from .constants import (
    JP_PATTERN, KO_PATTERN, JP_RANGES, KO_RANGES,
    WORD_BRACKET_PATTERN, EXPLANATION_PATTERNS, PARTICLE_PATTERN,
    KANA_TO_HANGUL
)
from .hangul_utils import decompose_hangul, compose_hangul, attach_jongsung


def has_japanese(text: str) -> bool:
    return bool(text and JP_PATTERN.search(text))


def resolve_arrows_and_memos(text: str) -> str:
    if not text:
        return text

    text = re.sub(r'\s*\(Wait[^\)]*\)\s*[-=]>[^\n]+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\(Wait[^\)]*\)', '', text, flags=re.IGNORECASE)

    if '->' not in text and '→' not in text:
        return text

    lines = text.split('\n')
    processed_lines = []
    for line in lines:
        line_strip = line.strip()
        m = re.search(r'[-=]>\s*(.+)$', line_strip)
        if not m:
            processed_lines.append(line)
            continue

        after_arrow = m.group(1).strip()
        before_arrow = line_strip[:m.start()].strip()

        if JP_PATTERN.search(before_arrow) and KO_PATTERN.search(after_arrow) and not JP_PATTERN.search(after_arrow):
            if len(after_arrow) >= len(before_arrow) * 0.6:
                processed_lines.append(after_arrow)
                continue

        if before_arrow.startswith('“') and after_arrow.startswith('“'):
            processed_lines.append(after_arrow)
            continue

        processed_lines.append(before_arrow)

    return '\n'.join(processed_lines)


def resolve_brackets_from_raw(text: str) -> str:
    if not text:
        return text

    text = re.sub(rf'[{KO_RANGES}{JP_RANGES}]+\([^\)]*오타:\s*([가-힣\s]+)\)', r'\1', text)

    def _resolve_whole_line_bilingual(line_str):
        clean = line_str.strip()
        quote_prefix = ''
        quote_suffix = ''
        if (clean.startswith('"') and clean.endswith('"')) or (clean.startswith('“') and clean.endswith('”')):
            quote_prefix = clean[0]
            quote_suffix = clean[-1]
            clean = clean[1:-1].strip()

        m = re.fullmatch(r'([^\(\)（）\n]{2,}?)\s*[\(（]([가-힣\s,.!?~…·―\?!]+)[\)）]', clean)
        if m:
            front_text = m.group(1).strip()
            inside_text = m.group(2).strip()
            if JP_PATTERN.search(front_text) and not JP_PATTERN.search(inside_text):
                return f"{quote_prefix}{inside_text}{quote_suffix}"
        return line_str

    text = '\n'.join([_resolve_whole_line_bilingual(l) for l in text.split('\n')])

    text = re.sub(r'『[^』]+』\s*[\(（]([^\(\)（）]+)[\)）]', r'『\1』', text)
    text = re.sub(r'《[^》]+》\s*[\(（]([^\(\)（）]+)[\)）]', r'《\1》', text)
    text = re.sub(r'\[[^\]]+\]\s*[\(（]([^\(\)（）]+)[\)）]', r'[\1]', text)

    def _replace_raw_bracket(m):
        lead = m.group(1)
        front_word = m.group(2)
        inside_text = m.group(3).strip()

        has_jp_front = bool(JP_PATTERN.search(front_word))
        has_ko_front = bool(KO_PATTERN.search(front_word))
        has_jp_inside = bool(JP_PATTERN.search(inside_text))
        has_ko_inside = bool(KO_PATTERN.search(inside_text))

        if has_ko_front and not has_jp_front and has_ko_inside and not has_jp_inside:
            return m.group(0)

        if has_ko_front and not has_jp_front and has_jp_inside and not has_ko_inside:
            return f"{lead}{front_word}"

        if has_jp_front and has_ko_inside and not has_jp_inside:
            if front_word in ['에っ', '에ッ', '앗っ', '앗ッ']:
                return f"{lead}{inside_text}"

            if has_ko_front:
                ko_stem = ''.join(re.findall(rf'[{KO_RANGES}]+', front_word))
                if ko_stem in inside_text:
                    return f"{lead}{inside_text}"
                else:
                    jp_part = ''.join(re.findall(rf'[{JP_RANGES}]+', front_word))
                    stem = front_word[:-len(jp_part)] if jp_part else front_word
                    return f"{lead}{stem} {inside_text}".strip()

            return f"{lead}{inside_text}"

        return m.group(0)

    text = WORD_BRACKET_PATTERN.sub(_replace_raw_bracket, text)
    text = re.sub(rf'([{KO_RANGES}]+)\s*[\(（][{JP_RANGES}\s]+[\)）]', r'\1', text)
    text = re.sub(r'([가-힣]+)\(\1\)', r'\1', text)
    return text


def clean_explanation_residue(text: str) -> str:
    if not text:
        return text
    for pat in EXPLANATION_PATTERNS:
        text = pat.sub('', text)
    return text.strip()


def strip_korean_particles(token: str) -> str:
    if not token:
        return token
    m = PARTICLE_PATTERN.search(token)
    if m:
        stem = token[:m.start()]
        if JP_PATTERN.search(stem):
            return stem
    return token


def sanitize_dot_addition(orig_text: str, trans_text: str) -> str:
    if not trans_text:
        return ""
    if '.' not in orig_text and '。' not in orig_text:
        trans_text = trans_text.replace('.', '').replace('。', '')
    return trans_text.strip()


def sanitize_translated_word(trans_text: str, orig_text: str = "") -> str:
    if not trans_text:
        return ""
    trans_text = clean_explanation_residue(trans_text)
    f = trans_text.find("： ")
    if f > -1:
        trans_text = trans_text[f + 1:]
    parts = re.split(r'[,，/／\n]', trans_text)
    first_choice = parts[0].strip()
    res = first_choice if first_choice else trans_text.strip()
    if orig_text:
        res = sanitize_dot_addition(orig_text, res)
    return res


def fix_japanese_interjections(text: str) -> str:
    if not text:
        return text

    CLOSING_QUOTES = r'[\s"\'“”‘’「」『』!?！？…….]'
    text = re.sub(rf'([가-힣])[-―~]ん(?={CLOSING_QUOTES}|$)', r'\1―응', text)
    text = re.sub(rf'(^|[\s“"\'「])ん\?', r'\1응?', text)
    text = re.sub(rf'(^|[\s“"\'「])ん(?={CLOSING_QUOTES}|$)', r'\1응', text)
    text = re.sub(r'후ふ+', '후후', text)

    text = re.sub(r'([가-힣])ぇっと', r'\1엣또', text)
    text = re.sub(r'([가-힣])っと', r'\1또', text)

    def lengthen_vowel(match):
        prev_char = match.group(1)
        small_kana = match.group(2)
        kana_map = {
            'ぁ': '아', 'ぃ': '이', 'ぅ': '우', 'ぇ': '에', 'ぉ': '오',
            'ァ': '아', 'ィ': '이', 'ゥ': '우', 'ェ': '에', 'ォ': '오'
        }
        return prev_char + kana_map.get(small_kana, '')

    text = re.sub(r'([가-힣])([ぁぃぅぇぉァィゥェォ])', lengthen_vowel, text)
    text = text.replace('え', '에').replace('゛', '')

    def replace_tsu(match):
        prev_char = match.group(1)
        punct = match.group(2)
        decomp = decompose_hangul(prev_char)
        if decomp:
            cho, jung, jong = decomp
            if jong == '':
                if prev_char in ['싸', '이', '앗', '하', '어', '에', '죽']:
                    return f"{compose_hangul(cho, jung, 'ㅅ')}{punct}"
                return f"{prev_char}{punct}"
            else:
                return f"{prev_char}앗{punct}"
        return f"{prev_char}{punct}"

    text = re.sub(r'([가-힣])[ッっｯ]+([!?！？…….]+)', replace_tsu, text)
    text = re.sub(r'([가-힣])[ッっｯ]([가-힣])', r'\1\2', text)
    text = re.sub(r'[ッっｯ]+(?=[\s\n!?,.]|$)', '!', text)
    text = re.sub(r'[ッっｯ]', '', text)
    return text


def fix_embedded_katakana(text: str) -> str:
    if not text:
        return text

    for k in sorted(KANA_TO_HANGUL.keys(), key=len, reverse=True):
        if k in text:
            text = text.replace(k, KANA_TO_HANGUL[k])

    def _combine_n(m):
        prev_char = m.group(1)
        return attach_jongsung(prev_char, 'ㄴ')

    text = re.sub(r'([가-힣])ン', _combine_n, text)
    text = text.replace('ン', 'ㄴ')
    return text