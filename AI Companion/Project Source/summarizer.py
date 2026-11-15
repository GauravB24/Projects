# summarizer.py
import os
import re
from typing import Callable

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

# small environment hints
os.environ.setdefault("PYTORCH_JIT", "0")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

SUMMARY_MODEL_NAME = "sshleifer/distilbart-cnn-6-6"
_SUMMARIZER_PIPELINE = None

def load_summarizer(model_name: str = SUMMARY_MODEL_NAME, force_cpu: bool = True):
    global _SUMMARIZER_PIPELINE
    if _SUMMARIZER_PIPELINE is not None:
        return _SUMMARIZER_PIPELINE

    if not TRANSFORMERS_AVAILABLE:
        def fallback_summarizer(text: str, **kwargs):
            return [{"summary_text": (text[:200] + ("..." if len(text) > 200 else ""))}]
        _SUMMARIZER_PIPELINE = fallback_summarizer
        return _SUMMARIZER_PIPELINE

    try:
        device = -1 if force_cpu else 0
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        _SUMMARIZER_PIPELINE = pipeline("summarization", model=model, tokenizer=tokenizer, device=device)
        return _SUMMARIZER_PIPELINE
    except Exception:
        def fallback_summarizer(text: str, **kwargs):
            return [{"summary_text": (text[:200] + ("..." if len(text) > 200 else ""))}]
        _SUMMARIZER_PIPELINE = fallback_summarizer
        return _SUMMARIZER_PIPELINE

def safe_summarize(text: str, max_length: int = 180, min_length: int = 40, summarizer=None) -> str:
    if not text or not text.strip():
        return ""
    if summarizer is None:
        summarizer = load_summarizer()
    try:
        out = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        if isinstance(out, list) and len(out) > 0:
            first = out[0]
            if isinstance(first, dict):
                return first.get("summary_text") or first.get("generated_text") or ""
            if isinstance(first, str):
                return first
        if isinstance(out, dict):
            return out.get("summary_text") or out.get("generated_text") or ""
        if isinstance(out, str):
            return out
    except Exception:
        snippet = text.strip()
        if len(snippet) > max_length:
            return snippet[:max_length].rsplit(" ", 1)[0] + "..."
        return snippet
    return ""
