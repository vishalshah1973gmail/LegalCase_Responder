"""Grounded answer generation with the Anthropic Claude API.

The model is instructed to answer ONLY from the retrieved chunks, to cite the
case name and section/paragraph number for every claim, and to say plainly when
the retrieved material does not answer the question.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ANTHROPIC_MAX_TOKENS, ANTHROPIC_MODEL  # noqa: E402
from retrieval.search import Hit  # noqa: E402

SYSTEM_PROMPT = """You are a legal research assistant working over a small corpus of \
property-law case documents. The corpus is partly or wholly SYNTHETIC (fictional cases \
generated for a demo).

Absolute rules:
1. Answer ONLY from the excerpts supplied in the user message. You have no other source. \
Do not use background legal knowledge to add, correct, extend, or "complete" an answer.
2. Cite the case name and the section identifier for EVERY substantive claim, inline, in \
the form (Case Name, Rider 2) or (Case Name, para. 7) or (Case Name, Clause 3). A sentence \
that states something about the corpus and carries no citation is an error.
3. If the excerpts do not answer the question, or the question is unrelated to this \
property-law corpus, say so plainly in one or two sentences and stop. Do not speculate, \
do not offer a general legal explanation, and do not answer from memory. Suggest a \
narrower or different query instead.
4. If the excerpts conflict, present the conflict and cite both sides rather than \
resolving it silently.
5. Do not state or imply what the law actually is in any real jurisdiction. Describe only \
what these documents say. Never give legal advice or a recommendation to act.
6. Be concise. Lead with the direct answer, then the supporting detail. Note when the \
cited excerpts are tagged synthetic.
"""

NO_CONTEXT_MSG = (
    "No excerpts in the corpus matched that question closely enough to answer it. "
    "Nothing was generated, because the assistant is restricted to the retrieved "
    "material. Try rephrasing, widening the filters, or lowering the similarity floor."
)


def format_context(hits: Sequence[Hit]) -> str:
    blocks: List[str] = []
    for i, h in enumerate(hits, start=1):
        m = h.meta
        blocks.append(
            f"<excerpt id=\"{i}\">\n"
            f"case_name: {h.case_name}\n"
            f"case_id: {m.get('case_id','')}\n"
            f"court: {m.get('court','')}\n"
            f"jurisdiction: {m.get('jurisdiction','')}\n"
            f"date: {m.get('date','')}\n"
            f"case_type: {m.get('case_type','')}\n"
            f"source: {h.source}\n"
            f"section: {h.section_type} {h.section_number}"
            f"{' — ' + m.get('heading','') if m.get('heading') else ''}\n"
            f"cite_as: {h.citation()}\n"
            f"similarity: {h.score:.3f}\n"
            f"---\n{h.text}\n</excerpt>"
        )
    return "\n\n".join(blocks)


def build_user_message(question: str, hits: Sequence[Hit]) -> str:
    return (
        f"Question: {question}\n\n"
        f"Retrieved excerpts ({len(hits)}). These are the ONLY materials you may use:\n\n"
        f"{format_context(hits)}\n\n"
        "Answer the question using only the excerpts above, citing case name and section "
        "for every claim. If they do not answer it, say so plainly."
    )


def generate_answer(question: str, hits: Sequence[Hit],
                    api_key: str | None = None,
                    model: str | None = None) -> Tuple[str, str | None]:
    """Return (answer_text, error_message). Never raises for API problems."""
    if not hits:
        return NO_CONTEXT_MSG, None

    import os
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return "", ("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add "
                    "your key, then restart the app. Retrieval below still works "
                    "without a key.")
    try:
        import anthropic
    except ImportError:
        return "", "The `anthropic` package is not installed. Run: pip install -r requirements.txt"

    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=model or ANTHROPIC_MODEL,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(question, hits)}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return text.strip(), None
    except Exception as exc:
        return "", f"Anthropic API error: {type(exc).__name__}: {exc}"
