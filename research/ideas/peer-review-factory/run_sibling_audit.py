"""Sibling-scanning Peer-Review Factory runner.

Lives inside ``research/ideas/peer-review-factory/`` and audits every sibling
idea folder under ``research/ideas/`` (skipping itself). Outputs are dropped
into shared common folders:
  - ``research/reviews/`` : encrypted per-idea review logs + encrypted ledger
  - ``research/drafts/``  : intermediate working drafts
  - ``research/papers/``  : academic papers (.md + .tex) for high-scoring ideas
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.skills.paper_generator.generator import (
    CANONICAL_SECTIONS,
    propose_section,
    render_latex,
    render_markdown,
)
from research.skills.peer_review_pipeline.encrypt_util import (
    compress_encrypt,
    generate_key,
    load_dotenv_if_present,
)
from research.skills.peer_review_pipeline.manager import process_paper
from research.skills.peer_review_pipeline.vector_store import DEFAULT_DB_PATH

FACTORY_DIR_NAME = "peer-review-factory"
CANDIDATE_FILENAMES = ("manuscript.md", "notes.md", "convo.md")
DEFAULT_PAPER_RISK_THRESHOLD = 35


def discover_sibling_ideas(ideas_root: Path) -> list[Path]:
    """Return sorted sibling idea directories under ``ideas_root`` (excluding this factory)."""
    if not ideas_root.is_dir():
        return []
    siblings: list[Path] = []
    for child in sorted(ideas_root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if child.name == FACTORY_DIR_NAME or child.name.startswith(".") or child.name == "__pycache__":
            continue
        siblings.append(child)
    return siblings


def _collect_idea_document(idea_dir: Path) -> tuple[str, list[Path]]:
    """Combine manuscript and/or conversation note markdown files inside ``idea_dir``."""
    found: list[Path] = []
    for name in CANDIDATE_FILENAMES:
        p = idea_dir / name
        if p.is_file():
            found.append(p)
    if not found:
        # Fall back to any markdown files directly inside the idea folder
        found = sorted(p for p in idea_dir.glob("*.md") if p.is_file())

    parts: list[str] = []
    for p in found:
        parts.append(f"<!-- source: {p.name} -->\n{p.read_text(encoding='utf-8').strip()}")
    return "\n\n".join(parts).strip(), found


def _build_sections_from_notes(idea_name: str, combined_text: str, verdict: str) -> dict[str, str]:
    title = idea_name.replace("-", " ").replace("_", " ").title()
    snippet = " ".join(combined_text.split()[:60])
    sections = {sec: propose_section(sec, title, context=snippet) for sec in CANONICAL_SECTIONS}
    sections["Discussion"] = (
        f"{sections['Discussion']}\n\nPeer-Review Swarm Audit Snapshot:\n{verdict.strip()}"
    )
    return sections


def audit_sibling_ideas(
    ideas_root: Path | None = None,
    reviews_dir: Path | None = None,
    drafts_dir: Path | None = None,
    papers_dir: Path | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    enc_key: bytes | str | None = None,
    allow_search: bool = False,
    apply_evolution: bool = False,
    paper_risk_threshold: int = DEFAULT_PAPER_RISK_THRESHOLD,
    force_paper: bool = False,
) -> dict[str, Any]:
    """Audit all sibling idea folders and write results into common output folders."""
    research_root = REPO_ROOT / "research"
    ideas_root = Path(ideas_root) if ideas_root is not None else research_root / "ideas"
    reviews_dir = Path(reviews_dir) if reviews_dir is not None else research_root / "reviews"
    drafts_dir = Path(drafts_dir) if drafts_dir is not None else research_root / "drafts"
    papers_dir = Path(papers_dir) if papers_dir is not None else research_root / "papers"

    reviews_dir.mkdir(parents=True, exist_ok=True)
    drafts_dir.mkdir(parents=True, exist_ok=True)
    papers_dir.mkdir(parents=True, exist_ok=True)

    siblings = discover_sibling_ideas(ideas_root)
    results: list[dict[str, Any]] = []

    for idea_dir in siblings:
        idea_name = idea_dir.name
        combined_text, source_files = _collect_idea_document(idea_dir)
        if not combined_text:
            results.append({"idea": idea_name, "status": "skipped_empty"})
            continue

        # Feed a single combined document if multiple note/manuscript files exist
        if len(source_files) == 1:
            target_path = source_files[0]
            tmp_file = None
        else:
            tmp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", encoding="utf-8", delete=False
            )
            tmp_file.write(combined_text)
            tmp_file.close()
            target_path = Path(tmp_file.name)

        try:
            review_log_path = reviews_dir / f"{idea_name}.review_log.enc.json"
            review_out = process_paper(
                paper_path=target_path,
                db_path=db_path,
                enc_key=enc_key,
                allow_search=allow_search,
                run_evolution=True,
                apply_evolution=apply_evolution,
                output_log_path=review_log_path,
            )
        finally:
            if tmp_file is not None:
                Path(tmp_file.name).unlink(missing_ok=True)

        editor = review_out["editor"]
        risk_pct = int(editor.get("rejection_risk_pct", 100))
        decision = editor.get("decision", "Reject")
        title = idea_name.replace("-", " ").replace("_", " ").title()
        sections = _build_sections_from_notes(idea_name, combined_text, editor.get("verdict", ""))
        citations = review_out.get("search_hits", [])

        # Always write an intermediate working draft to common research/drafts/
        draft_path = drafts_dir / f"{idea_name}_draft.md"
        draft_path.write_text(render_markdown(title, sections, citations), encoding="utf-8")

        paper_paths: dict[str, str] = {}
        if force_paper or risk_pct <= paper_risk_threshold:
            md_path = papers_dir / f"{idea_name}_paper.md"
            tex_path = papers_dir / f"{idea_name}_paper.tex"
            md_path.write_text(render_markdown(title, sections, citations), encoding="utf-8")
            tex_path.write_text(render_latex(title, sections, citations), encoding="utf-8")
            paper_paths = {"markdown": str(md_path), "latex": str(tex_path)}

        results.append(
            {
                "idea": idea_name,
                "status": "audited",
                "sources": [p.name for p in source_files],
                "decision": decision,
                "rejection_risk_pct": risk_pct,
                "novelty_score": editor.get("novelty_score"),
                "rigor_score": editor.get("rigor_score"),
                "review_log_path": str(review_log_path),
                "draft_path": str(draft_path),
                "paper_paths": paper_paths,
            }
        )

    ledger = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ideas_audited": len([r for r in results if r.get("status") == "audited"]),
        "results": results,
    }
    ledger_path = reviews_dir / "grades_ledger.enc.json"
    ledger_path.write_bytes(compress_encrypt(ledger, key=enc_key))
    ledger["ledger_path"] = str(ledger_path)
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit all sibling idea folders under research/ideas/")
    parser.add_argument("--allow-search", action="store_true", help="Enable free Semantic Scholar/arXiv fallback (max 2 queries)")
    parser.add_argument("--apply-evolution", action="store_true", help="Apply winning <=1% genetic mutation if fitness > 0")
    parser.add_argument("--force-paper", action="store_true", help="Generate .md + .tex into research/papers/ regardless of risk threshold")
    parser.add_argument("--risk-threshold", type=int, default=DEFAULT_PAPER_RISK_THRESHOLD, help="Max rejection risk %% to auto-generate a paper")
    parser.add_argument("--ephemeral-key", action="store_true", help="Use an ephemeral key if IDEA_ENC_KEY is unset")
    args = parser.parse_args()

    load_dotenv_if_present()
    enc_key = os.getenv("IDEA_ENC_KEY")
    if not enc_key:
        if args.ephemeral_key:
            enc_key = generate_key()
            print("[WARN] IDEA_ENC_KEY not set in env/.env; using ephemeral key for this dry run.")
        else:
            print(
                "[ERROR] IDEA_ENC_KEY not set. Add IDEA_ENC_KEY=... to .env or pass --ephemeral-key.",
                file=sys.stderr,
            )
            return 1

    ledger = audit_sibling_ideas(
        enc_key=enc_key,
        allow_search=args.allow_search,
        apply_evolution=args.apply_evolution,
        paper_risk_threshold=args.risk_threshold,
        force_paper=args.force_paper,
    )

    print(f"=== SIBLING AUDIT COMPLETE ({ledger['ideas_audited']} ideas) ===")
    for item in ledger["results"]:
        if item["status"] != "audited":
            print(f"- {item['idea']}: {item['status']}")
            continue
        paper_flag = "PAPER GENERATED" if item["paper_paths"] else "draft only"
        print(
            f"- {item['idea']}: {item['decision']} | Risk={item['rejection_risk_pct']}% "
            f"| Novelty={item['novelty_score']}/10 Rigor={item['rigor_score']}/10 | {paper_flag}"
        )
    print(f"[LEDGER] {ledger['ledger_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
