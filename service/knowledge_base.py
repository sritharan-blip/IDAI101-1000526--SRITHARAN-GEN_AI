from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import streamlit as st

KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
TOKEN_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)


@st.cache_data(ttl=3600, show_spinner=False)
def load_knowledge_chunks() -> tuple[tuple[str, str], ...]:
    """Load locally maintained, reviewable notes rather than inventing live references."""
    chunks: list[tuple[str, str]] = []
    if not KNOWLEDGE_DIR.exists():
        return ()
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for section in re.split(r"\n(?=##?\s)", text):
            excerpt = section.strip()
            if excerpt:
                chunks.append((path.name, excerpt[:1800]))
    return tuple(chunks)


def retrieve_context(query: str, limit: int = 3) -> str:
    """Retrieve the closest local notes with a small BM25-style lexical ranker."""
    chunks = load_knowledge_chunks()
    if not chunks:
        return "No vetted reference notes are available."
    terms = [term.lower() for term in TOKEN_RE.findall(query)]
    if not terms:
        return "No relevant local reference notes were found."
    tokenized = [Counter(token.lower() for token in TOKEN_RE.findall(text)) for _, text in chunks]
    doc_freq = Counter(term for term in set(terms) for doc in tokenized if doc[term])
    total = max(len(chunks), 1)

    def score(doc: Counter[str]) -> float:
        length_norm = 1 + 0.6 * sum(doc.values()) / max(
            sum(sum(item.values()) for item in tokenized) / total, 1
        )
        return sum(
            math.log(1 + (total - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            * (doc[term] * 2.2 / (doc[term] + 1.2 * length_norm))
            for term in set(terms)
        )

    ranked = sorted(
        ((score(doc), chunks[index]) for index, doc in enumerate(tokenized)),
        key=lambda item: item[0],
        reverse=True,
    )
    relevant = [(source, text) for value, (source, text) in ranked[:limit] if value > 0]
    if not relevant:
        return "No relevant local reference notes were found."
    return "\n\n".join(f"[Local reference: {source}]\n{text}" for source, text in relevant)
