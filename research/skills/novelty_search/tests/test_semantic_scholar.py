"""Unit tests for free-tier Semantic Scholar & arXiv targeted search."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from research.skills.novelty_search.semantic_scholar import (
    search_arxiv,
    search_semantic_scholar,
    targeted_search,
)


ARXIV_SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2501.00001v1</id>
    <published>2025-01-10T00:00:00Z</published>
    <title>Compact Swarms for Peer Review</title>
    <summary>We study token-minimalist local swarms for scientific review.</summary>
  </entry>
</feed>
"""


class TestNoveltySearch(unittest.TestCase):
    @patch("research.skills.novelty_search.semantic_scholar.requests.get")
    def test_semantic_scholar_parses_compact_fields(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "title": "Token-Minimalist Peer Review",
                    "year": 2025,
                    "citationCount": 42,
                    "abstract": "A" * 400,
                    "url": "https://semanticscholar.org/paper/1",
                }
            ]
        }
        mock_get.return_value = mock_resp

        hits = search_semantic_scholar("peer review swarm", limit=2)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["source"], "semantic_scholar")
        self.assertEqual(hits[0]["citationCount"], 42)
        self.assertEqual(len(hits[0]["abstract"]), 300)

    @patch("research.skills.novelty_search.semantic_scholar.requests.get")
    def test_arxiv_fallback_parses_atom_xml(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.text = ARXIV_SAMPLE_XML
        mock_get.return_value = mock_resp

        hits = search_arxiv("peer review swarm", limit=2)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["source"], "arxiv")
        self.assertEqual(hits[0]["year"], 2025)
        self.assertIn("Compact Swarms", hits[0]["title"])

    @patch("research.skills.novelty_search.semantic_scholar.search_arxiv")
    @patch("research.skills.novelty_search.semantic_scholar.search_semantic_scholar")
    def test_targeted_search_falls_back_gracefully(
        self, mock_s2: MagicMock, mock_arxiv: MagicMock
    ) -> None:
        mock_s2.side_effect = RuntimeError("429 Too Many Requests")
        mock_arxiv.return_value = [{"source": "arxiv", "title": "Fallback Paper", "year": 2025}]

        hits = targeted_search("offline swarm", limit=2)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["title"], "Fallback Paper")


if __name__ == "__main__":
    unittest.main()
