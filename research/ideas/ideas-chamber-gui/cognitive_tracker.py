"""Longitudinal Cognitive Evolution Tracker (Intelligence, Memory & Abilities).

Stores timestamped check-ins in ``cognitive_log.jsonl``, merges objective
peer-review metrics (novelty, rigor, rejection risk) and LanceDB/JSONL wisdom
memory growth, and computes OLS linear regression slopes to classify each
ability as INCLINING, STABLE, DECLINING, or BASELINE.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ABILITIES = (
    "intelligence",
    "memory",
    "focus",
    "creativity",
    "reasoning",
    "energy",
)

SLOPE_THRESHOLD = 0.05
DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "cognitive_log.jsonl"


def compute_ols_trend(values: list[float]) -> dict[str, Any]:
    """Compute OLS slope, delta, mean, latest, and directional status for a series."""
    n = len(values)
    if n == 0:
        return {
            "count": 0,
            "latest": None,
            "mean": None,
            "delta": 0.0,
            "slope": 0.0,
            "status": "BASELINE",
        }
    mean_y = sum(values) / n
    latest = values[-1]
    if n == 1:
        return {
            "count": 1,
            "latest": round(latest, 2),
            "mean": round(mean_y, 2),
            "delta": 0.0,
            "slope": 0.0,
            "status": "BASELINE",
        }

    mean_x = (n - 1) / 2.0
    num = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    slope = num / den if den > 0 else 0.0
    delta = latest - values[0]

    if slope > SLOPE_THRESHOLD:
        status = "INCLINING"
    elif slope < -SLOPE_THRESHOLD:
        status = "DECLINING"
    else:
        status = "STABLE"

    return {
        "count": n,
        "latest": round(latest, 2),
        "mean": round(mean_y, 2),
        "delta": round(delta, 2),
        "slope": round(slope, 4),
        "status": status,
    }


def load_cognitive_log(log_path: Path = DEFAULT_LOG_PATH) -> list[dict[str, Any]]:
    """Read all JSONL entries from ``log_path``."""
    if not log_path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def append_cognitive_checkin(
    scores: dict[str, float],
    note: str = "",
    log_path: Path = DEFAULT_LOG_PATH,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Validate (0–10) and append a cognitive check-in entry to ``log_path``."""
    clean_scores: dict[str, float] = {}
    for ability in ABILITIES:
        raw = scores.get(ability)
        if raw is None:
            raise ValueError(f"Missing required ability score: {ability}")
        val = float(raw)
        if not (0.0 <= val <= 10.0):
            raise ValueError(f"Score for '{ability}' must be between 0 and 10 (got {val}).")
        clean_scores[ability] = round(val, 2)

    entry = {
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "scores": clean_scores,
        "composite": round((sum(clean_scores.values()) / len(ABILITIES)) * 10.0, 2),
        "note": note.strip()[:500],
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def summarize_cognitive_evolution(
    log_path: Path = DEFAULT_LOG_PATH,
    review_metrics: list[dict[str, Any]] | None = None,
    wisdom_count: int = 0,
) -> dict[str, Any]:
    """Build full longitudinal evolution report across manual check-ins and peer-review telemetry."""
    entries = load_cognitive_log(log_path)
    ability_trends: dict[str, Any] = {}
    for ability in ABILITIES:
        series = [
            float(e["scores"][ability])
            for e in entries
            if isinstance(e.get("scores"), dict) and ability in e["scores"]
        ]
        trend = compute_ols_trend(series)
        trend["series"] = series[-30:]
        ability_trends[ability] = trend

    composite_series = [float(e["composite"]) for e in entries if "composite" in e]
    overall_trend = compute_ols_trend(composite_series)
    overall_trend["series"] = composite_series[-30:]

    # Objective peer-review telemetry trends
    reviews = review_metrics or []
    novelty_series = [float(r["novelty_score"]) for r in reviews if r.get("novelty_score") is not None]
    rigor_series = [float(r["rigor_score"]) for r in reviews if r.get("rigor_score") is not None]
    risk_series = [float(r["rejection_risk_pct"]) for r in reviews if r.get("rejection_risk_pct") is not None]

    return {
        "total_checkins": len(entries),
        "overall": overall_trend,
        "abilities": ability_trends,
        "objective_telemetry": {
            "ideas_evaluated": len(reviews),
            "wisdom_memory_items": wisdom_count,
            "novelty": compute_ols_trend(novelty_series),
            "rigor": compute_ols_trend(rigor_series),
            "rejection_risk": compute_ols_trend(risk_series),
        },
        "recent_entries": list(reversed(entries[-20:])),
    }
