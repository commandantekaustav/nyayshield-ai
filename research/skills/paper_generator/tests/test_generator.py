"""Unit tests for the interactive academic paper generator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.skills.paper_generator.generator import (
    CANONICAL_SECTIONS,
    interactive_generate,
)


class TestPaperGenerator(unittest.TestCase):
    def test_interactive_accept_edit_and_latex_export(self) -> None:
        # Abstract -> edit, remaining 6 sections -> accept
        responses = iter(["e", "Custom edited abstract with 90% savings.", "a", "a", "a", "a", "a", "a"])
        citations = [{"title": "Offline Swarms", "year": 2025, "url": "https://arxiv.org/abs/2501.00001"}]

        with tempfile.TemporaryDirectory() as tmp:
            paths = interactive_generate(
                title="Peer-Review Factory",
                out_dir=tmp,
                citations=citations,
                input_fn=lambda _prompt: next(responses),
                print_fn=lambda _msg: None,
            )

            md_text = Path(paths["markdown"]).read_text(encoding="utf-8")
            tex_text = Path(paths["latex"]).read_text(encoding="utf-8")

            self.assertIn("Custom edited abstract with 90% savings.", md_text)
            self.assertIn("## References", md_text)
            for sec in CANONICAL_SECTIONS:
                self.assertIn(f"## {sec}", md_text)

            self.assertIn("\\documentclass[11pt]{article}", tex_text)
            self.assertIn("90\\% savings", tex_text)
            self.assertIn("\\bibitem{ref1}", tex_text)


if __name__ == "__main__":
    unittest.main()
