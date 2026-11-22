"""Unit tests for .env loading and sibling-scanning peer-review-factory."""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from research.skills.peer_review_pipeline.encrypt_util import (
    decrypt_decompress,
    generate_key,
    load_dotenv_if_present,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AUDITOR_PATH = REPO_ROOT / "research" / "ideas" / "peer-review-factory" / "run_sibling_audit.py"


def _load_auditor():
    spec = importlib.util.spec_from_file_location("run_sibling_audit_test", AUDITOR_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSiblingAuditAndDotenv(unittest.TestCase):
    def test_load_dotenv_reads_key_without_overwriting_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            key1 = generate_key()
            env_file.write_text(
                f"# comment\nIDEA_ENC_KEY={key1}\nTEST_ONLY_VAR='hello'\n",
                encoding="utf-8",
            )
            prev_key = os.environ.pop("IDEA_ENC_KEY", None)
            prev_test = os.environ.pop("TEST_ONLY_VAR", None)
            try:
                loaded = load_dotenv_if_present(env_paths=(env_file,))
                self.assertEqual(loaded["IDEA_ENC_KEY"], key1)
                self.assertEqual(os.environ["TEST_ONLY_VAR"], "hello")

                # Existing os.environ must not be overwritten
                os.environ["TEST_ONLY_VAR"] = "keep_me"
                load_dotenv_if_present(env_paths=(env_file,))
                self.assertEqual(os.environ["TEST_ONLY_VAR"], "keep_me")
            finally:
                os.environ.pop("IDEA_ENC_KEY", None)
                os.environ.pop("TEST_ONLY_VAR", None)
                if prev_key is not None:
                    os.environ["IDEA_ENC_KEY"] = prev_key
                if prev_test is not None:
                    os.environ["TEST_ONLY_VAR"] = prev_test

    def test_sibling_audit_skips_factory_and_writes_common_folders(self) -> None:
        auditor = _load_auditor()
        key = generate_key()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ideas_root = root / "ideas"
            (ideas_root / "peer-review-factory").mkdir(parents=True)
            (ideas_root / "peer-review-factory" / "notes.md").write_text("# Factory self", encoding="utf-8")

            (ideas_root / "idea-alpha").mkdir(parents=True)
            (ideas_root / "idea-alpha" / "notes.md").write_text(
                "# Alpha\n## Abstract\nNovel offline swarm.\n## Methodology\nLocal embeddings.\n",
                encoding="utf-8",
            )

            (ideas_root / "idea-beta").mkdir(parents=True)
            (ideas_root / "idea-beta" / "manuscript.md").write_text(
                "# Beta\n## Abstract\nDeterministic triage.\n## Results\nn = 40, p = 0.01.\n",
                encoding="utf-8",
            )

            reviews_dir = root / "reviews"
            drafts_dir = root / "drafts"
            papers_dir = root / "papers"
            db_path = root / "reviewer_brain"

            ledger = auditor.audit_sibling_ideas(
                ideas_root=ideas_root,
                reviews_dir=reviews_dir,
                drafts_dir=drafts_dir,
                papers_dir=papers_dir,
                db_path=db_path,
                enc_key=key,
                allow_search=False,
                apply_evolution=False,
                force_paper=True,
            )

            audited_names = [r["idea"] for r in ledger["results"]]
            self.assertEqual(audited_names, ["idea-alpha", "idea-beta"])
            self.assertNotIn("peer-review-factory", audited_names)

            # Verify common output folders
            self.assertTrue((reviews_dir / "idea-alpha.review_log.enc.json").is_file())
            self.assertTrue((reviews_dir / "idea-beta.review_log.enc.json").is_file())
            self.assertTrue((reviews_dir / "grades_ledger.enc.json").is_file())
            self.assertTrue((drafts_dir / "idea-alpha_draft.md").is_file())
            self.assertTrue((drafts_dir / "idea-beta_draft.md").is_file())
            self.assertTrue((papers_dir / "idea-alpha_paper.md").is_file())
            self.assertTrue((papers_dir / "idea-alpha_paper.tex").is_file())

            # Verify ledger decrypts cleanly
            decrypted_ledger = decrypt_decompress(
                (reviews_dir / "grades_ledger.enc.json").read_bytes(), key=key
            )
            self.assertEqual(decrypted_ledger["ideas_audited"], 2)


if __name__ == "__main__":
    unittest.main()
