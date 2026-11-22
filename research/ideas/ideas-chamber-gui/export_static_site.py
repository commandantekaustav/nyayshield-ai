"""Export a privacy-safe static GitHub Pages bundle for HisMastersChamber GUI.

Writes to ``docs/chamber/`` (index.html + data.json) and ``docs/.nojekyll``.
NEVER exports ``.env``, ``IDEA_ENC_KEY``, or private encrypted blobs.
Cognitive check-ins on GitHub Pages run interactively in browser ``localStorage``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
GUI_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))

from server import build_workspace_snapshot, safe_read_scoped_file  # noqa: E402


def export_static(
    out_dir: Path | None = None,
    include_cognitive: bool = False,
) -> dict[str, Path]:
    research_root = REPO_ROOT / "research"
    target_dir = Path(out_dir) if out_dir is not None else (REPO_ROOT / "docs" / "chamber")
    target_dir.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "docs" / ".nojekyll").write_text("", encoding="utf-8")

    # Never decrypt private encrypted logs into public GitHub Pages by default
    snap: dict[str, Any] = build_workspace_snapshot(
        research_root=research_root,
        enc_key="",
    )
    if not include_cognitive:
        snap["cognitive"]["recent_entries"] = []

    # Bundle non-sensitive markdown/tex files so viewers can browse ideas, drafts & papers
    static_files: dict[str, str] = {}
    for idea in snap["ideas"]:
        for f in idea["files"]:
            if f["name"].endswith((".md", ".tex")):
                rel = f"{idea['name']}/{f['relpath']}"
                ok, content = safe_read_scoped_file(research_root, "ideas", rel)
                if ok:
                    static_files[f"ideas/{rel}"] = content
    for scope in ("drafts", "papers"):
        for f in snap[scope]:
            if f["name"].endswith((".md", ".tex")):
                ok, content = safe_read_scoped_file(research_root, scope, f["relpath"])
                if ok:
                    static_files[f"{scope}/{f['relpath']}"] = content

    snap["static_files"] = static_files
    snap["hosted_mode"] = "github_pages_static"

    html_out = target_dir / "index.html"
    data_out = target_dir / "data.json"
    shutil.copyfile(GUI_DIR / "index.html", html_out)
    data_out.write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"html": html_out, "data": data_out}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export static GitHub Pages bundle for Ideas Chamber GUI")
    parser.add_argument("--include-cognitive", action="store_true", help="Include recent cognitive_log.jsonl entries")
    args = parser.parse_args()
    paths = export_static(include_cognitive=args.include_cognitive)
    print(f"Exported static GUI: {paths['html']}")
    print(f"Exported snapshot:   {paths['data']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
