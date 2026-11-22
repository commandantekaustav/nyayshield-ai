# Peer-Review Factory (`research/ideas/peer-review-factory/`)

This folder is a **sibling subfolder** inside `research/ideas/`. Its job is to scan all **sibling idea folders** (e.g., `ai-swarm-company/`, `demo/`, and any future ideas), analyze their conversation notes (`notes.md`, `convo.md`) and manuscripts (`manuscript.md`), grade them using the offline 3-agent peer-review swarm, and drop outputs into common shared directories:

- `research/reviews/` — encrypted per-idea review logs (`<idea>.review_log.enc.json`) and consolidated encrypted `grades_ledger.enc.json`
- `research/drafts/` — intermediate working drafts (`<idea>_draft.md`)
- `research/papers/` — formatted academic papers (`<idea>_paper.md` + `<idea>_paper.tex`) when an idea passes the quality threshold (Rejection Risk ≤ 35%) or `--force-paper` is set
- `research/reviewer_brain/` — shared local LanceDB vector store (`wisdom`, git-ignored)

## Usage

```powershell
# Load IDEA_ENC_KEY from .env automatically and audit all sibling ideas
python research/ideas/peer-review-factory/run_sibling_audit.py

# Dry run with an ephemeral key (no .env required)
python research/ideas/peer-review-factory/run_sibling_audit.py --ephemeral-key

# Force academic paper generation into research/papers/ regardless of risk threshold
python research/ideas/peer-review-factory/run_sibling_audit.py --ephemeral-key --force-paper
```
