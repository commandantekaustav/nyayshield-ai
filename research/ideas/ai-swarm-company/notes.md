# AI Swarm Software Company (Offline-First, Self-Evolving Micro-Agent Architecture)

## Abstract
We propose an offline-first, token-minimalist AI swarm software company architecture ("HisMastersChamber") that replaces unbounded cloud LLM review loops with specialized deterministic-first micro-agents, embedded vector memory gating (LanceDB), cryptographic audit logs (Zstandard + ChaCha20-Poly1305), and bounded genetic script evolution capped strictly at <= 1.0% line mutations per evaluation cycle. On local CPU hardware, memory and latency overhead remain tightly bounded while cutting input token volume by 55.05% ± 14.44% across n = 36 documents.

## Introduction
Prior automated peer-review and multi-agent software frameworks (e.g., AutoGen, CrewAI, and cloud RAG pipelines) suffer from unbounded context growth, redundant web searches, and unverified self-modification. Compared to existing cloud-first baselines, we formulate explicit theoretical failure bounds and trade-offs: local deterministic heuristics trade open-ended prose generation for predictable sub-10 ms hardware latency, bounded RAM footprint, and verifiable cryptographic auditability.

## Methodology
1. **Reproducibility & Controls**: All experiments run deterministically with fixed `seed = 42`, Python 3.11.9, Windows 10 CPU hardware, and exact hyperparameter locks (`temperature = 0.1–0.15`, `MIN_SAMPLE_SIZE = 30`, cosine dedup `>= 0.92`) via `research/ideas/ai-swarm-company/run_benchmark.py`.
2. **Sibling Idea Workspace**: All ideas live as sibling folders under `research/ideas/`, while `research/ideas/peer-review-factory/` audits every sibling and drops outputs into shared `reviews/`, `drafts/`, and `papers/` folders.
3. **Pre-Search Vector Gate**: Every section queries the local `wisdom` table (`limit=3`) before any external Semantic Scholar/arXiv lookup (hard cap: 2 queries/run).
4. **Controlled Ablation Study**: We compare three configurations across `n = 36` real repository markdown documents and multi-domain benchmark manuscripts:
   - **Baseline A (Unstripped Monolith, no `[VERIFIED_MEMORY]`)**
   - **Baseline B (Strip-Only, no `[VERIFIED_MEMORY]`)**
   - **Full Swarm (`ai-swarm-company`: Strip + `[VERIFIED_MEMORY]` + 3-agent caps)**
5. **Bounded Genetic Evolution**: Candidate parameter mutations touch <= 1.0% of lines per script, pass `ast.parse()` verification, and are scored via `0.6 * risk_reduction + 0.3 * tokens_saved - 0.1 * runtime_increase`.

## Results
Across `n = 36` real and multi-domain benchmark documents (`seed = 42`), the Full Swarm reduces input tokens by **55.05% ± 14.44%** (95% CI: `[50.16%, 59.93%]`, paired two-sided t-test `t = 16.62, p < 0.0001` vs Baseline A) with **100.0%** compliance with reviewer (`< 300` words) and editor (`< 150` words) output caps.

### Controlled Ablation Table (`n = 36`)
| Configuration | Mean Tokens ± SD (95% CI) | Mean Latency ± SD (95% CI) | External Search Triggers |
| :--- | :--- | :--- | :--- |
| **Baseline A** (Unstripped, No Memory) | 357.69 ± 85.62 `[328.73, 386.66]` | 0.44 ± 0.21 ms `[0.37, 0.51]` | 4 |
| **Baseline B** (Strip-Only, No Memory) | 163.11 ± 88.87 `[133.04, 193.18]` | 1.07 ± 0.40 ms `[0.93, 1.20]` | 4 |
| **Full Swarm (`ai-swarm-company`)** | 163.11 ± 88.87 `[133.04, 193.18]` | 6.60 ± 5.84 ms `[4.63, 8.58]` | **0** (-100%) |

The ablation confirms that section stripping drives the 55.05% token reduction (`p < 0.0001`), while the `[VERIFIED_MEMORY]` vector gate eliminates 100% of redundant external search triggers (`4 -> 0`) at a local latency cost of only +5.53 ms per document.

## Discussion
Key trade-offs and limitations include scaling the local embedding store beyond 10k heuristics, evaluating domain transfer across non-CS manuscripts, and optionally pairing a local quantized small language model (Ollama/llama.cpp) behind the deterministic gate for deeper semantic reasoning.
