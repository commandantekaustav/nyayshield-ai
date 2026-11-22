---
name: skill-cognitive-evolution-telemetry
description: |
  Tracks, computes, and visualizes longitudinal personal cognitive evolution (Intelligence/Rigor, Creativity/Novelty, Memory/Wisdom Retention, Focus, Reasoning, and Idea Velocity) across timestamped check-ins and peer-review verdicts, classifying each ability as INCLINING, STABLE, or DECLINING via ordinary least-squares (OLS) trend slopes inside the Ideas Chamber GUI.
---

# Cognitive Evolution Telemetry Skill

## When to Use
Activate this skill when logging personal cognitive check-ins, auditing whether intelligence, memory, focus, or research rigor are inclining or declining over time, or launching/extending the Ideas Chamber GUI (`research/ideas/ideas-chamber-gui/`).

## Tracked Dimensions & Trend Math
1. **Data Sources**:
   - Manual / session check-ins stored in `research/ideas/ideas-chamber-gui/cognitive_log.jsonl` (scores `0–10` for `intelligence`, `memory`, `focus`, `creativity`, `reasoning`, `energy`, plus free-text notes).
   - Automated peer-review telemetry from `research/reviews/*.review_log.enc.json` & `grades_ledger.enc.json` (decrypted via `IDEA_ENC_KEY` in `.env`): `novelty_score`, `rigor_score`, `rejection_risk_pct`.
   - Local knowledge retention telemetry from `research/reviewer_brain/wisdom.jsonl` (count of distilled heuristics, verified benchmarks, and score logs).
2. **Incline / Stable / Decline Classification**:
   - For any ability series $y_0, y_1, \dots, y_{k-1}$ ordered by timestamp, compute the OLS slope $m$ over index $t = 0, \dots, k-1$:
     - `INCLINING` if $k \ge 2$ and $m > +0.05$
     - `DECLINING` if $k \ge 2$ and $m < -0.05$
     - `STABLE` otherwise (or `BASELINE` if $k < 2$)
3. **Interactive Local GUI**:
   - Zero-dependency local web server at `research/ideas/ideas-chamber-gui/server.py` (default `http://127.0.0.1:8765`).

## Commands
```powershell
# Launch the Ideas Chamber GUI & Cognitive Evolution Dashboard
backend\.venv\Scripts\python.exe research/ideas/ideas-chamber-gui/server.py --port 8765
```
