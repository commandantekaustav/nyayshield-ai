"""CLI entry point for the self-evolving peer-review pipeline.

Usage:
  python research/scripts/run_review.py --paper research/ideas/demo/manuscript.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure repo root is importable when executed as a standalone script
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.skills.peer_review_pipeline.encrypt_util import generate_key
from research.skills.peer_review_pipeline.manager import process_paper


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Peer-Review Swarm Pipeline")
    parser.add_argument("--paper", required=True, help="Path to manuscript markdown file")
    parser.add_argument(
        "--allow-search",
        action="store_true",
        help="Enable targeted Semantic Scholar / arXiv fallback (max 2 queries)",
    )
    parser.add_argument(
        "--apply-evolution",
        action="store_true",
        help="Apply winning <=1% genetic script mutation if fitness > 0",
    )
    parser.add_argument(
        "--ephemeral-key",
        action="store_true",
        help="Generate an ephemeral key if IDEA_ENC_KEY is unset (for local dry runs only)",
    )
    args = parser.parse_args()

    enc_key = os.getenv("IDEA_ENC_KEY")
    if not enc_key:
        if args.ephemeral_key:
            enc_key = generate_key()
            print("[WARN] IDEA_ENC_KEY not set; using ephemeral key for this dry run.")
        else:
            print(
                "[ERROR] IDEA_ENC_KEY environment variable is required. "
                "Generate one via encrypt_util.generate_key() or pass --ephemeral-key for a dry run.",
                file=sys.stderr,
            )
            return 1

    result = process_paper(
        paper_path=args.paper,
        enc_key=enc_key,
        allow_search=args.allow_search,
        run_evolution=True,
        apply_evolution=args.apply_evolution,
    )

    editor = result["editor"]
    tok = result["token_stats"]
    evo = result["evolution"]

    print("=== PEER-REVIEW SWARM VERDICT ===")
    print(editor["verdict"])
    print(
        f"\n[TOKENS] {tok['tokens_before']} -> {tok['tokens_after']} "
        f"(saved {tok['tokens_saved']}, -{tok['reduction_pct']}%)"
    )
    print(f"[ENCRYPTED LOG] {result['encrypted_log_path']}")
    print(
        f"[EVOLUTION] status={evo.get('status')} | candidates={evo.get('candidates_evaluated', 0)} "
        f"| best={evo.get('constant', 'n/a')} ({evo.get('change_pct', 0)}% lines) "
        f"| applied={evo.get('applied', False)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
