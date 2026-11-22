"""Agent 3: Gatekeeper Editor (Synthesis & Scoring).

Input: Compressed outputs from Agent 1 & Agent 2 + Historical score_log from VectorDB.
Task: Output editorial decision (Reject / Major Revision / Minor Revision), Rejection Risk %,
top 3 dealbreakers, and a 1-sentence actionable fix per dealbreaker (< 150 words).
"""

from __future__ import annotations

import re
from typing import Any

TEMPERATURE = 0.2
MAX_WORDS = 145
FATAL_RISK_WEIGHT = 35
MAJOR_RISK_WEIGHT = 15
MINOR_RISK_WEIGHT = 5

GLOBAL_OUTPUT_CONSTRAINT = (
    "Zero greetings, zero paper summaries, zero praise. "
    "Telegraphic bullet points only. "
    "Hard word cap: < 150 words."
)


def _extract_bullets(critique: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for line in critique.splitlines():
        m = re.match(r"^\s*-\s*\[(FATAL|MAJOR|MINOR)\]\s*(.+)$", line.strip())
        if m:
            items.append((m.group(1), m.group(2).strip()))
    return items


def _propose_fix(issue: str) -> str:
    low = issue.lower()
    if "sample size" in low:
        return "Expand evaluation to >= 30 real manuscripts with power calculation."
    if "dispersion" in low or "ci" in low:
        return "Report mean +/- SD and 95% bootstrap CIs across >= 5 seeds."
    if "ablation" in low:
        return "Add a controlled ablation table isolating each micro-agent."
    if "synthetic" in low:
        return "Validate on an open peer-review corpus (e.g., OpenReview/ICLR)."
    if "novelty" in low or "baseline" in low or "sota" in low:
        return "Benchmark directly against >= 2 published SOTA baselines with citations."
    if "falsification" in low or "hypothesis" in low:
        return "Define quantitative failure thresholds and theoretical bounds in Introduction."
    if "p-value" in low:
        return "Run paired statistical significance tests with multiple-comparison correction."
    return "Add empirical evidence and explicit protocol details in the cited section."


def _cap_words(text: str, max_words: int = MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def run_editor(
    skeptic_out: dict[str, Any],
    methodologist_out: dict[str, Any],
    score_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Synthesize reviewer outputs into a strict <150-word editorial verdict."""
    history = score_log or []
    all_issues = _extract_bullets(skeptic_out.get("critique", "")) + _extract_bullets(
        methodologist_out.get("critique", "")
    )

    fatal_cnt = sum(1 for sev, _ in all_issues if sev == "FATAL")
    major_cnt = sum(1 for sev, _ in all_issues if sev == "MAJOR")
    minor_cnt = sum(1 for sev, _ in all_issues if sev == "MINOR")

    risk_pct = min(
        98,
        max(5, 10 + fatal_cnt * FATAL_RISK_WEIGHT + major_cnt * MAJOR_RISK_WEIGHT + minor_cnt * MINOR_RISK_WEIGHT),
    )

    if fatal_cnt > 0 or risk_pct >= 75:
        decision = "Reject"
    elif major_cnt >= 2 or risk_pct >= 40:
        decision = "Major Revision"
    else:
        decision = "Minor Revision"

    # Rank dealbreakers: FATAL > MAJOR > MINOR
    severity_rank = {"FATAL": 0, "MAJOR": 1, "MINOR": 2}
    ranked = sorted(all_issues, key=lambda x: severity_rank.get(x[0], 3))
    top_3 = ranked[:3]

    novelty_score = max(1, min(10, 8 - sum(1 for s, _ in _extract_bullets(skeptic_out.get("critique", "")) if s in ("FATAL", "MAJOR")) * 2))
    rigor_score = max(1, min(10, 9 - sum(1 for s, _ in _extract_bullets(methodologist_out.get("critique", "")) if s in ("FATAL", "MAJOR")) * 2))

    lines = [
        f"- Decision: {decision} | Rejection Risk: {risk_pct}% | Novelty: {novelty_score}/10 | Rigor: {rigor_score}/10",
    ]
    if history:
        lines.append(f"- Prior: {history[0].get('content', '')[:60]}")

    for idx, (sev, text) in enumerate(top_3, start=1):
        short_issue = " ".join(text.split()[:14])
        fix = _propose_fix(text)
        lines.append(f"- [{sev}] #{idx} {short_issue} -> Fix: {fix}")

    verdict_text = _cap_words("\n".join(lines), MAX_WORDS)
    top_fix = _propose_fix(top_3[0][1]) if top_3 else "Polish presentation."
    version = len(history) + 1
    score_summary = f"v{version} | Novelty:{novelty_score} Rigor:{rigor_score} Risk:{risk_pct}% | Fix: {' '.join(top_fix.split()[:6])}"

    return {
        "agent": "Gatekeeper Editor",
        "temperature": TEMPERATURE,
        "decision": decision,
        "rejection_risk_pct": risk_pct,
        "novelty_score": novelty_score,
        "rigor_score": rigor_score,
        "verdict": verdict_text,
        "word_count": len(verdict_text.split()),
        "score_summary": score_summary,
        "dealbreakers": [{"severity": s, "issue": t, "fix": _propose_fix(t)} for s, t in top_3],
    }
