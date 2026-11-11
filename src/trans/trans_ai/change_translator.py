import asyncio
import json
import os
import re
from src.trans.trans_ai_utils import (
    detect_raw_text,
    save_translation_json,
    save_translation_txt
)
import src.down.down as down
from .json_translator import _parse_json_title_metadata
from .config import ForceStopException
from .chunk_utils import _is_stopped

def _find_backup_dir(file_path: str, chunk=None):
    out = down.downin.base_data.OUTFOLDER + '/'
    trs_dir = os.path.join(out, "trs")

    if os.path.isdir(file_path):
        base = os.path.basename(os.path.normpath(file_path))
        if base.startswith("ai_down_"):
            return os.path.abspath(file_path)

    parent = os.path.dirname(os.path.abspath(file_path))
    if os.path.basename(parent).startswith("ai_down_"):
        return parent

    safe_candidate = None
    chunk_candidate = str(chunk) if chunk is not None else None

    if os.path.isfile(file_path) and file_path.lower().endswith('.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_meta = json.load(f)
            title = json_meta.get('name', '')
            if title:
                safe_candidate = re.sub(r'[\\/:*?"<>|]', '_', title).strip()
            if not chunk_candidate and 'chunk' in json_meta:
                chunk_candidate = str(json_meta['chunk'])
        except Exception:
            pass

    filename = os.path.basename(file_path)
    name_no_ext = os.path.splitext(filename)[0]

    if not safe_candidate:
        m_save = re.match(r'^save_(.+?)(?:\s*_\s*|_복원|_)?(\d+)?(?:_복원)?$', name_no_ext)
        if m_save:
            safe_candidate = m_save.group(1).strip()
            if not chunk_candidate and m_save.group(2):
                chunk_candidate = m_save.group(2)
        else:
            clean = re.sub(r'(_번역|_복원|\(raw\))+$', '', name_no_ext).strip()
            safe_candidate = re.sub(r'[\\/:*?"<>|]', '_', clean).strip()

    if os.path.exists(trs_dir):
        if safe_candidate and chunk_candidate:
            exact_dir = os.path.join(trs_dir, f"ai_down_{safe_candidate}_{chunk_candidate}")
            if os.path.isdir(exact_dir):
                return exact_dir

        if safe_candidate:
            prefix = f"ai_down_{safe_candidate}_"
            for d in os.listdir(trs_dir):
                full_d = os.path.join(trs_dir, d)
                if os.path.isdir(full_d) and (d == f"ai_down_{safe_candidate}" or d.startswith(prefix)):
                    return full_d

            core_name = safe_candidate.replace('_복원', '').replace('_번역', '').strip('_')
            for d in os.listdir(trs_dir):
                full_d = os.path.join(trs_dir, d)
                if os.path.isdir(full_d) and d.startswith("ai_down_") and core_name in d:
                    return full_d

    return None


def Change_file(
    file_path: str,
    chunk=None,
    check=None,
    check_i=None
) -> str:
    try:
        if _is_stopped(check, check_i):
            return ''

        if not file_path:
            return ''

        backup_dir = _find_backup_dir(file_path, chunk)
        if not backup_dir or not os.path.isdir(backup_dir):
            return ''

        files = os.listdir(backup_dir)
        chunk_files = []
        for fname in files:
            m = re.match(r'^(\d+)\.txt$', fname)
            if m:
                chunk_files.append((int(m.group(1)), os.path.join(backup_dir, fname)))

        if not chunk_files:
            return ''

        chunk_files.sort(key=lambda x: x[0])

        parts = []
        for idx, fpath in chunk_files:
            if _is_stopped(check, check_i):
                return ''
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    parts.append(f.read())
            except Exception as read_err:
                pass

        if not parts:
            return ''

        final_result = '\n\n'.join(p for p in parts if p)

        dir_name = os.path.basename(os.path.normpath(backup_dir))
        m_dir = re.match(r'^ai_down_(.+)_(\d+)$', dir_name)
        if m_dir:
            safe = m_dir.group(1)
            chunk_val = int(m_dir.group(2))
        else:
            safe = dir_name.replace('ai_down_', '')
            chunk_val = chunk if chunk is not None else 5000

        title = None
        raw = False
        json_path = None

        if os.path.isfile(file_path) and file_path.lower().endswith('.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    j_data = json.load(f)
                title = j_data.get('name')
                raw = bool(j_data.get('raw', False))
                json_path = file_path
            except Exception:
                pass

        trs_dir = os.path.dirname(os.path.normpath(backup_dir))
        if not title:
            possible_jsons = [
                os.path.join(trs_dir, f"save_{safe} _ {chunk_val}.json"),
                os.path.join(trs_dir, f"save_{safe}_{chunk_val}_복원.json"),
                os.path.join(trs_dir, f"save_{safe}_{chunk_val}.json")
            ]
            for pj in possible_jsons:
                if os.path.exists(pj):
                    try:
                        with open(pj, 'r', encoding='utf-8') as f:
                            j_data = json.load(f)
                        title = j_data.get('name')
                        raw = bool(j_data.get('raw', False))
                        json_path = pj
                        break
                    except Exception:
                        pass

        if not title:
            title = safe

        if not raw:
            raw = detect_raw_text(final_result)

        restored_book_title, author, episode, restored_name = _parse_json_title_metadata(title)
        clean_book_title = re.sub(r'(_번역|_복원)+$', '', restored_book_title).strip()

        if _is_stopped(check, check_i):
            return ''

        if raw:
            raw_header = [clean_book_title, author, '(raw)']
            if episode:
                raw_header.append(episode)
            epub_text = '\n'.join(raw_header) + f'\n+---+\n{final_result}'
        else:
            normal_header = [f'{clean_book_title}_번역']
            if author:
                normal_header.append(author)
            if episode:
                normal_header.append(episode)
            epub_text = '\n'.join(normal_header) + f'\n+---+\n{final_result}'

        down.create_epub_from_merged_txt(txt_value=epub_text, RAW=raw)

        if _is_stopped(check, check_i):
            return ''

        out = down.downin.base_data.OUTFOLDER + '/'
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', clean_book_title).strip()
        if raw:
            os.makedirs(os.path.join(out, "epub", "raw_txt"), exist_ok=True)
            txt_path = os.path.join(out, "epub", "raw_txt", f"{safe_title}.txt")
            r_title = f'''{clean_book_title}
{author}
(raw)
{'+---+\n'}{clean_book_title} | {author}

'''
            if not _is_stopped(check, check_i):
                save_translation_txt(parts, r_title, txt_path)

        if not json_path:
            json_path = os.path.join(out, "trs", f"save_{safe_title}_{chunk_val}_복원.json")

        save_translation_json(parts, parts, chunk_val, restored_name, json_path, raw=raw)

        return json_path

    except (ForceStopException, asyncio.CancelledError):
        return ''
    except Exception as e:
        return ''