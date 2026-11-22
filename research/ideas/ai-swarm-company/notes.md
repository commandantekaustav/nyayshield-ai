# AI Swarm Software Company (Offline-First, Self-Evolving Micro-Agent Architecture)

## Abstract
We propose an offline-first, token-minimalist AI swarm software company architecture ("HisMastersChamber") that replaces expensive general-purpose cloud LLM loops with specialized deterministic-first micro-agents, embedded vector memory gating (LanceDB), cryptographic audit logs (Zstandard + ChaCha20-Poly1305), and bounded genetic script evolution capped strictly at <= 1.0% line mutations per evaluation cycle.

## Introduction
Conventional multi-agent software frameworks suffer from unbounded token expansion, redundant web searches, hallucinated baselines, and unverified self-modification. Our design minimizes marginal inference cost to near zero by combining local 384-dim embeddings, strict telegraphic output caps (< 300 words for reviewers, < 150 words for editors), and AST-validated bounded mutations.

## Methodology
1. **Sibling Idea Workspace**: All ideas live as sibling folders under `research/ideas/`, while `research/ideas/peer-review-factory/` acts as the central auditing sibling.
2. **Pre-Search Vector Gate**: Every section queries the local `wisdom` table (`limit=3`, cosine deduplication >= 0.92) before any external Semantic Scholar/arXiv lookup (hard cap: 2 queries/run).
3. **Bounded Genetic Evolution**: Candidate parameter mutations touch <= 1.0% of lines in any target script, pass `ast.parse()` verification, and are scored via `0.6 * risk_reduction + 0.3 * tokens_saved - 0.1 * runtime_increase`.
4. **Encrypted Persistence**: Review logs and grade ledgers are compressed with Zstandard (level 3) and encrypted with ChaCha20-Poly1305 using `IDEA_ENC_KEY` loaded from a git-ignored `.env`.

## Results
Preliminary dry runs on synthetic manuscripts demonstrate 12.6%–15.0% input token reduction from non-substantive section stripping, sub-second local execution latency, and strict <= 1.0% line-change compliance across 14 evaluated mutation candidates. Full benchmark evaluation across n >= 30 diverse manuscripts with 95% confidence intervals and baseline ablations is scheduled as the next milestone.

## Discussion
Key open questions include scaling the local embedding store beyond 10k heuristics, evaluating domain transfer across non-CS manuscripts, and integrating optional local small language models (Ollama/llama.cpp) behind the deterministic gate.
