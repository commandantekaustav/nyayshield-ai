"""Unit and HTTP integration tests for the Ideas Chamber GUI & Cognitive Evolution Tracker."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from research.skills.peer_review_pipeline.encrypt_util import compress_encrypt, generate_key

GUI_DIR = Path(__file__).resolve().parents[1]
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tracker = _load_module("cognitive_tracker_test", GUI_DIR / "cognitive_tracker.py")
gui_server = _load_module("ideas_chamber_server_test", GUI_DIR / "server.py")


class TestCognitiveTrackerAndGUI(unittest.TestCase):
    def test_ols_trend_classifications(self) -> None:
        self.assertEqual(tracker.compute_ols_trend([])["status"], "BASELINE")
        self.assertEqual(tracker.compute_ols_trend([7.0])["status"], "BASELINE")
        self.assertEqual(tracker.compute_ols_trend([5.0, 6.0, 7.5, 8.5])["status"], "INCLINING")
        self.assertEqual(tracker.compute_ols_trend([8.5, 7.5, 6.0, 5.0])["status"], "DECLINING")
        self.assertEqual(tracker.compute_ols_trend([7.0, 7.02, 6.99, 7.01])["status"], "STABLE")

    def test_checkin_validation_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "cognitive_log.jsonl"
            s1 = {"intelligence": 6, "memory": 6, "focus": 6, "creativity": 7, "reasoning": 6, "energy": 7}
            s2 = {"intelligence": 8, "memory": 5, "focus": 6, "creativity": 9, "reasoning": 8, "energy": 7}
            tracker.append_cognitive_checkin(s1, note="day 1", log_path=log_path)
            tracker.append_cognitive_checkin(s2, note="day 2", log_path=log_path)

            summary = tracker.summarize_cognitive_evolution(log_path=log_path)
            self.assertEqual(summary["total_checkins"], 2)
            self.assertEqual(summary["abilities"]["intelligence"]["status"], "INCLINING")
            self.assertEqual(summary["abilities"]["memory"]["status"], "DECLINING")
            self.assertEqual(summary["abilities"]["focus"]["status"], "STABLE")

            with self.assertRaises(ValueError):
                tracker.append_cognitive_checkin({**s1, "memory": 12.0}, log_path=log_path)

    def test_path_traversal_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ideas" / "alpha").mkdir(parents=True)
            (root / "ideas" / "alpha" / "notes.md").write_text("# Alpha", encoding="utf-8")
            (root / "secret.txt").write_text("TOP SECRET", encoding="utf-8")

            ok, content = gui_server.safe_read_scoped_file(root, "ideas", "alpha/notes.md")
            self.assertTrue(ok)
            self.assertIn("Alpha", content)

            ok_bad, err = gui_server.safe_read_scoped_file(root, "ideas", "../secret.txt")
            self.assertFalse(ok_bad)
            self.assertIn("Access denied", err)

    def test_workspace_snapshot_decrypts_reviews_and_tracks_rejections(self) -> None:
        key = generate_key()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ideas" / "alpha").mkdir(parents=True)
            (root / "ideas" / "alpha" / "notes.md").write_text("# Alpha", encoding="utf-8")
            (root / "reviews").mkdir(parents=True)
            (root / "drafts").mkdir(parents=True)
            (root / "papers").mkdir(parents=True)

            payload = {
                "paper": "notes.md",
                "timestamp": "2026-11-23T00:00:00+00:00",
                "editor": {
                    "decision": "Reject",
                    "rejection_risk_pct": 92,
                    "novelty_score": 7,
                    "rigor_score": 2,
                    "verdict": "Decision: Reject | Risk: 92%",
                    "dealbreakers": [],
                },
            }
            (root / "reviews" / "alpha.review_log.enc.json").write_bytes(
                compress_encrypt(payload, key=key)
            )

            snap = gui_server.build_workspace_snapshot(
                research_root=root,
                cognitive_log_path=root / "cog.jsonl",
                enc_key=key,
            )
            self.assertEqual(len(snap["reviews"]), 1)
            self.assertEqual(len(snap["rejections"]), 1)
            self.assertEqual(snap["reviews"][0]["idea"], "alpha")

            # Without key, file is reported as locked rather than crashing
            snap_locked = gui_server.build_workspace_snapshot(
                research_root=root,
                cognitive_log_path=root / "cog.jsonl",
                enc_key="",
            )
            self.assertEqual(len(snap_locked["reviews"]), 0)
            self.assertEqual(snap_locked["locked_reviews"], ["alpha.review_log.enc.json"])

    def test_http_handler_routes_in_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ideas" / "alpha").mkdir(parents=True)
            (root / "ideas" / "alpha" / "notes.md").write_text("# Hello GUI", encoding="utf-8")
            cog_path = root / "cog.jsonl"
            handler_cls = gui_server.make_handler(root, cog_path)

            def _dispatch(method: str, path: str, body: dict | None = None) -> tuple[int, bytes]:
                raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
                h = handler_cls.__new__(handler_cls)
                h.path = path
                h.headers = {"Content-Length": str(len(raw_body))}
                h.rfile = io.BytesIO(raw_body)
                h.wfile = io.BytesIO()
                status_box = {"code": 0}
                h.send_response = lambda code, msg=None: status_box.__setitem__("code", int(code))
                h.send_header = lambda k, v: None
                h.end_headers = lambda: None
                if method == "GET":
                    h.do_GET()
                else:
                    h.do_POST()
                return status_box["code"], h.wfile.getvalue()

            code, html_bytes = _dispatch("GET", "/")
            self.assertEqual(code, 200)
            self.assertIn("HisMastersChamber", html_bytes.decode("utf-8"))

            code, ov_bytes = _dispatch("GET", "/api/overview")
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(ov_bytes)["ideas"][0]["name"], "alpha")

            code, post_bytes = _dispatch(
                "POST",
                "/api/cognitive/log",
                {
                    "scores": {
                        "intelligence": 8.5,
                        "memory": 8.0,
                        "focus": 7.5,
                        "creativity": 9.0,
                        "reasoning": 8.5,
                        "energy": 7.0,
                    },
                    "note": "in-memory route test",
                },
            )
            self.assertEqual(code, 201)
            self.assertEqual(json.loads(post_bytes)["cognitive"]["total_checkins"], 1)

            code, bad_bytes = _dispatch("GET", "/api/file?scope=ideas&path=../secret.txt")
            self.assertEqual(code, 400)
            self.assertIn("Access denied", json.loads(bad_bytes)["error"])


if __name__ == "__main__":
    unittest.main()
