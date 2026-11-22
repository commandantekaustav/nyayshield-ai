---
name: novelty_search
description: Token-minimalist targeted academic literature search using the free Semantic Scholar Graph API and arXiv API (abstracts and citation metrics only, max 2 queries per review run).
---

# Novelty Search Skill

## Purpose
Provides a strictly gated, zero-cost literature fallback for `peer_review_pipeline`. Only invoked when `[VERIFIED_MEMORY]` in LanceDB does not already cover an empirical baseline or novelty claim.

## Rules
- Never scrape full HTML pages.
- Fetch only `title`, `year`, `citationCount`, `abstract` (truncated to 300 chars), and `url`.
- Hard cap of **2 queries per review run**.
- Gracefully falls back to arXiv API if Semantic Scholar rate-limits (HTTP 429) or is unreachable.
