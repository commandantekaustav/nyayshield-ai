---
name: skill-idea-paper-synthesizer
description: |
  Transforms sibling idea conversation notes and peer-review swarm verdicts into structured intermediate drafts (`research/drafts/`) and publication-ready Markdown + LaTeX (`.tex`) academic papers (`research/papers/`) when Rejection Risk <= 35% (or `--force-paper`), with optional free Semantic Scholar/arXiv citation grounding.
---

# Idea Paper Synthesizer Skill

## When to Use
Activate this skill when converting an evaluated sibling idea under `research/ideas/<idea>/` into a working draft (`research/drafts/<idea>_draft.md`) or a formatted academic manuscript (`research/papers/<idea>_paper.md` and `.tex`).

## Workflow
1. **Draft Promotion (Always)**: Every audited sibling idea produces an updated working draft in `research/drafts/<idea>_draft.md` combining canonical academic sections (`Abstract`, `Introduction`, `Related Work`, `Methodology`, `Results`, `Discussion`, `Conclusion`) with the latest Gatekeeper Editor audit snapshot.
2. **Paper Promotion (Quality-Gated)**:
   - Automatic trigger: `rejection_risk_pct <= 35` (configurable via `--risk-threshold`).
   - Manual override: pass `--force-paper` to `run_sibling_audit.py` or run interactive mode via `research/skills/paper_generator/generator.py` (`accept` / `edit` / `redo` per section).
   - Writes both Markdown (`research/papers/<idea>_paper.md`) and LaTeX (`research/papers/<idea>_paper.tex`) with escaped special characters and `thebibliography` entries.
3. **Citation Grounding**: Uses compact metadata from `research/skills/novelty_search/semantic_scholar.py` (max 2 free API queries/run, zero paid APIs).

## Commands
```powershell
# Auto-generate drafts & quality-gated papers for all sibling ideas
backend\.venv\Scripts\python.exe research/scripts/run_review.py --all-siblings

# Interactive section-by-section academic paper builder
backend\.venv\Scripts\python.exe -m research.skills.paper_generator.generator --title "<Title>" --out research/papers/<idea>
```
