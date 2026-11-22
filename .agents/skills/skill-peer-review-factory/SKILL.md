---
name: skill-peer-review-factory
description: |
  Runs the offline-first, token-minimalist 3-agent academic peer-review swarm (Domain Skeptic, Forensic Methodologist, Gatekeeper Editor) from `research/ideas/peer-review-factory/` across sibling idea folders, gating web searches via embedded LanceDB `[VERIFIED_MEMORY]`, persisting ZSTD+ChaCha20-Poly1305 encrypted logs in `research/reviews/` using `.env` keys, and evaluating <=1.0% AST-validated genetic script mutations.
---

# Peer-Review Factory Skill

## When to Use
Activate this skill when auditing one or more research ideas under `research/ideas/`, grading manuscripts or conversation notes (`notes.md`, `convo.md`, `manuscript.md`), encrypting review logs, or running bounded genetic evolution on reviewer agents.

## Architecture & Invariants
1. **Sibling Topology**: `research/ideas/peer-review-factory/` is a single subfolder inside `research/ideas/` that scans all sibling idea directories (skipping itself).
2. **Three-Agent Pipeline (`temperature = 0.1–0.2`)**:
   - **Agent 1 — Domain Skeptic** (`agent_skeptic.py`): Audits Abstract + Introduction + top-3 `[VERIFIED_MEMORY]` heuristics for novelty gaps, incrementalism, and hidden assumptions (`< 300` words).
   - **Agent 2 — Forensic Methodologist** (`agent_methodologist.py`): Audits Methodology + Results + top-3 `[VERIFIED_MEMORY]` benchmarks for sample size (`n >= 30`), dispersion/CI, SOTA baselines, and reproducibility (`< 300` words).
   - **Agent 3 — Gatekeeper Editor** (`agent_editor.py`): Synthesizes both audits + historical `score_log` into an editorial decision (`Accept` / `Minor Revision` / `Major Revision` / `Reject`), Rejection Risk %, top 3 dealbreakers, and 1-sentence fixes (`< 150` words).
3. **Token & Search Discipline**:
   - Strip `References`, `Bibliography`, `Acknowledgments`, and `Author Metadata` before review.
   - Query local `research/reviewer_brain` (`wisdom` table, cosine dedup `>= 0.92`) first.
   - Free Semantic Scholar / arXiv fallback is strictly opt-in (`--allow-search`) and capped at **2 queries/run**.
4. **Encrypted Persistence**:
   - Compress with Zstandard (level 3) and encrypt with ChaCha20-Poly1305 using `IDEA_ENC_KEY` auto-loaded from git-ignored `.env`.
   - Drop per-idea logs (`<idea>.review_log.enc.json`) and consolidated `grades_ledger.enc.json` into `research/reviews/`.
5. **Bounded Genetic Evolution (`mutator.py`)**:
   - Strictly `<= 1.0%` of lines per script per evaluation cycle, AST-validated via `ast.parse()`, scored by `0.6*risk_reduction + 0.3*tokens_saved - 0.1*runtime_increase`.

## Commands
```powershell
# Audit all sibling ideas (reads IDEA_ENC_KEY from .env)
backend\.venv\Scripts\python.exe research/ideas/peer-review-factory/run_sibling_audit.py

# Dry run with ephemeral key
backend\.venv\Scripts\python.exe research/ideas/peer-review-factory/run_sibling_audit.py --ephemeral-key

# Single manuscript audit via unified CLI
backend\.venv\Scripts\python.exe research/scripts/run_review.py --paper research/ideas/<idea>/manuscript.md
```
