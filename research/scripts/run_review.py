"""CLI entry point for the self-evolving peer-review pipeline.

Usage:
  python research/scripts/run_review.py --paper research/ideas/demo/manuscript.md
  python research/scripts/run_review.py --all-siblings
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

# Ensure repo root is importable when executed as a standalone script
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.skills.peer_review_pipeline.encrypt_util import (
    generate_key,
    load_dotenv_if_present,
)
from research.skills.peer_review_pipeline.manager import process_paper


def _load_sibling_auditor():
    script_path = REPO_ROOT / "research" / "ideas" / "peer-review-factory" / "run_sibling_audit.py"
    spec = importlib.util.spec_from_file_location("run_sibling_audit", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load sibling auditor from {script_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Peer-Review Swarm Pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--paper", help="Path to a single manuscript markdown file")
    group.add_argument(
        "--all-siblings",
        action="store_true",
        help="Audit all sibling idea folders under research/ideas/ and drop outputs in common folders",
    )
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
        "--force-paper",
        action="store_true",
        help="(With --all-siblings) Generate .md + .tex into research/papers/ regardless of risk threshold",
    )
    parser.add_argument(
        "--ephemeral-key",
        action="store_true",
        help="Generate an ephemeral key if IDEA_ENC_KEY is unset (for local dry runs only)",
    )
    args = parser.parse_args()

    load_dotenv_if_present()
    enc_key = os.getenv("IDEA_ENC_KEY")
    if not enc_key:
        if args.ephemeral_key:
            enc_key = generate_key()
            print("[WARN] IDEA_ENC_KEY not set in env/.env; using ephemeral key for this dry run.")
        else:
            print(
                "[ERROR] IDEA_ENC_KEY environment variable is required. "
                "Add IDEA_ENC_KEY=... to .env or pass --ephemeral-key for a dry run.",
                file=sys.stderr,
            )
            return 1

    if args.all_siblings:
        auditor = _load_sibling_auditor()
        ledger = auditor.audit_sibling_ideas(
            enc_key=enc_key,
            allow_search=args.allow_search,
            apply_evolution=args.apply_evolution,
            force_paper=args.force_paper,
        )
        print(f"=== SIBLING AUDIT COMPLETE ({ledger['ideas_audited']} ideas) ===")
        for item in ledger["results"]:
            if item["status"] != "audited":
                print(f"- {item['idea']}: {item['status']}")
                continue
            print(
                f"- {item['idea']}: {item['decision']} | Risk={item['rejection_risk_pct']}% "
                f"| Log={item['review_log_path']}"
            )
        print(f"[LEDGER] {ledger['ledger_path']}")
        return 0

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
