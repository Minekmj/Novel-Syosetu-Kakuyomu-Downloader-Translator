import re
import threading

from src.system.config import USE_LOCAL_AI
from src.system.load_save import load_data

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
        return fallback_breaks(lines)
    
    if AI_MODEL_INSTANCE is None:
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