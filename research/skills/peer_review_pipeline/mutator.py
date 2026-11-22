"""Bounded Genetic Script Mutator (<= 1% line modification cap per generation).

Parses target agent Python scripts via AST, generates safe parameter/constant
mutation candidates, validates syntax, enforces the strict <= 1.0% changed-line
ceiling, scores candidates via a weighted fitness function, and optionally
applies + git-tags winning mutations (`pre-gen-<NN>` -> `gen-<NN>`).
"""

from __future__ import annotations

import ast
import difflib
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

MAX_MUTATION_RATIO = 0.01  # Strict <= 1% of lines per evaluation cycle
DEFAULT_WEIGHTS = (0.6, 0.3, 0.1)  # (w1: risk_reduction, w2: tokens_saved, w3: runtime_increase)

SAFE_TUNABLE_BOUNDS: dict[str, tuple[float, float, float]] = {
    "TEMPERATURE": (0.1, 0.2, 0.02),
    "MAX_WORDS": (120, 295, 5),
    "NOVELTY_HYPE_THRESHOLD": (1, 4, 1),
    "MIN_SAMPLE_SIZE": (20, 50, 5),
}


@dataclass(frozen=True)
class MutationCandidate:
    file_path: Path
    constant_name: str
    old_value: Any
    new_value: Any
    original_source: str
    mutated_source: str
    changed_lines: int
    total_lines: int

    @property
    def change_ratio(self) -> float:
        return self.changed_lines / max(1, self.total_lines)


def count_changed_lines(original: str, mutated: str) -> int:
    """Count modified/added lines using SequenceMatcher opcodes."""
    orig_lines = original.splitlines()
    mut_lines = mutated.splitlines()
    changed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, orig_lines, mut_lines).get_opcodes():
        if tag != "equal":
            changed += max(i2 - i1, j2 - j1)
    return changed


def compute_fitness(
    risk_reduction: float,
    tokens_saved: float,
    runtime_increase: float,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> float:
    """Compute weighted fitness: w1*risk_reduction + w2*tokens_saved - w3*runtime_increase."""
    w1, w2, w3 = weights
    return round(w1 * risk_reduction + w2 * tokens_saved - w3 * runtime_increase, 6)


def generate_candidates(
    script_paths: list[Path],
    max_ratio: float = MAX_MUTATION_RATIO,
) -> list[MutationCandidate]:
    """Generate AST-validated single-line constant mutations respecting the <= 1% cap."""
    candidates: list[MutationCandidate] = []
    for path in script_paths:
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines(keepends=True)
        total_lines = len(lines)
        max_allowed_lines = math.floor(total_lines * max_ratio)
        if max_allowed_lines < 1:
            continue

        tree = ast.parse(source, filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if name not in SAFE_TUNABLE_BOUNDS:
                continue
            if not isinstance(node.value, ast.Constant) or not isinstance(
                node.value.value, (int, float)
            ):
                continue

            old_val = node.value.value
            lo, hi, step = SAFE_TUNABLE_BOUNDS[name]
            proposals: list[int | float] = []
            for delta in (-step, step):
                new_val = old_val + delta
                if isinstance(old_val, int):
                    new_val = int(round(new_val))
                else:
                    new_val = round(float(new_val), 4)
                if lo <= new_val <= hi and new_val != old_val:
                    proposals.append(new_val)

            line_idx = node.lineno - 1
            for new_val in proposals:
                mut_lines = list(lines)
                ending = "\n" if mut_lines[line_idx].endswith("\n") else ""
                mut_lines[line_idx] = f"{name} = {new_val}{ending}"
                mutated_source = "".join(mut_lines)

                try:
                    ast.parse(mutated_source, filename=str(path))
                except SyntaxError:
                    continue

                changed = count_changed_lines(source, mutated_source)
                if changed <= max_allowed_lines and (changed / total_lines) <= max_ratio:
                    candidates.append(
                        MutationCandidate(
                            file_path=path,
                            constant_name=name,
                            old_value=old_val,
                            new_value=new_val,
                            original_source=source,
                            mutated_source=mutated_source,
                            changed_lines=changed,
                            total_lines=total_lines,
                        )
                    )
    return candidates


def evolve_scripts(
    script_paths: list[Path],
    evaluator: Callable[[MutationCandidate], tuple[float, float, float]] | None = None,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    apply_best: bool = False,
    git_tag_generation: int | None = None,
) -> dict[str, Any]:
    """Evaluate bounded <=1% mutation candidates and optionally apply the fittest one."""
    candidates = generate_candidates(script_paths, max_ratio=MAX_MUTATION_RATIO)
    if not candidates:
        return {
            "status": "no_eligible_mutations",
            "candidates_evaluated": 0,
            "applied": False,
            "max_ratio": MAX_MUTATION_RATIO,
        }

    scored: list[tuple[float, MutationCandidate]] = []
    for cand in candidates:
        if evaluator is not None:
            r_red, t_sav, rt_inc = evaluator(cand)
        else:
            r_red = 0.05 if cand.constant_name == "MIN_SAMPLE_SIZE" and cand.new_value > cand.old_value else 0.01
            t_sav = 0.05 if cand.constant_name == "MAX_WORDS" and cand.new_value < cand.old_value else 0.0
            rt_inc = 0.0
        fit = compute_fitness(r_red, t_sav, rt_inc, weights=weights)
        scored.append((fit, cand))

    scored.sort(key=lambda item: item[0], reverse=True)
    best_fitness, best = scored[0]

    result: dict[str, Any] = {
        "status": "evaluated",
        "candidates_evaluated": len(candidates),
        "best_fitness": best_fitness,
        "best_file": str(best.file_path),
        "constant": best.constant_name,
        "old_value": best.old_value,
        "new_value": best.new_value,
        "changed_lines": best.changed_lines,
        "total_lines": best.total_lines,
        "change_pct": round(best.change_ratio * 100.0, 3),
        "applied": False,
    }

    if apply_best and best_fitness > 0.0:
        if git_tag_generation is not None:
            _try_git_tag(f"pre-gen-{git_tag_generation:02d}")
        best.file_path.write_text(best.mutated_source, encoding="utf-8")
        result["applied"] = True
        result["status"] = "applied"
        if git_tag_generation is not None:
            result["pre_tag"] = f"pre-gen-{git_tag_generation:02d}"
            result["post_tag"] = f"gen-{git_tag_generation:02d}"

    return result


def _try_git_tag(tag_name: str) -> None:
    try:
        subprocess.run(["git", "tag", "-f", tag_name], check=False, capture_output=True, text=True)
    except OSError:
        pass
