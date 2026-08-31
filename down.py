import os
import re
import time
import zipfile
import shutil
import downin
from make_image import create_cover_image
import threading

from config import USE_LOCAL_AI

IS_START = False

AI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

AI_BATCH_SIZE = 32

CPU_BATCH_SIZE = 8

AI_MAX_LENGTH = 384

torch = None
AutoTokenizer = None
AutoModelForSequenceClassification = None

AI_DEVICE = None
AI_TOKENIZER = None
AI_MODEL_INSTANCE = None
AI_ENTAILMENT_INDEX = None

def setup_local_ai():
    global torch, AutoTokenizer, AutoModelForSequenceClassification
    import torch as tor
    from transformers import AutoTokenizer as autot, AutoModelForSequenceClassification as autom
    torch = tor
    AutoTokenizer = autot
    AutoModelForSequenceClassification = autom
    
    global AI_DEVICE, AI_TOKENIZER, AI_MODEL_INSTANCE, AI_ENTAILMENT_INDEX

    if not USE_LOCAL_AI:
        return False

    if torch is None or AutoTokenizer is None:
        print("\n[AI] torch 또는 transformers가 설치되어 있지 않습니다.")
        return False

    if torch.cuda.is_available():
        AI_DEVICE = torch.device("cuda")
        print(f"\n[AI] CUDA 사용: {torch.cuda.get_device_name(0)}")
    else:
        AI_DEVICE = torch.device("cpu")
        print("\n[AI] CPU fallback 실행")

    try:
        print(f"[AI] 모델 스레드 로딩 시작: {AI_MODEL}")

        AI_TOKENIZER = AutoTokenizer.from_pretrained(AI_MODEL)
        
        model = AutoModelForSequenceClassification.from_pretrained(AI_MODEL)
        model.to(AI_DEVICE)
        model.eval()
        AI_MODEL_INSTANCE = model

        id2label = AI_MODEL_INSTANCE.config.id2label
        AI_ENTAILMENT_INDEX = None

        for index, label in id2label.items():
            if "ENTAIL" in str(label).upper():
                AI_ENTAILMENT_INDEX = int(index)
                break

        if AI_ENTAILMENT_INDEX is None:
            return False

        if AI_DEVICE.type == "cuda":
            torch.cuda.empty_cache()

        print("[AI] 모델 로딩 완료")
        return True

    except Exception as e:
        print(f"[AI] 모델 로딩 실패: {e}")
        return False

def setup_local_ai_in_thread(wait=True):
    if not USE_LOCAL_AI: return
    thread = threading.Thread(target=setup_local_ai, daemon=True)
    thread.start()
    if wait:
        thread.join()

def print_progress(current, total, prefix="진행", width=30):
    if total <= 0:
        return

    percent = current / total
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)

    print(
        f"\r[{prefix}] [{bar}] {percent * 100:6.2f}% ({current}/{total})",
        end="",
        flush=True
    )

def print_ai_progress(current, total):
    print_progress(current, total, "AI 문단 분석")

def fallback_breaks(lines):
    
    transition_words = (
        "어느 날",
        "어느날",
        "그날",
        "다음 날",
        "다음날",
        "며칠 후",
        "며칠 뒤",
        "그 후",
        "잠시 후",
        "한편",
        "그때",
        "얼마 후",
        "얼마 뒤",
        "다음 순간",
        "그 순간",
    )
    
    back_start_marks = -1
    end = True
    end_in = True
    
    data = []
    
    for line in lines:
        cleaned = line.replace('「', '“').replace('」', '”').replace("｢","“").replace("｣","”").replace("<","〈").replace(">","〉")
        stripped_for_check = re.sub(r'\s+', '', cleaned)
        
        start = False
        
        if end and end_in:
            if cleaned[0] == '「' or cleaned[0] == '“' or cleaned[0] == '"' or cleaned[0] == "『":
                if back_start_marks != 1:
                    start = True
                if not ('」' in cleaned or '”' in cleaned or '"' in cleaned[1:] or "』" in cleaned):
                    end = False
                back_start_marks = 1
            elif cleaned[0] == "-" or cleaned[0] == "—" or cleaned[0] == "―":
                if back_start_marks != 2:
                    start = True
                back_start_marks = 2
            elif cleaned[0] == '(' or cleaned[0] =='（':
                if back_start_marks != 3:
                    start = True
                if not (')' in cleaned or '）' in cleaned):
                    end_in = False
                back_start_marks = 3
            else:
                if cleaned[:1] in transition_words:
                    start = True
                if cleaned[:2] in transition_words:
                    start = True
                if cleaned[:3] in transition_words:
                    start = True
                if cleaned[:4] in transition_words:
                    start = True
                if back_start_marks != 0:
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
            start = True
            back_start_marks = -1
        data.append(start)
    return data

def make_ai_context(lines, index):
    previous_line = lines[index - 1] if index > 0 else ""
    current_line = lines[index]
    next_line = lines[index + 1] if index + 1 < len(lines) else ""

    return (
        f"이전 문장:\n{previous_line}\n\n"
        f"현재 문장:\n{current_line}\n\n"
        f"다음 문장:\n{next_line}"
    )

def classify_break_batch(batch_contexts):
    if not batch_contexts:
        return []

    if AI_MODEL_INSTANCE is None or AI_TOKENIZER is None:
        return None

    if AI_DEVICE is None:
        return None
    
    print("start")

    
    normalized_contexts = []

    for context in batch_contexts:
        if context is None:
            normalized_contexts.append("")
        elif isinstance(context, str):
            normalized_contexts.append(context)
        else:
            normalized_contexts.append(str(context))

    break_hypothesis = "현재 문장 앞에서 새로운 문단이 시작되는 것이 자연스럽다."
    keep_hypothesis = "현재 문장은 이전 문장과 같은 문단에서 계속 이어지는 것이 자연스럽다."

    premises = []
    hypotheses = []

    for context in normalized_contexts:
        premises.append(context)
        hypotheses.append(break_hypothesis)
        premises.append(context)
        hypotheses.append(keep_hypothesis)

    try:
        encoded = AI_TOKENIZER(
            premises,
            hypotheses,
            padding=True,
            truncation=True,
            max_length=AI_MAX_LENGTH,
            return_tensors="pt"
        )

        encoded = {
            key: value.to(AI_DEVICE)
            for key, value in encoded.items()
        }

        with torch.inference_mode():
            outputs = AI_MODEL_INSTANCE(**encoded)
            probabilities = torch.softmax(outputs.logits, dim=-1)

        entailment_scores = probabilities[:, AI_ENTAILMENT_INDEX]

        result = []

        for i in range(0, len(normalized_contexts) * 2, 2):
            break_score = float(entailment_scores[i].item())
            keep_score = float(entailment_scores[i + 1].item())

            margin = break_score - keep_score

            
            should_break = (
                break_score >= 0.64 and
                margin >= 0.16
            )

            result.append(should_break)

        del encoded
        del outputs
        del probabilities
        del entailment_scores

        if AI_DEVICE.type == "cuda":
            torch.cuda.empty_cache()

        return result

    except RuntimeError as e:
        if "out of memory" in str(e).lower() and AI_DEVICE.type == "cuda":
            print("\n[AI] CUDA 메모리 부족. batch 크기를 줄여 다시 시도합니다.")
            torch.cuda.empty_cache()

            if len(normalized_contexts) > 1:
                middle = len(normalized_contexts) // 2

                left = classify_break_batch(normalized_contexts[:middle])
                right = classify_break_batch(normalized_contexts[middle:])

                if left is not None and right is not None:
                    return left + right

        print(f"\n[AI] GPU 분류 오류: {e}")
        return None

    except Exception as e:
        print(f"\n[AI] 문단 분류 오류: {e}")
        return None

def ask_local_ai_for_breaks(lines):
    if not lines:
        return []

    if not USE_LOCAL_AI:
        print("USE_LOCAL_AI")
        return fallback_breaks(lines)
    
    if AI_MODEL_INSTANCE is None:
        print("AI_MODEL_INSTANCE")
        return fallback_breaks(lines)

    MAX_CHARS = 5000
    total = len(lines)
    result = [False] * total

    
    batches = []
    current_batch = []
    current_chars = 0
    current_start = 0

    for i, line in enumerate(lines):
        line = str(line)
        line_len = len(line) + 1  

        if current_batch and current_chars + line_len > MAX_CHARS:
            batches.append((current_start, current_batch))
            current_batch = []
            current_chars = 0
            current_start = i

        current_batch.append(line)
        current_chars += line_len

    if current_batch:
        batches.append((current_start, current_batch))

    
    for start_index, batch_lines in batches:
        try:
            contexts = [
                make_ai_context(batch_lines, i)
                for i in range(len(batch_lines))
            ]
            batch_result = classify_break_batch(contexts)

            for j, value in enumerate(batch_result):
                index = start_index + j
                if index < total:
                    result[index] = bool(value)

        except Exception as e:
            print(f"[AI 문단 분석] 배치 처리 오류: {e}")

    
    if result:
        result[0] = False

    return result

def ai_paragraph_breaks(lines):
    if not lines:
        return []
    return ask_local_ai_for_breaks(lines)

def extract_number(filename):
    match = re.search(r'(\d+)번', filename)
    return int(match.group(1)) if match else 9999

def create_epub_from_merged_txt(
    input_txt_path="", base_dir=".", txt_value=""
):
    global IS_START
    
    if USE_LOCAL_AI:
        while AI_MODEL_INSTANCE is None:
            time.sleep(1)  
    
    while IS_START:
        time.sleep(1)  
        
    while IS_START: pass
    IS_START = True
    
    
    if txt_value != "":
        content = txt_value
    else:
        if not os.path.exists(input_txt_path):
            return False

        try:
            with open(input_txt_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(input_txt_path, "r", encoding="cp949") as f:
                content = f.read()

    
    content = content.replace("\r\n", "\n").replace("\n\n", "\n")
    content = content.replace('SPLIT_POINT = "+---+"', "+---+")

    
    delimiter = getattr(downin, "SPLIT_POINT", "+---+")
    sections = [s.strip() for s in content.split(delimiter) if s.strip()]

    if not sections:
        return False

    
    header_lines = [
        line.strip() for line in sections[0].splitlines() if line.strip()
    ]
    main_title = header_lines[0] if len(header_lines) > 0 else "Untitled"
    sub_title = header_lines[1] if len(header_lines) > 1 else ""

    book_title = (
        f"{main_title} | {sub_title}" if sub_title else main_title
    )
    book_title = book_title.replace("<", "〈").replace(">", "〉")

    
    build_dir = os.path.join(base_dir, "temp_epub_build_with_cover")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(os.path.join(build_dir, "META-INF"), exist_ok=True)
    os.makedirs(os.path.join(build_dir, "OEBPS"), exist_ok=True)
    os.makedirs(os.path.join(build_dir, "OEBPS", "css"), exist_ok=True)

    
    with open(
        os.path.join(build_dir, "mimetype"), "w", encoding="utf-8"
    ) as f:
        f.write("application/epub+zip")

    
    container_xml = """<?xml version="1.0" encoding="UTF-8"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>"""
    with open(
        os.path.join(build_dir, "META-INF", "container.xml"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(container_xml)

    
    css_content = """@charset "utf-8";

html { margin: 0; padding: 0; }
body {
    margin: 0;
    padding: 0;
    font-family: serif;
    line-height: 1.75;
    word-break: keep-all;
    overflow-wrap: break-word;
    -webkit-text-size-adjust: none;
}
p {
    margin: 0;
    padding: 0;
    text-indent: 1em;
    text-align: left;
}
p + p {
    margin-top: 0.3em;
}
strong, b { font-weight: bold; }
.chapter-title {
    margin: 0 0 2.2em 0;
    padding: 0;
    text-align: center;
    text-indent: 0;
    font-size: 1.35em;
    font-weight: bold;
    line-height: 1.5;
    page-break-after: avoid;
    break-after: avoid-page;
}
.chapter-title + p { text-indent: 0; }
.center {
    margin: 1.2em 0;
    padding: 0;
    text-align: center;
    text-indent: 0;
}
.no-indent { text-indent: 0; }
@page { margin: 5%; }"""

    with open(
        os.path.join(build_dir, "OEBPS", "css", "style.css"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(css_content)

    
    create_cover_image(build_dir, book_title)

    manifest_items = [
        '<item id="css" href="css/style.css" media-type="text/css"/>',
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="cover-image" href="cover.png" media-type="image/png"/>',
    ]
    spine_items = []
    toc_items = []

    
    title_html_content = f"""<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{book_title}</title><link rel="stylesheet" type="text/css" href="css/style.css"/></head><body><div style="width:100vw; height: 100vh; display: flex; align-items: center;"><div style="text-align:center; margin: 0 auto;"> <h2 class="subtitle">{main_title}</h2><hr/><h3>{sub_title}</h3></div></div></body></html>"""

    ch_id, ch_filename = "title", "title.xhtml"
    with open(
        os.path.join(build_dir, "OEBPS", ch_filename), "w", encoding="utf-8"
    ) as f:
        f.write(title_html_content)

    manifest_items.append(
        f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>'
    )
    spine_items.append(f'<itemref idref="{ch_id}"/>')
    toc_items.append(
        f'<navPoint id="{ch_id}" playOrder="0"><navLabel><text>title</text></navLabel><content src="{ch_filename}"/></navPoint>'
    )

    
    chapter_sections = sections[1:]
    idx = 1
    total_chapters = len(chapter_sections)

    for chapter_index, chapter_text in enumerate(chapter_sections, 1):
        if "print_progress" in globals():
            print_progress(chapter_index, total_chapters, "EPUB 변환")

        lines = [
            line.strip()
            for line in chapter_text.splitlines()
            if line.strip()
        ]
        if not lines:
            continue

        subtitle = (
            lines[0]
            .replace("**", "")
            .replace("<", "〈")
            .replace(">", "〉")
        )
        raw_body_lines = lines[1:]

        first_body_line = raw_body_lines[0] if raw_body_lines else ""

        
        if first_body_line.startswith("<p") or first_body_line.startswith(
            "<div"
        ):
            paragraphs = "\n".join(raw_body_lines)
        else:
            
            merged_body_lines = (
                raw_body_lines
            )

            
            ai_breaks = (
                ai_paragraph_breaks(merged_body_lines)
                if "ai_paragraph_breaks" in globals()
                else [False] * len(merged_body_lines)
            )
            

            processed_lines = []
            back_center = False
            for line_index, line in enumerate(merged_body_lines):
                
                cleaned = (
                    line.replace("「", "“")
                    .replace("」", "”")
                    .replace("｢", "“")
                    .replace("｣", "”")
                    .replace("<", "〈")
                    .replace(">", "〉")
                    .replace("（", "'")
                    .replace("）", "'")
                    if globals().get("USE_Quotation_marks", True)
                    else line
                )

                cleaned = re.sub(
                    r"\*\*(.*?)\*\*", r"<b>\1</b>", cleaned
                )
                stripped_for_check = re.sub(r"\s+", "", cleaned)

                
                start = (
                    "<p><br/></p>"
                    if (line_index > 0 and ai_breaks[line_index]) or line_index == 0 or back_center
                    else ""
                )

                
                if globals().get(
                    "USE_Center_marks", True
                ) and re.fullmatch(
                    r'''[^\w.\"'\'「」『』“”‘’!?。…]{1,}''',
                    stripped_for_check,
                ):
                    processed_lines.append(
                        f"<p><br/></p><p class='center'>{cleaned}</p>"
                    )
                    back_center = True
                else:
                    processed_lines.append(f"{start}<p>{cleaned}</p>")
                    back_center = False

            paragraphs = "\n".join(processed_lines)

        chapter_html_content = f"""<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{subtitle}</title><link rel="stylesheet" type="text/css" href="css/style.css"/></head><body><h2 class="subtitle chapter-title">{subtitle}</h2>{paragraphs}</body></html>"""

        ch_id, ch_filename = f"chapter_{idx}", f"chapter_{idx}.xhtml"
        with open(
            os.path.join(build_dir, "OEBPS", ch_filename),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(chapter_html_content)

        manifest_items.append(
            f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'<itemref idref="{ch_id}"/>')
        toc_items.append(
            f'<navPoint id="{ch_id}" playOrder="{idx}"><navLabel><text>{subtitle}</text></navLabel><content src="{ch_filename}"/></navPoint>'
        )
        idx += 1

    if "print_progress" in globals():
        print()

    
    manifest_str = "\n ".join(manifest_items)
    spine_str = "\n ".join(spine_items)
    toc_str = "\n".join(toc_items)

    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{book_title}</dc:title>
    <dc:language>ko</dc:language>
    <dc:identifier id="BookId">urn:uuid:550e8400-e29b-41d4-a716-446655440000</dc:identifier>
    <meta name="cover" content="cover-image"/> 
  </metadata>
  <manifest>
    {manifest_str}
  </manifest>
  <spine toc="ncx">
    {spine_str}
  </spine>
</package>"""

    with open(
        os.path.join(build_dir, "OEBPS", "content.opf"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(content_opf)

    toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd"><ncx xmlns="http://www.daisy.org/z3986/2005/ncx-1.0.dtd" version="1.0"><head><meta name="dtb:uid" content="urn:uuid:550e8400-e29b-41d4-a716-446655440000"/><meta name="dtb:depth" content="1"/></head><docTitle><text>{book_title}</text></docTitle><navMap>{toc_str}</navMap></ncx>"""

    with open(
        os.path.join(build_dir, "OEBPS", "toc.ncx"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(toc_ncx)
    out_folder = getattr(downin, "OUTFOLDER", "./out/")
    if not os.path.exists(out_folder):
        os.mkdir(out_folder)
    out_folder = os.path.join(out_folder, "epub")
    if not os.path.exists(out_folder):
        os.mkdir(out_folder)
    output_epub_path = os.path.join(
        out_folder, re.sub(r'[\/:*?"<>|]', "_", book_title) + ".epub"
    )

    with zipfile.ZipFile(
        output_epub_path, "w", zipfile.ZIP_DEFLATED
    ) as epub_zip:
        epub_zip.write(
            os.path.join(build_dir, "mimetype"),
            "mimetype",
            compress_type=zipfile.ZIP_STORED,
        )
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                if file == "mimetype":
                    continue
                full_path = os.path.join(root, file)
                epub_zip.write(
                    full_path, os.path.relpath(full_path, build_dir)
                )

    shutil.rmtree(build_dir)
    IS_START = False
    return True

setup_local_ai_in_thread(wait=False)