"""Unit tests for peer_review_pipeline manager, encryption, and vector store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.skills.peer_review_pipeline.encrypt_util import (
    compress_encrypt,
    decrypt_decompress,
    generate_key,
)
from research.skills.peer_review_pipeline.manager import (
    load_and_strip,
    process_paper,
    split_sections,
)
from research.skills.peer_review_pipeline.vector_store import WisdomVectorStore


SAMPLE_MANUSCRIPT = """# Novel Offline Swarm

## Abstract
We present a novel, unprecedented, first zero-cost offline swarm reducing tokens by up to 90%.

## Introduction
We hypothesize this works better than everything else.

## Methodology
We run three agents with deterministic hashing.

## Results
Across n=12 synthetic papers, runtime was 1.5s.

## Acknowledgments
Thanks to everyone.

## References
[1] Dummy reference 1.
[2] Dummy reference 2.
"""


class TestManagerPipeline(unittest.TestCase):
    def test_load_and_strip_removes_references_and_acknowledgments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "manuscript.md"
            p.write_text(SAMPLE_MANUSCRIPT, encoding="utf-8")
            stripped, stats = load_and_strip(p)
            self.assertNotIn("Dummy reference", stripped)
            self.assertNotIn("Thanks to everyone", stripped)
            self.assertIn("n=12 synthetic papers", stripped)
            self.assertGreater(stats["tokens_saved"], 0)
            self.assertGreater(stats["reduction_pct"], 0.0)

    def test_split_sections(self) -> None:
        sections = split_sections(SAMPLE_MANUSCRIPT)
        self.assertIn("zero-cost offline swarm", sections["abstract"])
        self.assertIn("hypothesize", sections["intro"])
        self.assertIn("three agents", sections["methods"])
        self.assertIn("n=12", sections["results"])

    def test_encrypt_decrypt_roundtrip_and_tamper_detection(self) -> None:
        key = generate_key()
        payload = {"paper": "demo.md", "risk": 85, "notes": ["[FATAL] n=12 < 30"]}
        blob = compress_encrypt(payload, key=key)
        self.assertIsInstance(blob, bytes)
        restored = decrypt_decompress(blob, key=key)
        self.assertEqual(restored, payload)

        # Flipping a ciphertext byte must fail authentication
        tampered = bytearray(blob)
        tampered[-1] ^= 0xFF
        with self.assertRaises(Exception):
            decrypt_decompress(bytes(tampered), key=key)

    def test_vector_store_insert_query_and_deduplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = WisdomVectorStore(db_path=Path(tmp) / "brain")
            r1 = store.add_wisdom("heuristic", "Require sample size n >= 30 with power analysis", weight=4.0)
            self.assertEqual(r1["action"], "inserted")
            # Near-identical insert should deduplicate
            r2 = store.add_wisdom("heuristic", "Require sample size n >= 30 with power analysis", weight=4.0)
            self.assertEqual(r2["action"], "deduplicated")
            self.assertEqual(store.count(), 1)

            hits = store.query_wisdom("small sample size power analysis", limit=3, category="heuristic")
            self.assertEqual(len(hits), 1)
            self.assertIn("n >= 30", hits[0]["content"])

    def test_full_process_paper_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            paper = tmp_path / "manuscript.md"
            paper.write_text(SAMPLE_MANUSCRIPT, encoding="utf-8")
            key = generate_key()

            result = process_paper(
                paper_path=paper,
                db_path=tmp_path / "brain",
                enc_key=key,
                allow_search=False,
                run_evolution=True,
                apply_evolution=False,
            )

            self.assertLess(result["skeptic"]["word_count"], 300)
            self.assertLess(result["methodologist"]["word_count"], 300)
            self.assertLess(result["editor"]["word_count"], 150)
            self.assertIn(result["editor"]["decision"], {"Reject", "Major Revision", "Minor Revision"})

            enc_file = Path(result["encrypted_log_path"])
            self.assertTrue(enc_file.exists())
            decrypted = decrypt_decompress(enc_file.read_bytes(), key=key)
            self.assertEqual(decrypted["paper"], "manuscript.md")
            self.assertEqual(decrypted["editor"]["decision"], result["editor"]["decision"])


if __name__ == "__main__":
    unittest.main()
