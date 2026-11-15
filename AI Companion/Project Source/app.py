# app.py — AI Study Companion (Full feature — Version C)
import re
import random
import streamlit as st
import torch
from typing import List, Tuple, Optional
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

st.set_page_config(page_title="📚 AI Study Companion", page_icon="📚", layout="wide")

# ------------------- User settings -------------------
# Models (you can change these later)
SUMMARY_MODEL = "t5-small"               # lightweight summarizer
QUIZ_MODEL = "google/flan-t5-base"       # quiz generation (good balance)

# ------------------- Device detection -------------------
USE_CUDA = torch.cuda.is_available()
st.sidebar.write("Device:", "GPU (cuda)" if USE_CUDA else "CPU")

# ------------------- Load & cache model pipelines -------------------
@st.cache_resource(show_spinner=False)
def load_summarizer(model_name: str, use_cuda: bool):
    """
    Load summarizer. For the small model we'll let pipeline handle device argument
    for CPU (-1) or GPU (None) depending on how model is loaded.
    """
    if use_cuda:
        # load on GPU with device_map so model is placed by accelerate
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        # do not pass device argument to pipeline because model has device_map
        return pipeline("summarization", model=model, tokenizer=tokenizer)
    else:
        # CPU: load normally and pass device=-1 to pipeline
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        return pipeline("summarization", model=model, tokenizer=tokenizer, device=-1)

@st.cache_resource(show_spinner=False)
def load_quiz_pipeline(model_name: str, use_cuda: bool):
    """
    Load quiz model. If CUDA available, load with device_map='auto' & fp16 and DO NOT pass device
    into pipeline (accelerate already placed it). If CPU, load normally and pass device=-1.
    """
    if use_cuda:
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, torch_dtype=torch.float16, device_map="auto")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        return pipeline("text2text-generation", model=model, tokenizer=tokenizer)
    else:
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        return pipeline("text2text-generation", model=model, tokenizer=tokenizer, device=-1)


with st.spinner("Loading models (first run may take longer)..."):
    summarizer = load_summarizer(SUMMARY_MODEL, USE_CUDA)
    qa_gen = load_quiz_pipeline(QUIZ_MODEL, USE_CUDA)

# ------------------- Helpers: prompt + parsing -------------------
def make_quiz_prompt(text: str, n_questions: int = 5) -> str:
    """
    Robust explicit prompt that requests N questions in a parseable format.
    Each question will be on its own block like:
    Q1. Question text?
    A) option A
    B) option B
    C) option C
    D) option D
    Answer: B
    Explanation: short explanation sentence
    """
    prompt = f"""Generate {n_questions} high-quality multiple-choice questions from the text below.
Requirements (STRICT):
- Produce exactly {n_questions} questions.
- Each question must have 4 labeled options: A) B) C) D)
- After each question block include a single line "Answer: X" where X is A/B/C/D
- After Answer include "Explanation: <one short sentence explaining why the answer is correct>"
- Do NOT include extra text, numbering other than Q1./Q2., or the original passage.

Format example (exact):
Q1. <question text>?
A) Option A
B) Option B
C) Option C
D) Option D
Answer: B
Explanation: Because ...

Text:
{text}

Now produce the questions exactly as requested."""
    return prompt

def parse_quiz_output(raw: str, expected_qs: int = 5) -> List[dict]:
    """
    Parse model raw output into list of question dicts:
    { "question": str, "options": [optA,optB,optC,optD], "answer": "A", "explanation": str }
    This parser is robust to common small format variations.
    """
    # Normalize newlines
    text = raw.replace("\r\n", "\n").strip()

    # Split by question blocks: look for lines starting with Q or Q1.
    parts = re.split(r'\n(?=Q\d*\.)', text, flags=re.IGNORECASE)
    questions = []
    for part in parts:
        if not part.strip():
            continue
        # Extract question line
        q_match = re.search(r'Q\d*\.\s*(.+?)(?:\n|$)', part, flags=re.IGNORECASE | re.DOTALL)
        if not q_match:
            continue
        question_text = q_match.group(1).strip()
        # Extract options (A/B/C/D)
        opts = re.findall(r'^[\s]*([A-D])\)\s*(.+)$', part, flags=re.IGNORECASE | re.MULTILINE)
        if opts and len(opts) >= 4:
            # maintain order A..D
            opts_sorted = [None]*4
            for letter, text_opt in opts:
                idx = ord(letter.upper()) - 65
                if 0 <= idx < 4:
                    opts_sorted[idx] = text_opt.strip()
            # if some missing, fallback to first four found
            if any(o is None for o in opts_sorted):
                opts_sorted = [t.strip() for _, t in opts][:4]
        else:
            # try inline A) ... B) ... pattern
            inline = re.search(r'A\)\s*(.*?)\s+B\)\s*(.*?)\s+C\)\s*(.*?)\s+D\)\s*(.*)', part, flags=re.IGNORECASE | re.DOTALL)
            if inline:
                opts_sorted = [inline.group(i).strip() for i in range(1,5)]
            else:
                opts_sorted = []

        # Extract Answer
        ans_match = re.search(r'Answer:\s*([A-D])', part, flags=re.IGNORECASE)
        ans = ans_match.group(1).upper() if ans_match else None

        # Explanation
        expl_match = re.search(r'Explanation:\s*(.+)', part, flags=re.IGNORECASE | re.DOTALL)
        expl = expl_match.group(1).strip() if expl_match else ""

        if question_text and len(opts_sorted) == 4:
            questions.append({
                "question": question_text,
                "options": opts_sorted,
                "answer": ans if ans else "A",
                "explanation": expl if expl else "No explanation provided."
            })
        # stop if enough collected
        if len(questions) >= expected_qs:
            break

    return questions

def assemble_quiz_from_parsed(parsed: List[dict]) -> List[dict]:
    """
    Shuffle options (for variability) while keeping the correct answer mapping.
    Returns new list of question dicts with options shuffled and answer letter updated.
    """
    quiz = []
    for q in parsed:
        opts = q["options"][:]
        correct_letter = q["answer"]
        # map old correct text
        if correct_letter and 65 <= ord(correct_letter) <= 90:
            try:
                correct_text = q["options"][ord(correct_letter)-65]
            except Exception:
                correct_text = q["options"][0]
        else:
            correct_text = q["options"][0]
        # shuffle
        random.shuffle(opts)
        new_idx = opts.index(correct_text)
        new_letter = chr(65 + new_idx)
        quiz.append({
            "question": q["question"],
            "options": opts,
            "answer": new_letter,
            "explanation": q["explanation"]
        })
    return quiz

# ------------------- Session state init -------------------
if "quiz" not in st.session_state:
    st.session_state.quiz: List[dict] = []
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "answered" not in st.session_state:
    st.session_state.answered = False
if "selected" not in st.session_state:
    st.session_state.selected: Optional[str] = None

# ------------------- UI: Header -------------------
st.title("📚 AI Study Companion — Summarize & Quiz")
st.write("Paste lecture notes below. Generate a detailed summary and an interactive 5-question MCQ quiz (with short explanations).")

text_input = st.text_area("Paste your lecture notes here:", height=300)

# ------------------- Summary generation -------------------
st.subheader("📌 Summary")
if st.button("Generate Summary"):
    if not text_input.strip():
        st.warning("Please paste some lecture notes first.")
    else:
        with st.spinner("Summarizing..."):
            try:
                out = summarizer(text_input, max_length=220, min_length=60, do_sample=False)
                summary = out[0].get("summary_text", "").strip()
            except Exception as e:
                st.error(f"Summarizer error: {e}")
                summary = ""
        if summary:
            # show bullet points quickly
            parts = re.split(r'\.\s+', summary)
            bullets = []
            for p in parts:
                p = p.strip()
                if p:
                    if not p.endswith("."):
                        p = p + "."
                    bullets.append("• " + p)
            st.success("\n".join(bullets))
        else:
            st.info("No summary produced.")

# ------------------- Quiz generation (improved prompt) -------------------
st.subheader("📝 Generate Quiz (5 MCQs)")
if st.button("Generate 5 MCQs with explanations"):
    if not text_input.strip():
        st.warning("Please paste lecture notes first.")
    else:
        with st.spinner("Creating summary (for quiz prompt)..."):
            try:
                # create a concise summary to feed into the question generator
                summary = summarizer(text_input, max_length=160, min_length=40, do_sample=False)[0].get("summary_text", "")
            except Exception as e:
                st.error(f"Summarizer error (for quiz prompt): {e}")
                summary = text_input[:1024]

        prompt = make_quiz_prompt(summary, n_questions=5)

        with st.spinner("Generating quiz questions (this may take a moment)..."):
            try:
                raw = qa_gen(prompt, max_new_tokens=512, do_sample=True, top_p=0.95, temperature=0.8, num_return_sequences=1)[0].get("generated_text", "")
            except Exception as e:
                st.error(f"Quiz generation error: {e}")
                raw = ""

        parsed = parse_quiz_output(raw, expected_qs=5)
        if len(parsed) < 5:
            # as a fallback, try generating questions one-by-one using bullets
            # create up to 5 bullets
            bullets = re.split(r'(?<=[.!?])\s+', summary)
            bullets = [b for b in bullets if b.strip()][:5]
            parsed = []
            for i, b in enumerate(bullets, start=1):
                single_prompt = f"""Create 1 concise multiple-choice question only from this single sentence/phrase:
Bullet:
{b}

Format:
Q1. <question>?
A) <optA>
B) <optB>
C) <optC>
D) <optD>
Answer: <A/B/C/D>
Explanation: <one short sentence>
"""
                try:
                    one_raw = qa_gen(single_prompt, max_new_tokens=180, do_sample=True, temperature=0.7)[0].get("generated_text", "")
                except Exception:
                    one_raw = ""
                p = parse_quiz_output(one_raw, expected_qs=1)
                if p:
                    parsed.extend(p)
                if len(parsed) >= 5:
                    break

        if not parsed:
            st.error("Failed to generate quiz. Try a longer input or regenerate.")
        else:
            quiz = assemble_quiz_from_parsed(parsed)
            # Only keep first 5
            st.session_state.quiz = quiz[:5]
            st.session_state.q_index = 0
            st.session_state.score = 0
            st.session_state.answered = False
            st.session_state.selected = None
            st.success(f"Generated {len(st.session_state.quiz)} questions. Scroll down to take the quiz.")

# ------------------- Interactive Quiz UI -------------------
st.subheader("📝 Interactive Quiz (Take it now)")

if not st.session_state.quiz:
    st.info("No quiz yet. Use 'Generate 5 MCQs with explanations' to create one.")
else:
    total = len(st.session_state.quiz)
    idx = st.session_state.q_index
    # Guard against index overflow
    if idx >= total:
        st.success(f"🎉 Quiz completed — Score: {st.session_state.score}/{total}")
        if st.button("Restart (generate new quiz)"):
            st.session_state.quiz = []
            st.session_state.q_index = 0
            st.session_state.score = 0
            st.session_state.answered = False
            st.session_state.selected = None
        st.stop()

    qobj = st.session_state.quiz[idx]
    st.markdown(f"**Q{idx+1}. {qobj['question']}**")

    # Show options; if unanswered - clickable buttons; if answered - colored blocks
    for i, opt_text in enumerate(qobj["options"]):
        letter = chr(65 + i)
        btn_key = f"q{idx}_opt{letter}"

        if not st.session_state.answered:
            clicked = st.button(f"{letter}) {opt_text}", key=btn_key)
            if clicked:
                # register answer immediately
                st.session_state.selected = letter
                st.session_state.answered = True
                # score update
                if letter == qobj["answer"]:
                    st.session_state.score += 1
                # Rerun to show highlights and explanation immediately
                st.experimental_rerun()
        else:
            # After answering: color highlights
            if letter == qobj["answer"]:
                bg = "#2ecc71"   # green
                color = "white"
                prefix = "✅"
            elif st.session_state.selected == letter:
                bg = "#ff6b6b"   # red
                color = "white"
                prefix = "❌"
            else:
                bg = "#f0f0f0"
                color = "black"
                prefix = ""
            st.markdown(
                f"""<div style="padding:10px;border-radius:6px;margin-bottom:6px;background:{bg};color:{color};">
<strong>{prefix} {letter})</strong> {opt_text}</div>""",
                unsafe_allow_html=True
            )

    # Show explanation once answered
    if st.session_state.answered:
        # show the explanation for the current question
        st.info(f"Explanation: {qobj.get('explanation', 'No explanation provided.')}")

        # Next / Finish controls
        if idx < total - 1:
            if st.button("➡️ Next"):
                st.session_state.q_index += 1
                st.session_state.answered = False
                st.session_state.selected = None
                # do not reset score
                # let rerun happen naturally on next render
        else:
            # Last question: show Finish button and disabled Next indicator
            st.button("Next (last question)", disabled=True)
            if st.button("Finish Quiz"):
                st.session_state.q_index = total
                # show final by letting loop continue
                st.experimental_rerun()
    else:
        st.caption("Select an option to answer this question.")

# ------------------- Footer -------------------
st.write("---")
st.caption("Mode: Full-feature (detailed summary + 5 MCQs with explanations). Use longer/clearer lecture notes for better questions.")
