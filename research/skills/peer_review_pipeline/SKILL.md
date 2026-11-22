---
name: peer_review_pipeline
description: Self-evolving, token-minimalist multi-agent academic peer-review pipeline with embedded LanceDB memory, ZSTD-ChaCha20-Poly1305 encrypted logs, and a <=1% bounded genetic script mutator.
---

# Peer-Review Pipeline Skill

## Purpose
Runs a three-agent academic peer-review pipeline modeled after top-tier journals (*Nature*, *Science*, *Springer*):
1. **Agent 1 — Domain Skeptic** (`agent_skeptic.py`): Novelty & logic auditor (Abstract + Introduction + Top-3 `[VERIFIED_MEMORY]`).
2. **Agent 2 — Forensic Methodologist** (`agent_methodologist.py`): Data, statistical significance, baselines, and reproducibility auditor (Methodology + Results + Top-3 `[VERIFIED_MEMORY]`).
3. **Agent 3 — Gatekeeper Editor** (`agent_editor.py`): Synthesizes compressed reviewer critiques + historical `score_log` into an editorial decision, Rejection Risk %, top 3 dealbreakers, and 1-sentence actionable fixes.

## Global Constraints
- Low temperature (`0.1`–`0.2`).
- Zero greetings, zero paper summaries, zero praise.
- Telegraphic bullet points prefixed with `[FATAL]`, `[MAJOR]`, or `[MINOR]` citing exact sections.
- Word caps: `< 300` words for reviewers, `< 150` words for Gatekeeper Editor.
- All persistent logs compressed with **Zstandard (level 3)** and encrypted with **ChaCha20-Poly1305** using `IDEA_ENC_KEY`.
- Bounded genetic evolution (`mutator.py`) modifies **at most 1% of lines** in any script per evaluation cycle and verifies via unit tests before committing.

## Quick Usage
```bash
# Generate a 32-byte base64 key once (store in your OS credential manager, never commit)
python -c "from research.skills.peer_review_pipeline.encrypt_util import generate_key; print(generate_key())"

# Run on a manuscript
python research/scripts/run_review.py --paper research/ideas/demo/manuscript.md
```
