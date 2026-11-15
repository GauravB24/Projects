# app1.py
import streamlit as st
from typing import List
import quiz_generator
import summarizer

st.set_page_config(page_title="AI Study Companion (Dark)", page_icon="📚", layout="wide")

NUM_QUESTIONS = 5

def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        st.session_state["_rerun_counter"] = st.session_state.get("_rerun_counter", 0) + 1

# ---------- Dark theme CSS (high contrast, accessible) ----------
st.markdown(
    """
    <style>
    /* overall dark app */
    .stApp, .main {
        background-color: #0b0f13 !important;
        color: #e6eef6 !important;
    }
    .block-container {
        padding: 1.2rem 2rem;
        max-width: 1200px;
    }
    h1, h2, h3 {
        color: #f7fbff !important;
    }
    /* option container: card style */
    .opt-card {
        display:flex;
        align-items:flex-start;
        gap:10px;
        padding:12px 14px;
        margin:8px 0;
        border-radius:10px;
        background: #111418;
        border: 1px solid rgba(255,255,255,0.06);
        color: #e6eef6;
        transition: transform 0.09s ease, box-shadow 0.09s ease;
    }
    .opt-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 22px rgba(0,0,0,0.5);
        cursor: pointer;
    }
    .opt-prefix {
        width:48px;
        font-weight:700;
    }
    .opt-text {
        flex:1;
        color: #e6eef6;
        line-height:1.35;
    }

    /* correct/wrong states */
    .opt-card.correct {
        background: linear-gradient(90deg,#0f9d58,#0b7a44) !important;
        color: #ffffff !important;
        border: none !important;
    }
    .opt-card.wrong {
        background: linear-gradient(90deg,#c62828,#8b1f1f) !important;
        color: #ffffff !important;
        border: none !important;
    }

    /* hide button visuals (we use invisible small buttons as click handlers) */
    .invis-btn > button {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        min-width: 0 !important;
        min-height: 0 !important;
        color: inherit !important;
    }

    /* Next / control buttons style */
    .stButton>button {
        background: #0b6fb5 !important;
        color: white !important;
        border-radius: 8px !important;
        padding: .45rem .8rem !important;
        box-shadow:none !important;
    }
    .stButton>button:hover {
        filter:brightness(1.06);
    }

    /* small responsive fix for long option text */
    .opt-text { word-break: break-word; white-space: pre-wrap; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Session init ----------
if "quiz" not in st.session_state:
    st.session_state.quiz = []
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "score" not in st.session_state:
    st.session_state.score = 0

st.title("📚 AI Study Companion — Dark UI")
st.write("Paste lecture notes. Generate a summary and a 5-question interactive quiz. Hover the options; click to answer.")

text_input = st.text_area("Paste lecture notes here:", height=300)

# ---------- Summary ----------
st.subheader("📌 Summary")
if st.button("Generate Summary", key="gen_summary"):
    if not text_input.strip():
        st.warning("Please paste some lecture notes first.")
    else:
        with st.spinner("Summarizing..."):
            summ_pipeline = summarizer.load_summarizer()
            short_summary = summarizer.safe_summarize(text_input, max_length=180, min_length=40, summarizer=summ_pipeline)
        if short_summary:
            st.success(short_summary)
        else:
            st.info("No summary produced; showing preview.")
            st.write(text_input[:800] + ("..." if len(text_input) > 800 else ""))

# ---------- Generate Quiz ----------
st.subheader(f"📝 Generate {NUM_QUESTIONS} MCQs")
if st.button(f"Generate {NUM_QUESTIONS} MCQs with explanations", key="gen_quiz"):
    if not text_input.strip():
        st.warning("Please paste lecture notes first.")
    else:
        with st.spinner("Generating quiz..."):
            summ_pipeline = summarizer.load_summarizer()
            short_summary = summarizer.safe_summarize(text_input, max_length=150, min_length=40, summarizer=summ_pipeline)
            prompt_text = short_summary if short_summary else text_input[:1000]
            quiz = quiz_generator.generate_quiz_from_text(prompt_text, n_questions=NUM_QUESTIONS, use_model=True)
            st.session_state.quiz = quiz
            st.session_state.q_index = 0
            st.session_state.score = 0
            # clear per-question keys
            for k in list(st.session_state.keys()):
                if isinstance(k, str) and (k.startswith("answered_") or k.startswith("selected_") or k.startswith("wrongs_") or k.startswith("scored_")):
                    del st.session_state[k]
            st.success(f"Generated {len(quiz)} questions. Scroll down to take the quiz.")

# ---------- Interactive Quiz UI ----------
st.subheader("📝 Interactive Quiz (take now)")

if not st.session_state.quiz:
    st.info("No quiz generated yet. Click Generate to create questions.")
else:
    quiz: List[dict] = st.session_state.quiz
    total = len(quiz)
    idx = st.session_state.q_index

    # Completed
    if idx >= total:
        st.success(f"🎉 Completed — Score: {st.session_state.score}/{total}")
        if st.button("Restart (generate new quiz)", key="restart"):
            st.session_state.quiz = []
            st.session_state.q_index = 0
            st.session_state.score = 0
            for k in list(st.session_state.keys()):
                if isinstance(k, str) and (k.startswith("answered_") or k.startswith("selected_") or k.startswith("wrongs_") or k.startswith("scored_")):
                    del st.session_state[k]
        st.stop()

    qobj = quiz[idx]
    st.markdown(f"**Q{idx+1}. {qobj['question']}**")

    # per-question keys
    answered_key = f"answered_{idx}"
    selected_key = f"selected_{idx}"
    wrongs_key = f"wrongs_{idx}"
    scored_key = f"scored_{idx}"

    if wrongs_key not in st.session_state:
        st.session_state[wrongs_key] = set()

    answered = st.session_state.get(answered_key, False)
    selected = st.session_state.get(selected_key, None)
    wrongs = st.session_state.get(wrongs_key, set())

    # We will render one visible card per option. To make them clickable we put a tiny
    # invisible st.button next to each card and give it a unique key. When the button is clicked
    # we update session_state and the cards re-render with new color classes.
    for i, opt in enumerate(qobj["options"]):
        letter = chr(65 + i)
        btn_key = f"optbtn_{idx}_{i}"  # unique key per question-option

        # When the button is clicked, update state
        pressed = st.button("", key=btn_key, help="Click option", args=None)
        if pressed:
            # mark answered and selected
            st.session_state[answered_key] = True
            st.session_state[selected_key] = letter
            # record wrong clicks (so multiple wrong picks show red)
            if letter != qobj["answer"]:
                s = st.session_state.get(wrongs_key, set())
                s.add(letter)
                st.session_state[wrongs_key] = s
            # scoring: increment once if correct and not already scored
            if letter == qobj["answer"] and not st.session_state.get(scored_key, False):
                st.session_state.score = st.session_state.get("score", 0) + 1
                st.session_state[scored_key] = True
            # Streamlit will rerun after this click; next render will show card colors
            # No explicit rerun call needed.

        # Now render the visible card (the card is always shown; click is handled by the invisible button)
        # Card class depends on state (correct/wrong/neutral)
        card_class = "opt-card"
        prefix = ""
        if st.session_state.get(answered_key, False):
            if letter == qobj["answer"]:
                card_class += " correct"
                prefix = "✅"
            elif letter in st.session_state.get(wrongs_key, set()):
                card_class += " wrong"
                prefix = "❌"
            elif st.session_state.get(selected_key) == letter and letter != qobj["answer"]:
                card_class += " wrong"
                prefix = "❌"
            else:
                card_class += ""
        # card markup (keeps same card in place and recolors on rerun)
        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="opt-prefix"><strong>{prefix} {letter}</strong></div>
                <div class="opt-text">{opt}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # explanation if answered
    if st.session_state.get(answered_key, False):
        st.info(f"Explanation: {qobj.get('explanation', 'No explanation provided.')}")
    else:
        st.caption("Hover and click any option to answer. Or click Next to skip this question.")

    # Navigation (unique Next key ensures single click works)
    if idx < total - 1:
        if st.button("➡️ Next", key=f"next_{idx}"):
            st.session_state.q_index = idx + 1
            safe_rerun()
    else:
        if st.button("Finish Quiz", key=f"finish_{idx}"):
            st.session_state.q_index = total
            safe_rerun()

st.write("---")
st.caption("Dark UI with hover effects; click option to mark (red/green) and Next advances in one click.")
