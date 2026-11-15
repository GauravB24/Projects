# quiz_generator.py
import re
import random
from typing import List

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

QUIZ_MODEL_NAME = "google/flan-t5-small"
_QA_PIPELINE = None

def load_quiz_pipeline(model_name: str = QUIZ_MODEL_NAME, force_cpu: bool = True):
    global _QA_PIPELINE
    if _QA_PIPELINE is not None:
        return _QA_PIPELINE
    if not TRANSFORMERS_AVAILABLE:
        def fallback(prompt: str, **kwargs):
            return [{"generated_text": ""}]
        _QA_PIPELINE = fallback
        return _QA_PIPELINE
    try:
        device = -1 if force_cpu else 0
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        _QA_PIPELINE = pipeline("text2text-generation", model=model, tokenizer=tokenizer, device=device)
        return _QA_PIPELINE
    except Exception:
        def fallback(prompt: str, **kwargs):
            return [{"generated_text": ""}]
        _QA_PIPELINE = fallback
        return _QA_PIPELINE

def make_quiz_prompt(text: str, n_questions: int = 5) -> str:
    return (
        f"Generate {n_questions} multiple-choice questions from the text below.\n"
        "Format each question block exactly as:\n"
        "Q1. <question>?\nA) <option A>\nB) <option B>\nC) <option C>\nD) <option D>\n"
        "Answer: <A/B/C/D>\nExplanation: <one short sentence>\n\n"
        f"Text:\n{text}\n\nProduce exactly the requested number of questions."
    )

def parse_quiz_output(raw: str, expected_qs: int = 5) -> List[dict]:
    text = raw.replace("\r\n", "\n").strip()
    parts = re.split(r'\n(?=Q\d+\.)', text, flags=re.IGNORECASE)
    questions = []
    for part in parts:
        if not part.strip():
            continue
        qm = re.search(r'Q\d+\.\s*(.+?)(?:\n|$)', part, flags=re.IGNORECASE | re.DOTALL)
        if not qm:
            continue
        qtext = qm.group(1).strip()
        opts = re.findall(r'^[\s]*([A-D])\)\s*(.+)$', part, flags=re.IGNORECASE | re.MULTILINE)
        options_sorted = [None]*4
        if opts:
            for letter, opt in opts:
                idx = ord(letter.upper()) - 65
                if 0 <= idx < 4:
                    options_sorted[idx] = opt.strip()
            if any(o is None for o in options_sorted):
                options_sorted = [o.strip() for _, o in opts][:4]
        else:
            inline = re.search(r"A\)\s*(.*?)\s+B\)\s*(.*?)\s+C\)\s*(.*?)\s+D\)\s*(.*)", part, flags=re.IGNORECASE | re.DOTALL)
            if inline:
                options_sorted = [inline.group(i).strip() for i in range(1,5)]
            else:
                options_sorted = []

        ansm = re.search(r'Answer:\s*([A-D])', part, flags=re.IGNORECASE)
        answer = ansm.group(1).upper() if ansm else None

        explm = re.search(r'Explanation:\s*(.+)', part, flags=re.IGNORECASE | re.DOTALL)
        expl = explm.group(1).strip() if explm else "No explanation."

        if qtext and len(options_sorted) == 4:
            questions.append({
                "question": qtext,
                "options": options_sorted,
                "answer": answer if answer else "A",
                "explanation": expl
            })
        if len(questions) >= expected_qs:
            break
    return questions

def assemble_quiz(parsed: List[dict], expected_qs: int = 5) -> List[dict]:
    quiz = []
    for item in parsed:
        opts = item["options"][:]
        ans = (item.get("answer") or "A")[0].upper()
        try:
            correct_text = item["options"][ord(ans) - 65]
        except Exception:
            correct_text = item["options"][0]
        random.shuffle(opts)
        try:
            new_idx = opts.index(correct_text)
        except ValueError:
            new_idx = 0
        new_letter = chr(65 + new_idx)
        quiz.append({
            "question": item["question"],
            "options": opts,
            "answer": new_letter,
            "explanation": item.get("explanation", "No explanation provided.")
        })
        if len(quiz) >= expected_qs:
            break
    return quiz

def _short_clip(s: str, max_words: int = 16) -> str:
    words = s.split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;:") + "..."

def _perturb_text(s: str) -> str:
    nums = re.findall(r'\d+', s)
    if nums:
        try:
            n = int(nums[0])
            return s.replace(str(n), str(n + random.choice([-1, 1, 2])), 1)
        except Exception:
            pass
    swaps = [("increase","decrease"), ("rise","fall"), ("more","less"), ("gain","lose")]
    for a,b in swaps:
        if re.search(rf'\b{a}\b', s, flags=re.IGNORECASE):
            return re.sub(rf'(?i)\b{a}\b', b, s, count=1)
    words = s.split()
    if len(words) > 4:
        i = random.randrange(0, len(words)-1)
        words[i], words[i+1] = words[i+1], words[i]
        return " ".join(words)
    return s + " (not)"

def synthesize_questions_from_text(text: str, needed: int) -> List[dict]:
    if not text or not text.strip():
        return [{
            "question": "No content provided — choose the best statement:",
            "options": ["No content (A)", "No content (B)", "No content (C)", "No content (D)"],
            "answer": "A",
            "explanation": "No input."
        } for _ in range(needed)]

    sents = re.split(r'(?<=[.!?])\s+', text)
    candidates = [s.strip().rstrip('.') for s in sents if 20 <= len(s.strip()) <= 300]
    if len(candidates) < needed:
        clauses = re.split(r',\s*', text)
        candidates.extend([c.strip().rstrip('.') for c in clauses if len(c.strip()) > 20])

    seen = set()
    cleaned = []
    for c in candidates:
        kc = c.lower()
        if kc in seen:
            continue
        seen.add(kc)
        cleaned.append(c)
    if not cleaned:
        cleaned = [text.strip()[:200]]

    questions = []
    for i, base_full in enumerate(cleaned[:needed]):
        base = _short_clip(base_full, max_words=18)
        others = [_short_clip(c, max_words=14) for j,c in enumerate(cleaned) if j != i]
        distractors = []
        for o in others:
            if len(distractors) >= 3:
                break
            if o.lower() == base.lower() or base.lower() in o.lower():
                continue
            distractors.append(o)
        attempts = 0
        while len(distractors) < 3 and attempts < 8:
            p = _perturb_text(base_full)
            p_short = _short_clip(p)
            if p_short.lower() not in [d.lower() for d in distractors] and p_short.lower() != base.lower():
                distractors.append(p_short)
            attempts += 1
        while len(distractors) < 3:
            distractors.append(base + " (not)")

        opts = [base] + distractors[:3]
        seen_o = set()
        uniq = []
        for o in opts:
            key = o.lower().strip()
            if key in seen_o:
                t = 1
                new_o = f"{o} ({t})"
                while new_o.lower().strip() in seen_o:
                    t += 1
                    new_o = f"{o} ({t})"
                o = new_o
            seen_o.add(o.lower().strip())
            uniq.append(o)

        random.shuffle(uniq)
        correct_letter = chr(65 + uniq.index(base)) if base in uniq else "A"
        questions.append({
            "question": f"Which of the following is TRUE according to the passage?",
            "options": uniq,
            "answer": correct_letter,
            "explanation": f"Because the passage states: {base_full}."
        })

    while len(questions) < needed:
        k = len(questions) + 1
        opts = [
            f"A specific fact about the passage ({k})",
            f"A contradictory statement ({k})",
            f"A partly true statement ({k})",
            f"An unrelated statement ({k})"
        ]
        questions.append({
            "question": f"Pick the most accurate statement for item {k}:",
            "options": opts,
            "answer": "A",
            "explanation": "Synthetic fallback."
        })

    return questions[:needed]

def generate_quiz_from_text(text: str, n_questions: int = 5, use_model: bool = True) -> List[dict]:
    pipeline_fn = load_quiz_pipeline()
    parsed = []
    if use_model and pipeline_fn is not None:
        try:
            prompt = make_quiz_prompt(text, n_questions)
            out = pipeline_fn(prompt, max_new_tokens=512, do_sample=True, top_p=0.95, temperature=0.8, num_return_sequences=1)
            raw = ""
            if isinstance(out, list) and len(out) > 0:
                first = out[0]
                if isinstance(first, dict):
                    raw = first.get("generated_text", "") or first.get("summary_text", "")
                elif isinstance(first, str):
                    raw = first
            elif isinstance(out, dict):
                raw = out.get("generated_text", "") or out.get("summary_text", "")
            if raw:
                parsed = parse_quiz_output(raw, expected_qs=n_questions)
        except Exception:
            parsed = []

    if len(parsed) < n_questions:
        needed = n_questions - len(parsed)
        parsed.extend(synthesize_questions_from_text(text, needed))

    final = assemble_quiz(parsed, expected_qs=n_questions)
    if len(final) < n_questions:
        final.extend(synthesize_questions_from_text(text, n_questions - len(final)))
    return final[:n_questions]
