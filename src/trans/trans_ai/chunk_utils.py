import os
import re
import src.down.down as down
from .config import ForceStopException


def _is_stopped(check, check_i=None):
    if check_i:
        try:
            if check_i():
                raise ForceStopException()
        except ForceStopException:
            raise
        except Exception:
            pass

    try:
        return bool(check and check())
    except Exception:
        return False


def repair_chunk_boundaries(chunks, raw=False):
    if not chunks:
        return chunks

    chunks = list(chunks)
    i = 0

    while i < len(chunks) - 1:
        current = chunks[i].splitlines(keepends=True)
        following = chunks[i + 1].splitlines(keepends=True)

        if not current or not following:
            i += 1
            continue

        last_line = current[-1].strip()
        first_line = following[0].strip()

        if not raw and last_line == '+---+':
            take = min(2, len(following))
            chunks[i] += ''.join(following[:take])
            chunks[i + 1] = ''.join(following[take:])
            if not chunks[i + 1]:
                chunks.pop(i + 1)
            continue

        if raw and re.fullmatch(r'={4,}', last_line):
            if re.fullmatch(r'={4,}', first_line):
                chunks[i] += ''.join(following[:1])
                chunks[i + 1] = ''.join(following[1:])
                if not chunks[i + 1]:
                    chunks.pop(i + 1)
                continue

            if len(following) >= 2 and re.fullmatch(r'={4,}', following[1].strip()):
                take = 2
                while take < len(following) and not following[take].strip():
                    take += 1
                if take < len(following):
                    take += 1
                chunks[i] += ''.join(following[:take])
                chunks[i + 1] = ''.join(following[take:])
                if not chunks[i + 1]:
                    chunks.pop(i + 1)
                continue

            i += 1

        return chunks
    return chunks


def adjust_split_mid(lines, mid, raw):
    n = len(lines)
    if n < 2:
        return mid

    mid = max(1, min(mid, n - 1))

    for _ in range(n):
        changed = False

        if not raw and lines[mid - 1].strip() == '+---+':
            mid = min(n - 1, mid + 2)
            changed = True

            if raw:
                left = lines[mid - 1].strip()
                right = lines[mid].strip()

                if re.fullmatch(r'={4,}', left):
                    mid = min(n - 1, mid + 2)
                    changed = True

                elif re.fullmatch(r'={4,}', right):
                    if mid >= 2 and lines[mid - 2].strip():
                        mid = max(1, mid - 1)
                        changed = True

            if not changed:
                break

        return max(1, min(mid, n - 1))


def prepare_output_paths(title, max_chars):
    out = down.downin.base_data.OUTFOLDER + '/'
    os.makedirs(f'{out}trs', exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|]', '_', title).strip()
    ai_dir = f'{out}trs\\ai_down_{safe}_{max_chars}'
    os.makedirs(ai_dir, exist_ok=True)
    return out, safe, ai_dir