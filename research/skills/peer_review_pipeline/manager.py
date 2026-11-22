"""Peer-Review Pipeline Manager.

Orchestrates preprocessing, [VERIFIED_MEMORY] vector gate, targeted search
fallback, three-agent review, post-review distillation, ZSTD+ChaCha20-Poly1305
encryption, and bounded <= 1% genetic evolution.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research.skills.novelty_search.semantic_scholar import targeted_search
from research.skills.peer_review_pipeline.agent_editor import run_editor
from research.skills.peer_review_pipeline.agent_methodologist import run_methodologist
from research.skills.peer_review_pipeline.agent_skeptic import run_skeptic
from research.skills.peer_review_pipeline.encrypt_util import compress_encrypt
from research.skills.peer_review_pipeline.mutator import evolve_scripts
from research.skills.peer_review_pipeline.vector_store import DEFAULT_DB_PATH, WisdomVectorStore

STRIP_HEADINGS = (
    "references",
    "bibliography",
    "acknowledgments",
    "acknowledgements",
    "author metadata",
    "authors",
    "affiliations",
    "funding",
)


def estimate_tokens(text: str) -> int:
    """Fast local token approximation (~1.33 tokens per whitespace-delimited word)."""
    words = len(text.split())
    return max(1, int(round(words * 1.33))) if words else 0


def load_and_strip(paper_path: str | Path) -> tuple[str, dict[str, int | float]]:
    """Read a markdown manuscript and strip non-substantive sections for token reduction."""
    raw = Path(paper_path).read_text(encoding="utf-8")
    tokens_before = estimate_tokens(raw)

    kept_lines: list[str] = []
    skipping = False
    for line in raw.splitlines():
        heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if heading_match:
            title = heading_match.group(1).strip().lower()
            if any(title == h or title.startswith(h + " ") for h in STRIP_HEADINGS):
                skipping = True
                continue
            skipping = False
        if not skipping:
            kept_lines.append(line)

    stripped = "\n".join(kept_lines).strip()
    tokens_after = estimate_tokens(stripped)
    stats: dict[str, int | float] = {
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "tokens_saved": max(0, tokens_before - tokens_after),
        "reduction_pct": round(
            ((tokens_before - tokens_after) / max(1, tokens_before)) * 100.0, 2
        ),
    }
    return stripped, stats


def split_sections(text: str) -> dict[str, str]:
    """Split markdown manuscript into canonical section buckets."""
    buckets: dict[str, list[str]] = {
        "abstract": [],
        "intro": [],
        "methods": [],
        "results": [],
        "discussion": [],
    }
    current = "abstract"
    for line in text.splitlines():
        m = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if m:
            h = m.group(1).strip().lower()
            if "abstract" in h:
                current = "abstract"
            elif "intro" in h or "background" in h or "related" in h:
                current = "intro"
            elif "method" in h or "approach" in h or "architecture" in h or "design" in h:
                current = "methods"
            elif "result" in h or "experiment" in h or "evaluation" in h:
                current = "results"
            elif "discuss" in h or "conclusion" in h or "limitation" in h:
                current = "discussion"
            continue
        buckets[current].append(line)

    return {k: "\n".join(v).strip() for k, v in buckets.items()}


def distill_and_store(
    store: WisdomVectorStore,
    editor_out: dict[str, Any],
    search_hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract <= 2 heuristics, verified benchmarks, and a 1-line score_log into LanceDB."""
    actions: list[dict[str, Any]] = []

    for db in editor_out.get("dealbreakers", [])[:2]:
        sev = db.get("severity", "MAJOR")
        fix = db.get("fix", "").strip()
        if fix:
            weight = 4.5 if sev == "FATAL" else 3.0 if sev == "MAJOR" else 1.5
            actions.append(store.add_wisdom("heuristic", fix, weight=weight))

    for hit in search_hits[:2]:
        title = hit.get("title", "").strip()
        year = hit.get("year", "")
        cites = hit.get("citationCount", 0)
        if title:
            summary = f"Benchmark ({year}, cites={cites}): {title}"
            actions.append(store.add_wisdom("benchmark", summary, weight=2.5))

    score_line = editor_out.get("score_summary", "")
    if score_line:
        actions.append(store.add_wisdom("score_log", score_line, weight=3.0))

    return actions


def process_paper(
    paper_path: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
    enc_key: bytes | str | None = None,
    allow_search: bool = False,
    run_evolution: bool = True,
    apply_evolution: bool = False,
) -> dict[str, Any]:
    """Execute the full peer-review pipeline on ``paper_path``."""
    t0 = time.perf_counter()
    paper = Path(paper_path)
    stripped_text, token_stats = load_and_strip(paper)
    sections = split_sections(stripped_text)

    store = WisdomVectorStore(db_path=db_path)

    skeptic_mem = store.query_wisdom(
        f"{sections['abstract']} {sections['intro']}", limit=3, category="heuristic"
    )
    method_mem = store.query_wisdom(
        f"{sections['methods']} {sections['results']}", limit=3, category="benchmark"
    )
    score_history = store.get_score_log(limit=5)

    skeptic_out = run_skeptic(sections["abstract"], sections["intro"], skeptic_mem)
    method_out = run_methodologist(sections["methods"], sections["results"], method_mem)

    search_hits: list[dict[str, Any]] = []
    if allow_search:
        pending_queries: list[str] = []
        if skeptic_out.get("needs_search"):
            pending_queries.extend(skeptic_out.get("search_queries", []))
        if method_out.get("needs_search"):
            pending_queries.extend(method_out.get("search_queries", []))
        for q in pending_queries[:2]:
            search_hits.extend(targeted_search(q, limit=2))

    editor_out = run_editor(skeptic_out, method_out, score_history)
    distill_actions = distill_and_store(store, editor_out, search_hits)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    evolution_report: dict[str, Any] = {"status": "skipped", "applied": False}
    if run_evolution:
        pkg_dir = Path(__file__).resolve().parent
        agent_files = [
            pkg_dir / "agent_skeptic.py",
            pkg_dir / "agent_methodologist.py",
            pkg_dir / "agent_editor.py",
        ]
        evolution_report = evolve_scripts(agent_files, apply_best=apply_evolution)

    log_payload: dict[str, Any] = {
        "paper": paper.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": elapsed_ms,
        "token_stats": token_stats,
        "skeptic": skeptic_out,
        "methodologist": method_out,
        "editor": editor_out,
        "search_hits": search_hits,
        "distill_actions": distill_actions,
        "evolution": evolution_report,
    }

    enc_path = paper.parent / "review_log.enc.json"
    enc_blob = compress_encrypt(log_payload, key=enc_key)
    enc_path.write_bytes(enc_blob)
    log_payload["encrypted_log_path"] = str(enc_path)

    return log_payload
