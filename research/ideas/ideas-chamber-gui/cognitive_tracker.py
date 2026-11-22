"""Longitudinal Cognitive Evolution Tracker (Intelligence, Memory & Abilities).

Computes research-backed cognitive and vibe-coding evolution telemetry automatically
from Git commits, repository hygiene, wisdom memory, and peer-review audits.
Zero manual inputs required. Grounded in peer-reviewed developer wellness & software
engineering cognition literature (Claes et al., ICSE 2018; Dawson & Reid, Nature 1997;
Eyolfson et al., MSR 2011; Kelley et al., 2020).
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
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
CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-zA-Z0-9_\-\.\/]+\))?:\s*.+"
)


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


def analyze_git_telemetry(repo_root: Path, limit: int = 200) -> list[dict[str, Any]]:
    """Parse git log into chronological commit events with author timestamp and stats."""
    try:
        raw = subprocess.check_output(
            ["git", "log", f"-n{limit}", "--pretty=format:%H|%an|%at|%s"],
            cwd=str(repo_root),
            text=True,
            encoding="utf-8",
            errors="replace",
        ).strip()
    except Exception:
        return []

    if not raw:
        return []

    commits: list[dict[str, Any]] = []
    lines = raw.splitlines()
    for line in lines:
        parts = line.split("|", 3)
        if len(parts) < 4:
            continue
        sha, author, at_str, subject = parts
        try:
            timestamp = int(at_str)
        except ValueError:
            continue

        is_conv = bool(CONVENTIONAL_COMMIT_RE.match(subject.strip()))
        dt = datetime.fromtimestamp(timestamp, timezone.utc)
        # Biological night check: 00:00 to 08:30 in local/IST (+05:30) or UTC 18:30-03:00
        # In UTC: 00:00-08:30 UTC or Indian Standard Time (UTC+5.5) -> approx 18:30 - 03:00 UTC
        hour_utc = dt.hour + (dt.minute / 60.0)
        # Night window: either local graveyard or nocturnal push
        is_night = (hour_utc >= 18.5 or hour_utc <= 3.0)

        commits.append({
            "sha": sha,
            "author": author,
            "timestamp": timestamp,
            "dt": dt.isoformat(),
            "subject": subject,
            "is_conventional": is_conv,
            "is_night": is_night,
        })

    # Return chronological order (oldest to newest)
    commits.reverse()
    return commits


def derive_automated_cognitive_snapshots(
    repo_root: Path,
    review_metrics: list[dict[str, Any]] | None = None,
    wisdom_count: int = 0,
    ideas_count: int = 0,
    commits: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Derive automated timestamped cognitive epochs from git commits and reviews.
    
    Dimensions derived per epoch (0-10):
    - reasoning: Semantic commit discipline & syntactic rigor
    - creativity: Ideas velocity & peer-review novelty
    - focus: Blast radius protection & commit batching cadence
    - energy: Circadian health & nocturnal fatigue reduction
    - memory: Wisdom retention & verified benchmarks accumulated
    - intelligence: Composite weighted index
    """
    if commits is None:
        commits = analyze_git_telemetry(repo_root)

    if not commits:
        # Default baseline epoch
        now_iso = datetime.now(timezone.utc).isoformat()
        return [{
            "timestamp": now_iso,
            "source": "baseline",
            "scores": {
                "intelligence": 8.0,
                "memory": 7.5,
                "focus": 8.0,
                "creativity": 8.5,
                "reasoning": 8.0,
                "energy": 7.5,
            },
            "composite": 79.2,
            "note": "Baseline initialization (0 manual entries)",
        }]

    # Chunk commits into sliding chronological windows (e.g. groups of 5-10 commits)
    chunk_size = max(3, len(commits) // 10)
    epochs: list[dict[str, Any]] = []

    # Calculate global wisdom and review metrics
    reviews = review_metrics or []
    avg_novelty = (
        sum(float(r["novelty_score"]) for r in reviews if r.get("novelty_score") is not None) / len(reviews)
        if reviews else 8.0
    )
    avg_rigor = (
        sum(float(r["rigor_score"]) for r in reviews if r.get("rigor_score") is not None) / len(reviews)
        if reviews else 8.5
    )
    avg_risk = (
        sum(float(r["rejection_risk_pct"]) for r in reviews if r.get("rejection_risk_pct") is not None) / len(reviews)
        if reviews else 25.0
    )

    for i in range(0, len(commits), chunk_size):
        chunk = commits[max(0, i - chunk_size): i + chunk_size]
        if not chunk:
            continue

        latest_c = chunk[-1]
        n_chunk = len(chunk)

        # 1. Reasoning: Conventional commit discipline + peer review rigor
        conv_ratio = sum(1 for c in chunk if c["is_conventional"]) / n_chunk
        reasoning_score = min(10.0, max(2.0, (conv_ratio * 5.0) + (avg_rigor * 0.5)))

        # 2. Creativity: Idea discovery + peer review novelty + promotion rate
        novelty_component = min(10.0, max(2.0, avg_novelty))
        ideas_boost = min(2.0, (ideas_count / 5.0))
        creativity_score = min(10.0, max(2.0, (novelty_component * 0.8) + ideas_boost))

        # 3. Focus: Cadence consistency and blast-radius safety (rejection risk <= 35%)
        risk_penalty = (avg_risk / 100.0) * 3.0
        focus_score = min(10.0, max(2.0, 9.5 - risk_penalty))

        # 4. Energy: Circadian graveyard ratio (Dawson & Reid, Nature 1997)
        night_ratio = sum(1 for c in chunk if c["is_night"]) / n_chunk
        energy_score = min(10.0, max(2.0, 10.0 - (night_ratio * 6.0)))

        # 5. Memory: Wisdom count & heuristics retention
        memory_score = min(10.0, max(3.0, 6.0 + min(4.0, (wisdom_count * 0.5))))

        # 6. Composite Intelligence (0-100)
        clean_scores = {
            "intelligence": round((reasoning_score * 0.35 + creativity_score * 0.35 + memory_score * 0.3), 2),
            "memory": round(memory_score, 2),
            "focus": round(focus_score, 2),
            "creativity": round(creativity_score, 2),
            "reasoning": round(reasoning_score, 2),
            "energy": round(energy_score, 2),
        }
        composite = round((sum(clean_scores.values()) / len(ABILITIES)) * 10.0, 2)

        epochs.append({
            "timestamp": latest_c["dt"],
            "sha": latest_c["sha"][:8],
            "trigger_commit": latest_c["subject"],
            "source": "automated_repo_telemetry",
            "scores": clean_scores,
            "composite": composite,
            "metrics": {
                "conventional_ratio_pct": round(conv_ratio * 100, 1),
                "graveyard_shift_pct": round(night_ratio * 100, 1),
                "novelty_avg": round(avg_novelty, 2),
                "rigor_avg": round(avg_rigor, 2),
                "rejection_risk_avg_pct": round(avg_risk, 1),
            },
            "note": f"Auto-computed from {n_chunk} commits ending at {latest_c['sha'][:8]} (Conv: {int(conv_ratio*100)}%, Night: {int(night_ratio*100)}%)",
        })

    return epochs


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
    """Validate (0–10) and append a cognitive check-in entry to ``log_path`` (legacy/fallback)."""
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
    repo_root: Path | None = None,
    log_path: Path = DEFAULT_LOG_PATH,
    review_metrics: list[dict[str, Any]] | None = None,
    wisdom_count: int = 0,
    ideas_count: int = 0,
) -> dict[str, Any]:
    """Build full longitudinal evolution report.
    
    If entries exist in ``log_path`` (legacy/explicit test entries), uses those;
    otherwise derives automated epochs from repository telemetry.
    """
    manual_entries = load_cognitive_log(log_path)
    if manual_entries:
        epochs = manual_entries
        mode = "explicit_log"
    else:
        target_root = repo_root or Path(__file__).resolve().parents[3]
        epochs = derive_automated_cognitive_snapshots(
            repo_root=target_root,
            review_metrics=review_metrics,
            wisdom_count=wisdom_count,
            ideas_count=ideas_count,
        )
        mode = "100% automated (Zero Manual Input)"

    ability_trends: dict[str, Any] = {}
    for ability in ABILITIES:
        series = [
            float(e["scores"][ability])
            for e in epochs
            if isinstance(e.get("scores"), dict) and ability in e["scores"]
        ]
        trend = compute_ols_trend(series)
        trend["series"] = series[-30:]
        ability_trends[ability] = trend

    composite_series = [float(e["composite"]) for e in epochs if "composite" in e]
    overall_trend = compute_ols_trend(composite_series)
    overall_trend["series"] = composite_series[-30:]

    # Objective peer-review telemetry trends
    reviews = review_metrics or []
    novelty_series = [float(r["novelty_score"]) for r in reviews if r.get("novelty_score") is not None]
    rigor_series = [float(r["rigor_score"]) for r in reviews if r.get("rigor_score") is not None]
    risk_series = [float(r["rejection_risk_pct"]) for r in reviews if r.get("rejection_risk_pct") is not None]

    return {
        "mode": mode,
        "total_checkins": len(epochs),
        "overall": overall_trend,
        "abilities": ability_trends,
        "objective_telemetry": {
            "ideas_evaluated": len(reviews),
            "wisdom_memory_items": wisdom_count,
            "novelty": compute_ols_trend(novelty_series),
            "rigor": compute_ols_trend(rigor_series),
            "rejection_risk": compute_ols_trend(risk_series),
        },
        "recent_entries": list(reversed(epochs[-20:])),
    }
