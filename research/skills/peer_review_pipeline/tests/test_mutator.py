"""Unit tests for the bounded <= 1% genetic script mutator."""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from research.skills.peer_review_pipeline.mutator import (
    MAX_MUTATION_RATIO,
    compute_fitness,
    evolve_scripts,
    generate_candidates,
)


def _make_dummy_script(num_lines: int) -> str:
    header = [
        '"""Dummy agent script."""',
        "TEMPERATURE = 0.15",
        "MAX_WORDS = 250",
        "MIN_SAMPLE_SIZE = 30",
    ]
    padding = [f"# padding line {i}" for i in range(max(0, num_lines - len(header)))]
    return "\n".join(header + padding) + "\n"


class TestGeneticMutator(unittest.TestCase):
    def test_refuses_mutation_when_file_too_short_for_1_percent_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            short_file = Path(tmp) / "short_agent.py"
            short_file.write_text(_make_dummy_script(50), encoding="utf-8")
            candidates = generate_candidates([short_file], max_ratio=MAX_MUTATION_RATIO)
            self.assertEqual(candidates, [])

    def test_all_candidates_respect_1_percent_ceiling_and_valid_ast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_file = Path(tmp) / "agent_demo.py"
            agent_file.write_text(_make_dummy_script(120), encoding="utf-8")
            candidates = generate_candidates([agent_file], max_ratio=MAX_MUTATION_RATIO)
            self.assertGreater(len(candidates), 0)
            for cand in candidates:
                self.assertEqual(cand.changed_lines, 1)
                self.assertLessEqual(cand.change_ratio, 0.01)
                ast.parse(cand.mutated_source)

    def test_compute_fitness_default_weights(self) -> None:
        score = compute_fitness(risk_reduction=0.5, tokens_saved=0.4, runtime_increase=0.1)
        self.assertAlmostEqual(score, 0.6 * 0.5 + 0.3 * 0.4 - 0.1 * 0.1, places=5)

    def test_evolve_scripts_applies_best_within_1_percent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent_file = Path(tmp) / "agent_demo.py"
            agent_file.write_text(_make_dummy_script(120), encoding="utf-8")

            report = evolve_scripts(
                [agent_file],
                apply_best=True,
                git_tag_generation=None,
            )
            self.assertTrue(report["applied"])
            self.assertLessEqual(report["change_pct"], 1.0)
            self.assertEqual(report["changed_lines"], 1)
            ast.parse(agent_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
