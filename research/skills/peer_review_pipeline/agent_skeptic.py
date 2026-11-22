"""Agent 1: Domain Skeptic (Novelty & Logic Auditor).

Input: Abstract + Introduction + Top-3 retrieved VectorDB heuristics ([VERIFIED_MEMORY]).
Task: Identify conceptual leaps, incrementalism, hidden assumptions, and unverified novelty claims.
"""

from __future__ import annotations

import re
from typing import Any

TEMPERATURE = 0.1
MAX_WORDS = 290
NOVELTY_HYPE_THRESHOLD = 2

GLOBAL_OUTPUT_CONSTRAINT = (
    "Zero greetings, zero paper summaries, zero praise. "
    "Telegraphic bullet points only. "
    "Prefix every critique with [FATAL], [MAJOR], or [MINOR] and cite the exact section/equation. "
    "Hard word cap: < 300 words."
)

HYPE_PATTERNS = (
    r"\bfirst\b",
    r"\bnovel\b",
    r"\bgroundbreaking\b",
    r"\bstate[- ]of[- ]the[- ]art\b",
    r"\bsota\b",
    r"\bunprecedented\b",
    r"\bup to \d+%",
)


def build_prompt(abstract: str, intro: str, verified_memory: list[dict[str, Any]]) -> str:
    """Build a token-minimalist prompt with [VERIFIED_MEMORY] injection."""
    mem_lines = [
        f"- ({m.get('category', 'heuristic')}, w={m.get('weight', 1.0)}) {m.get('content', '')}"
        for m in verified_memory[:3]
    ]
    mem_block = "\n".join(mem_lines) if mem_lines else "- None"
    return (
        f"ROLE: Domain Skeptic (Novelty & Logic Auditor). Temp={TEMPERATURE}.\n"
        f"RULES: {GLOBAL_OUTPUT_CONSTRAINT}\n"
        f"SEARCH_RULE: Do NOT call web/academic search if [VERIFIED_MEMORY] answers the claim.\n"
        f"[VERIFIED_MEMORY]\n{mem_block}\n"
        f"[ABSTRACT]\n{abstract.strip()}\n"
        f"[INTRODUCTION]\n{intro.strip()}\n"
    )


def _cap_words(text: str, max_words: int = MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def run_skeptic(
    abstract: str,
    intro: str,
    verified_memory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run deterministic offline Domain Skeptic audit with telegraphic output."""
    memories = verified_memory or []
    bullets: list[str] = []
    needs_search_queries: list[str] = []

    abs_low = abstract.lower()
    intro_low = intro.lower()
    combined = f"{abs_low}\n{intro_low}"

    # 1. Unverified novelty / hype claims
    hype_hits = [pat for pat in HYPE_PATTERNS if re.search(pat, combined)]
    if len(hype_hits) >= NOVELTY_HYPE_THRESHOLD and not memories:
        bullets.append(
            "[MAJOR] Abstract/Introduction: Unverified novelty/compression claim "
            f"({len(hype_hits)} superlative markers) lacks [VERIFIED_MEMORY] or SOTA citation."
        )
        # Extract concise search phrase for targeted fallback
        first_sentence = abstract.strip().split(".")[0][:120]
        if first_sentence:
            needs_search_queries.append(first_sentence)

    # 2. Conceptual leap: hypothesis without falsification / failure modes
    if "hypothesize" in intro_low or "claim" in combined:
        if not any(k in combined for k in ("limitation", "threat", "failure", "bound", "trade-off")):
            bullets.append(
                "[MAJOR] Introduction: Core hypothesis stated without explicit falsification "
                "criteria or theoretical failure bounds."
            )

    # 3. Incrementalism check: baseline contrast
    if not any(k in intro_low for k in ("prior", "existing", "baseline", "previous", "compared")):
        bullets.append(
            "[FATAL] Introduction: No concrete contrast against prior SOTA approaches; "
            "high risk of incrementalism."
        )

    # 4. Hidden assumption check: zero-cost / offline generality
    if "zero-cost" in combined or "offline" in combined:
        if "hardware" not in combined and "latency" not in combined and "memory" not in combined:
            bullets.append(
                "[MINOR] Abstract: 'Zero-cost/offline' claim omits local compute, RAM, and "
                "energy overhead assumptions."
            )

    # 5. Memory-grounded critique
    for mem in memories[:3]:
        content = mem.get("content", "").strip()
        if content:
            bullets.append(
                f"[MINOR] Abstract/Introduction: Cross-check against [VERIFIED_MEMORY]: {content}"
            )

    if not bullets:
        bullets.append(
            "[MINOR] Introduction: Claims appear internally consistent; verify empirical novelty "
            "against latest arXiv benchmarks."
        )

    critique_text = _cap_words("\n".join(f"- {b}" for b in bullets), MAX_WORDS)
    return {
        "agent": "Domain Skeptic",
        "temperature": TEMPERATURE,
        "critique": critique_text,
        "word_count": len(critique_text.split()),
        "needs_search": bool(needs_search_queries) and not bool(memories),
        "search_queries": needs_search_queries[:1],
        "prompt_preview": build_prompt(abstract, intro, memories)[:240],
    }
