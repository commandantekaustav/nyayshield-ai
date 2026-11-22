"""Agent 2: Forensic Methodologist (Data & Reproducibility Auditor).

Input: Methodology + Results + Top-3 retrieved VectorDB benchmarks ([VERIFIED_MEMORY]).
Task: Audit statistical significance, sample sizes, baselines, confounding variables, and reproducibility.
"""

from __future__ import annotations

import re
from typing import Any

TEMPERATURE = 0.15
MAX_WORDS = 290
MIN_SAMPLE_SIZE = 30

GLOBAL_OUTPUT_CONSTRAINT = (
    "Zero greetings, zero paper summaries, zero praise. "
    "Telegraphic bullet points only. "
    "Prefix every critique with [FATAL], [MAJOR], or [MINOR] and cite the exact section/equation. "
    "Hard word cap: < 300 words."
)


def build_prompt(methods: str, results: str, verified_memory: list[dict[str, Any]]) -> str:
    """Build a token-minimalist prompt with [VERIFIED_MEMORY] benchmark injection."""
    mem_lines = [
        f"- ({m.get('category', 'benchmark')}, w={m.get('weight', 1.0)}) {m.get('content', '')}"
        for m in verified_memory[:3]
    ]
    mem_block = "\n".join(mem_lines) if mem_lines else "- None"
    return (
        f"ROLE: Forensic Methodologist (Data & Reproducibility Auditor). Temp={TEMPERATURE}.\n"
        f"RULES: {GLOBAL_OUTPUT_CONSTRAINT}\n"
        f"SEARCH_RULE: Do NOT call web/academic search if [VERIFIED_MEMORY] answers the baseline.\n"
        f"[VERIFIED_MEMORY]\n{mem_block}\n"
        f"[METHODOLOGY]\n{methods.strip()}\n"
        f"[RESULTS]\n{results.strip()}\n"
    )


def _cap_words(text: str, max_words: int = MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def run_methodologist(
    methods: str,
    results: str,
    verified_memory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run deterministic offline Forensic Methodologist audit."""
    memories = verified_memory or []
    bullets: list[str] = []
    needs_search_queries: list[str] = []

    meth_low = methods.lower()
    res_low = results.lower()
    combined = f"{meth_low}\n{res_low}"

    # 1. Sample size audit (n=X)
    sample_matches = [int(m) for m in re.findall(r"\bn\s*=\s*(\d+)", combined)]
    if not sample_matches:
        bullets.append(
            "[MAJOR] Results: Sample size (n) not explicitly reported; statistical power cannot be verified."
        )
    elif min(sample_matches) < MIN_SAMPLE_SIZE:
        bullets.append(
            f"[FATAL] Results: Underpowered sample size (n={min(sample_matches)} < {MIN_SAMPLE_SIZE}); "
            "high variance invalidates generalization."
        )

    # 2. Statistical significance & effect size / CI
    has_p = bool(re.search(r"\bp\s*[<=>]\s*0?\.\d+", combined))
    has_ci = any(k in combined for k in ("confidence interval", "95% ci", "std", "±", "variance"))
    if not has_p:
        bullets.append(
            "[MAJOR] Results: No p-values or hypothesis test statistics reported for claimed gains."
        )
    if not has_ci:
        bullets.append(
            "[MAJOR] Results: Missing dispersion metrics (SD, 95% CI, or IQR) alongside point estimates."
        )

    # 3. Ablation & baseline comparison
    if "ablation" not in combined:
        bullets.append(
            "[MAJOR] Methodology/Results: No ablation study isolating each swarm component's contribution."
        )
    if "baseline" not in combined and not memories:
        bullets.append(
            "[MAJOR] Results: Missing external SOTA baseline comparison in Results and [VERIFIED_MEMORY]."
        )
        needs_search_queries.append("automated peer review LLM benchmark token compression")

    # 4. Reproducibility: random seed, hardware spec, code/data availability
    if not any(k in meth_low for k in ("seed", "deterministic", "reproduc", "hyperparameter")):
        bullets.append(
            "[MINOR] Methodology: Random seeds, exact model hashes, and hardware specs omitted; "
            "reproducibility impaired."
        )

    # 5. Confounding variables (e.g., synthetic data)
    if "synthetic" in res_low and "real" not in res_low:
        bullets.append(
            "[MAJOR] Results: Evaluation relies solely on synthetic data; real-world distribution shift unmeasured."
        )

    if not bullets:
        bullets.append(
            "[MINOR] Methodology/Results: Experimental controls present; verify external replication."
        )

    critique_text = _cap_words("\n".join(f"- {b}" for b in bullets), MAX_WORDS)
    return {
        "agent": "Forensic Methodologist",
        "temperature": TEMPERATURE,
        "critique": critique_text,
        "word_count": len(critique_text.split()),
        "needs_search": bool(needs_search_queries) and not bool(memories),
        "search_queries": needs_search_queries[:1],
        "prompt_preview": build_prompt(methods, results, memories)[:240],
    }
