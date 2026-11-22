"""Offline-first local web GUI server for HisMastersChamber (Ideas & Cognitive Evolution).

Zero external web framework dependencies (uses Python stdlib ``http.server``).
Binds strictly to ``127.0.0.1`` for local privacy.

Usage:
  backend\\.venv\\Scripts\\python.exe research/ideas/ideas-chamber-gui/server.py --port 8765
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GUI_DIR = Path(__file__).resolve().parent
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))

from cognitive_tracker import (  # noqa: E402
    DEFAULT_LOG_PATH,
    append_cognitive_checkin,
    summarize_cognitive_evolution,
)
from research.skills.peer_review_pipeline.encrypt_util import (  # noqa: E402
    decrypt_decompress,
    load_dotenv_if_present,
)


def _load_sibling_auditor():
    script_path = REPO_ROOT / "research" / "ideas" / "peer-review-factory" / "run_sibling_audit.py"
    spec = importlib.util.spec_from_file_location("run_sibling_audit_gui", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load sibling auditor from {script_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _list_files(root: Path, max_depth: int = 2) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if len(rel.parts) > max_depth + 1:
            continue
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        out.append(
            {
                "name": p.name,
                "relpath": rel.as_posix(),
                "size_bytes": p.stat().st_size,
            }
        )
    return out


def _read_wisdom(research_root: Path) -> list[dict[str, Any]]:
    jsonl = research_root / "reviewer_brain" / "wisdom.jsonl"
    if not jsonl.is_file():
        return []
    items: list[dict[str, Any]] = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            items.append(
                {
                    "category": obj.get("category", "unknown"),
                    "content": obj.get("content", ""),
                    "weight": obj.get("weight", 1.0),
                    "timestamp": obj.get("timestamp", ""),
                }
            )
        except json.JSONDecodeError:
            continue
    return list(reversed(items))


def _read_reviews(research_root: Path, enc_key: str | None) -> dict[str, Any]:
    reviews_dir = research_root / "reviews"
    if not reviews_dir.is_dir():
        return {"key_configured": bool(enc_key), "reviews": [], "rejections": [], "locked_files": []}

    reviews: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    locked_files: list[str] = []

    for enc_file in sorted(reviews_dir.glob("*.review_log.enc.json")):
        idea_name = enc_file.name.replace(".review_log.enc.json", "")
        if not enc_key:
            locked_files.append(enc_file.name)
            continue
        try:
            payload = decrypt_decompress(enc_file.read_bytes(), key=enc_key)
        except Exception:
            locked_files.append(enc_file.name)
            continue

        editor = payload.get("editor", {})
        rec = {
            "idea": idea_name,
            "paper": payload.get("paper", ""),
            "timestamp": payload.get("timestamp", ""),
            "decision": editor.get("decision", "Unknown"),
            "rejection_risk_pct": editor.get("rejection_risk_pct", 100),
            "novelty_score": editor.get("novelty_score"),
            "rigor_score": editor.get("rigor_score"),
            "verdict": editor.get("verdict", ""),
            "dealbreakers": editor.get("dealbreakers", []),
            "token_stats": payload.get("token_stats", {}),
            "evolution": payload.get("evolution", {}),
        }
        reviews.append(rec)
        if str(rec["decision"]).lower() == "reject" or int(rec["rejection_risk_pct"]) >= 75:
            rejections.append(rec)

    return {
        "key_configured": bool(enc_key),
        "reviews": reviews,
        "rejections": rejections,
        "locked_files": locked_files,
    }


def safe_read_scoped_file(research_root: Path, scope: str, relpath: str) -> tuple[bool, str]:
    """Read a text file strictly contained within ideas, drafts, or papers."""
    scope_map = {
        "ideas": research_root / "ideas",
        "drafts": research_root / "drafts",
        "papers": research_root / "papers",
    }
    base = scope_map.get(scope)
    if base is None:
        return False, f"Invalid scope: {scope}"
    target = (base / relpath).resolve()
    base_resolved = base.resolve()
    try:
        target.relative_to(base_resolved)
    except ValueError:
        return False, "Access denied: path escapes allowed scope."
    if not target.is_file():
        return False, f"File not found: {relpath}"
    if target.suffix.lower() in (".json", ".enc", ".pyc", ".bin") and target.name.endswith(".enc.json"):
        return False, "Encrypted files are displayed in the Evaluations tab."
    return True, target.read_text(encoding="utf-8", errors="replace")


def build_workspace_snapshot(
    research_root: Path | None = None,
    cognitive_log_path: Path = DEFAULT_LOG_PATH,
    enc_key: str | None = None,
) -> dict[str, Any]:
    """Aggregate all ideas, folders, reviews, rejections, drafts, papers, wisdom, and cognitive telemetry."""
    research_root = Path(research_root) if research_root is not None else (REPO_ROOT / "research")
    if enc_key is None:
        load_dotenv_if_present()
        enc_key = os.getenv("IDEA_ENC_KEY")

    ideas_dir = research_root / "ideas"
    ideas: list[dict[str, Any]] = []
    if ideas_dir.is_dir():
        for child in sorted(ideas_dir.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir() or child.name.startswith(".") or child.name == "__pycache__":
                continue
            ideas.append(
                {
                    "name": child.name,
                    "is_factory": child.name == "peer-review-factory",
                    "files": _list_files(child, max_depth=1),
                }
            )

    review_data = _read_reviews(research_root, enc_key=enc_key)
    wisdom = _read_wisdom(research_root)
    cognitive = summarize_cognitive_evolution(
        repo_root=REPO_ROOT,
        log_path=cognitive_log_path,
        review_metrics=review_data["reviews"],
        wisdom_count=len(wisdom),
        ideas_count=len(ideas),
    )

    return {
        "ideas": ideas,
        "drafts": _list_files(research_root / "drafts", max_depth=1),
        "papers": _list_files(research_root / "papers", max_depth=1),
        "reviews": review_data["reviews"],
        "rejections": review_data["rejections"],
        "locked_reviews": review_data["locked_files"],
        "key_configured": review_data["key_configured"],
        "wisdom": wisdom[:100],
        "wisdom_count": len(wisdom),
        "cognitive": cognitive,
    }


def make_handler(research_root: Path, cognitive_log_path: Path):
    class ChamberHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return  # Keep console clean

        def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _send_html(self, html: str) -> None:
            raw = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                html_path = GUI_DIR / "index.html"
                self._send_html(html_path.read_text(encoding="utf-8"))
                return
            if parsed.path == "/api/overview":
                self._send_json(
                    build_workspace_snapshot(
                        research_root=research_root,
                        cognitive_log_path=cognitive_log_path,
                    )
                )
                return
            if parsed.path == "/api/cognitive":
                snap = build_workspace_snapshot(
                    research_root=research_root,
                    cognitive_log_path=cognitive_log_path,
                )
                self._send_json(snap["cognitive"])
                return
            if parsed.path == "/api/file":
                qs = parse_qs(parsed.query)
                scope = (qs.get("scope") or [""])[0]
                relpath = (qs.get("path") or [""])[0]
                ok, content = safe_read_scoped_file(research_root, scope, relpath)
                if not ok:
                    self._send_json({"error": content}, status=HTTPStatus.BAD_REQUEST)
                else:
                    self._send_json({"scope": scope, "path": relpath, "content": content})
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            body_bytes = self.rfile.read(length) if length > 0 else b"{}"
            try:
                body = json.loads(body_bytes.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
                return

            if parsed.path == "/api/cognitive/log":
                try:
                    entry = append_cognitive_checkin(
                        scores=body.get("scores", {}),
                        note=str(body.get("note", "")),
                        log_path=cognitive_log_path,
                    )
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                snap = build_workspace_snapshot(
                    research_root=research_root,
                    cognitive_log_path=cognitive_log_path,
                )
                self._send_json({"saved": entry, "cognitive": snap["cognitive"]}, status=HTTPStatus.CREATED)
                return

            if parsed.path == "/api/audit/run":
                load_dotenv_if_present()
                enc_key = os.getenv("IDEA_ENC_KEY")
                if not enc_key:
                    self._send_json(
                        {"error": "IDEA_ENC_KEY is not configured in .env; cannot persist encrypted reviews."},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                auditor = _load_sibling_auditor()
                ledger = auditor.audit_sibling_ideas(
                    ideas_root=research_root / "ideas",
                    reviews_dir=research_root / "reviews",
                    drafts_dir=research_root / "drafts",
                    papers_dir=research_root / "papers",
                    enc_key=enc_key,
                    allow_search=bool(body.get("allow_search", False)),
                    force_paper=bool(body.get("force_paper", False)),
                )
                self._send_json({"status": "ok", "ledger": ledger})
                return

            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    return ChamberHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch HisMastersChamber Ideas & Cognitive GUI")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    args = parser.parse_args()

    research_root = REPO_ROOT / "research"
    handler_cls = make_handler(research_root, DEFAULT_LOG_PATH)
    server = ThreadingHTTPServer((args.host, args.port), handler_cls)
    print(f"HisMastersChamber GUI running at http://{args.host}:{args.port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
