---
name: paper_generator
description: Interactive academic draft builder that composes manuscripts section-by-section (accept/edit/redo), injects verified citations from novelty_search, and exports LaTeX-ready .tex and Markdown files.
---

# Paper Generator Skill

## Purpose
Builds high-impact, journal-ready academic drafts interactively from idea notes, peer-review critiques, and verified citations.

## Workflow
1. Walks through canonical sections: Abstract, Introduction, Related Work, Methodology, Results, Discussion, Conclusion.
2. For each section, proposes a draft and prompts the author to `accept`, `edit`, or `redo`.
3. Injects citations retrieved from `novelty_search` and exports both `draft.md` and `draft.tex`.

## Quick Usage
```bash
python -m research.skills.paper_generator.generator --title "Token-Minimalist Peer Review Swarms" --out research/ideas/demo
```
