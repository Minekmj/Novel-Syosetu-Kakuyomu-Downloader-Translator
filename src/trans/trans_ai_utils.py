import json
import os
import re

try:
    from google.genai import types
except ImportError:
    types = None

from src.trans.prom import *
import src.glossary.glossary_text as glossary_text

extract_glossary = glossary_text.extract_glossary


def split_text_by_lines(text, max_chars=5000):
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chunk = []
    current_length = 0

    for line in lines:
        if current_length + len(line) > max_chars and current_chunk:
            chunks.append(''.join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line)

    if current_chunk:
        chunks.append(''.join(current_chunk))

    return chunks


JP_PATTERN = re.compile(
    r'[\u3040-\u309f\u30a0-\u30fb\u30fd-\u30ff\u31f0-\u31ff\uff65-\uff6f\uff71-\uff9f\u4e00-\u9fff\uf900-\ufaff\u3005\u3006]'
)


def get_japanese_ratio(text):
    if not text:
        return 0.0

    clean_text = re.sub(r'[^\w]|[\d_]', '', text)
    if not clean_text:
        return 0.0

    jp_chars = len(JP_PATTERN.findall(clean_text))
    return jp_chars / len(clean_text) * 100


def get_korean_ratio(text):
    if not text:
        return 0.0

    clean_text = re.sub(r'[^\w]|[\d_]', '', text)
    if not clean_text:
        return 0.0

    ko_chars = len(re.findall(r'[\uac00-\ud7a3\u3131-\u318e]', clean_text))
    return ko_chars / len(clean_text) * 100


def get_linebreak_preservation_ratio(original, translated):
    original_breaks = original.count('\n')
    translated_breaks = translated.count('\n')

    if original_breaks == 0:
        return 100.0 if translated_breaks == 0 else 0.0

    difference = abs(original_breaks - translated_breaks)
    return max(0.0, (1.0 - difference / original_breaks) * 100.0)


def get_japanese_info(text):
    if not text:
        return 0.0, 0

    clean_text = re.sub(r"[^\w]|[\d_]", "", text)
    if not clean_text:
        return 0.0, 0

    jp_chars = len(JP_PATTERN.findall(clean_text))
    ratio = (jp_chars / len(clean_text)) * 100
    return ratio, jp_chars


def inspect_json_japanese(
    json_path, ratio_threshold=10.0, char_count_threshold=0, encoding="utf-8"
):
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_path}")

    with open(json_path, "r", encoding=encoding) as f:
        data = json.load(f)

    title = data.get("name", os.path.splitext(os.path.basename(json_path))[0])
    chunk_size = data.get("chunk", 5000)
    raw = bool(data.get("raw", False))

    chunk_indices = sorted(
        list(set(int(k) for k in data.keys() if k.isdigit()))
    )

    detected_items = []

    def is_jp_line(line_text):
        jp_ratio, jp_count = get_japanese_info(line_text)
        if char_count_threshold > 0:
            return jp_count >= char_count_threshold
        return jp_ratio >= ratio_threshold

    for chunk_idx in chunk_indices:
        chunk_key = str(chunk_idx)
        text = data.get(chunk_key)
        if not text or not isinstance(text, str):
            continue

        lines = text.splitlines(keepends=True)
        total_lines = len(lines)
        i = 0

        while i < total_lines:
            if is_jp_line(lines[i]):
                start_line = i
                last_jp_line = i
                j = i + 1

                while j < total_lines:
                    if is_jp_line(lines[j]):
                        last_jp_line = j
                        j += 1
                    elif lines[j].strip() == "":
                        k = j + 1
                        while k < total_lines and lines[k].strip() == "":
                            k += 1
                        if k < total_lines and is_jp_line(lines[k]):
                            j += 1
                        else:
                            break
                    else:
                        break

                end_line = last_jp_line + 1
                block_text = "".join(lines[start_line:end_line])

                detected_items.append(
                    {
                        "chunk_key": chunk_key,
                        "chunk_display": chunk_idx + 1,
                        "start_line": start_line,
                        "end_line": end_line,
                        "original_text": block_text,
                    }
                )

                i = end_line
            else:
                i += 1

    return {
        "json_path": json_path,
        "title": title,
        "chunk_size": chunk_size,
        "raw": raw,
        "items": detected_items,
    }


def apply_japanese_corrections(json_path, corrections):
    if not os.path.exists(json_path):
        return False, 0, f"JSON 파일을 찾을 수 없습니다: {json_path}"

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        title = data.get('name', 'restored')
        max_chars = data.get('chunk', 5000)
        out = os.environ.get('minedown_setting_src', './out/')
        safe = re.sub(r'[\\/:*?"<>|]', '_', title).strip()
        ai_dir = os.path.join(out, "trs", f'ai_down_{safe}_{max_chars}')

        grouped = {}
        for corr in corrections:
            ck = corr['chunk_key']
            if ck not in grouped:
                grouped[ck] = []
            grouped[ck].append(corr)

        modified_count = 0

        for chunk_key, corr_list in grouped.items():
            if chunk_key not in data:
                continue

            text = data[chunk_key]
            lines = text.splitlines(keepends=True)

            corr_list.sort(key=lambda x: x['start_line'], reverse=True)

            for item in corr_list:
                start = item['start_line']
                end = item['end_line']
                new_text = item['new_text']

                new_lines = new_text.splitlines(keepends=True)
                lines[start:end] = new_lines
                modified_count += 1

            updated_chunk_text = ''.join(lines)
            data[chunk_key] = updated_chunk_text

            if os.path.exists(ai_dir):
                try:
                    display_idx = int(chunk_key) + 1
                    chunk_file = f'{ai_dir}/{display_idx}.txt'
                    with open(chunk_file, 'w', encoding='utf-8') as cf:
                        cf.write(updated_chunk_text)
                except Exception:
                    pass

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return True, modified_count, ""

    except Exception as e:
        return False, 0, str(e)


def build_dynamic_glossary(chunk, dictionary, max_chars=GLOSSARY_MAX_CHARS):
    if not dictionary:
        return ''

    matched = []
    for source, target in dictionary.items():
        source = str(source).strip()
        target = str(target).strip()

        if not source or not target:
            continue

        count = chunk.count(source)
        if count >= 1:
            matched.append((count, source, target))

    if not matched:
        return ''

    matched.sort(key=lambda x: x[0], reverse=True)

    selected = []
    current_length = 0

    for count, source, target in matched:
        line = f'{source} → {target}'
        line_length = len(line) + (1 if selected else 0)

        if current_length + line_length > max_chars:
            break

        selected.append(line)
        current_length += line_length

    if not selected:
        return ''

    return '\n'.join(selected)


def restore_img_placeholders(text, img_tags):
    for tag in img_tags:
        text = text.replace(IMG_PLACEHOLDER, tag, 1)
    return text


def build_thinking_config(thinking_val, model_name=""):
    from src.ai.models.gemini import build_thinking_config as _btc
    return _btc(thinking_val, model_name)


def detect_raw_text(text):
    lines = text.splitlines()
    return len(lines) >= 3 and lines[2].strip().lower() == '(raw)'


def prepare_raw_text(text):
    lines = text.splitlines(keepends=True)

    if len(lines) < 3 or lines[2].strip().lower() != '(raw)':
        return text, '제목 미정'

    book_title = lines[0].strip()
    author = lines[1].strip()
    title = book_title + '_' + author
    delimiter_index = None

    for i, line in enumerate(lines):
        if line.strip() == '=' * 30:
            delimiter_index = i
            break

    if delimiter_index is not None:
        body_start = delimiter_index
    else:
        body_start = 5

    raw_body = ''.join(lines[body_start:])
    return raw_body, title


def save_translation_json(
    translated_parts,
    original_chunks,
    max_chars,
    title,
    file_path,
    raw=False,
    br_start=0,
    thinking_budget=None,
    ai_target=None
):
    data = {}
    count = max(
        len(translated_parts) if translated_parts else 0,
        len(original_chunks) if original_chunks else 0
    )

    for i in range(count):
        trans = translated_parts[i] if translated_parts and i < len(translated_parts) else None
        orig = original_chunks[i] if original_chunks and i < len(original_chunks) else None

        if trans is not None:
            data[str(i)] = trans
        if orig is not None:
            data[f"{i}-j"] = orig

    data['chunk'] = max_chars
    data['name'] = title
    if raw:
        data['raw'] = True
    data['br_start'] = br_start
    if thinking_budget is not None:
        data['thinking_budget'] = thinking_budget
    if ai_target is not None:
        data['ai_target'] = int(ai_target)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def save_translation_txt(
    translated_parts,
    title,
    file_path
):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(title + '\n' + ''.join(p for p in translated_parts if p))


glossary_text.get_japanese_ratio = get_japanese_ratio