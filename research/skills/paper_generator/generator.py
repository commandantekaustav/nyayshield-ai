"""Interactive academic paper generator with Markdown and LaTeX (.tex) export."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

CANONICAL_SECTIONS = (
    "Abstract",
    "Introduction",
    "Related Work",
    "Methodology",
    "Results",
    "Discussion",
    "Conclusion",
)


def propose_section(section: str, title: str, context: str = "") -> str:
    """Return a concise starter paragraph for ``section``."""
    ctx_note = f" Context: {context.strip()}." if context.strip() else ""
    templates = {
        "Abstract": (
            f"We investigate {title}, presenting a token-minimalist, locally executed "
            f"multi-agent architecture that preserves analytical rigor while cutting "
            f"context overhead.{ctx_note}"
        ),
        "Introduction": (
            f"Modern AI-assisted workflows face escalating token costs and reproducibility "
            f"gaps. In {title}, we formulate a deterministic-first swarm pipeline with "
            f"explicit failure bounds.{ctx_note}"
        ),
        "Related Work": (
            "Prior research explores standalone LLM reviewers and cloud RAG stores, but "
            "rarely integrates embedded vector gating with bounded self-evolution."
        ),
        "Methodology": (
            "Manuscripts undergo non-substantive section stripping, local 384-dim embedding, "
            "LanceDB [VERIFIED_MEMORY] gating, three-agent low-temperature auditing, and "
            "<=1% AST-validated genetic refinement."
        ),
        "Results": (
            "Empirical evaluation reports token reduction %, mean latency +/- SD, 95% CIs, "
            "and controlled ablations across n >= 30 benchmark documents."
        ),
        "Discussion": (
            "We analyze trade-offs between strict token ceilings, domain generalization, "
            "and cryptographic auditability (ZSTD + ChaCha20-Poly1305)."
        ),
        "Conclusion": (
            f"{title} demonstrates that offline-first, bounded self-evolving micro-agent "
            "swarms can deliver high-rigor peer review at near-zero marginal cost."
        ),
    }
    return templates.get(section, f"Draft content for {section}.{ctx_note}")


def format_citations_markdown(citations: list[dict[str, Any]]) -> str:
    if not citations:
        return ""
    lines = ["## References"]
    for idx, c in enumerate(citations, start=1):
        title = c.get("title", "Untitled")
        year = c.get("year") or "n.d."
        url = c.get("url", "")
        suffix = f" ({url})" if url else ""
        lines.append(f"[{idx}] {title} ({year}).{suffix}")
    return "\n".join(lines)


def render_markdown(title: str, sections: dict[str, str], citations: list[dict[str, Any]]) -> str:
    parts = [f"# {title}", ""]
    for sec in CANONICAL_SECTIONS:
        if sec in sections and sections[sec].strip():
            parts.append(f"## {sec}")
            parts.append(sections[sec].strip())
            parts.append("")
    ref_block = format_citations_markdown(citations)
    if ref_block:
        parts.append(ref_block)
        parts.append("")
    return "\n".join(parts)


def render_latex(title: str, sections: dict[str, str], citations: list[dict[str, Any]]) -> str:
    def _esc(s: str) -> str:
        return s.replace("\\", "\\textbackslash{}").replace("%", "\\%").replace("_", "\\_").replace("&", "\\&")

    lines = [
        "\\documentclass[11pt]{article}",
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage{hyperref}",
        f"\\title{{{_esc(title)}}}",
        "\\date{\\today}",
        "\\begin{document}",
        "\\maketitle",
    ]
    if "Abstract" in sections:
        lines.append("\\begin{abstract}")
        lines.append(_esc(sections["Abstract"].strip()))
        lines.append("\\end{abstract}")

    for sec in CANONICAL_SECTIONS:
        if sec == "Abstract":
            continue
        if sec in sections and sections[sec].strip():
            lines.append(f"\\section{{{_esc(sec)}}}")
            lines.append(_esc(sections[sec].strip()))

    if citations:
        lines.append("\\begin{thebibliography}{9}")
        for idx, c in enumerate(citations, start=1):
            c_title = _esc(c.get("title", "Untitled"))
            year = c.get("year") or "n.d."
            lines.append(f"\\bibitem{{ref{idx}}} {c_title} ({year}).")
        lines.append("\\end{thebibliography}")

    lines.append("\\end{document}")
    return "\n".join(lines) + "\n"


def interactive_generate(
    title: str,
    out_dir: str | Path,
    citations: list[dict[str, Any]] | None = None,
    context: str = "",
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
) -> dict[str, Path]:
    """Walk interactively through each section (accept / edit / redo) and write .md + .tex."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    accepted: dict[str, str] = {}

    for sec in CANONICAL_SECTIONS:
        draft = propose_section(sec, title, context=context)
        while True:
            print_fn(f"\n--- {sec} ---\n{draft}")
            choice = input_fn(f"[{sec}] (a)ccept / (e)dit / (r)edo: ").strip().lower()
            if choice in ("", "a", "accept"):
                accepted[sec] = draft
                break
            if choice in ("e", "edit"):
                edited = input_fn(f"Enter replacement text for {sec}: ").strip()
                if edited:
                    draft = edited
                accepted[sec] = draft
                break
            if choice in ("r", "redo"):
                extra = input_fn("Guidance for regeneration: ").strip()
                draft = propose_section(sec, title, context=f"{context} {extra}".strip())

    cite_list = citations or []
    md_path = out / "draft.md"
    tex_path = out / "draft.tex"
    md_path.write_text(render_markdown(title, accepted, cite_list), encoding="utf-8")
    tex_path.write_text(render_latex(title, accepted, cite_list), encoding="utf-8")
    return {"markdown": md_path, "latex": tex_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Academic Paper Generator")
    parser.add_argument("--title", required=True, help="Paper title")
    parser.add_argument("--out", required=True, help="Output directory for draft.md and draft.tex")
    parser.add_argument("--context", default="", help="Optional idea context notes")
    args = parser.parse_args()
    paths = interactive_generate(title=args.title, out_dir=args.out, context=args.context)
    print(f"Saved Markdown: {paths['markdown']}")
    print(f"Saved LaTeX:    {paths['latex']}")


if __name__ == "__main__":
    main()
