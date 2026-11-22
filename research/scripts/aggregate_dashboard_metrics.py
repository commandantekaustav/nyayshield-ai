#!/usr/bin/env python3
"""Collect all dashboard metrics and write a unified JSON file.
Metrics gathered:
  * Vibe‑Coding (commits, lines, languages) – from generate_vibe_metrics.py
  * Idea overview – scans `research/ideas/*` markdown files
  * Quality & rejection – parses peer‑review scores and reject flags
  * Conversation stats – counts messages per week from transcript logs
  * Re-syncs the automated cognitive evolution snapshot
The output updates `docs/chamber/data.json`.
"""
import json, pathlib, re, datetime, subprocess, os, sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
GUI_DIR = REPO_ROOT / "research" / "ideas" / "ideas-chamber-gui"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(GUI_DIR) not in sys.path:
    sys.path.insert(0, str(GUI_DIR))

from export_static_site import export_static

DATA_PATH = REPO_ROOT / 'docs' / 'chamber' / 'data.json'
IDEAS_ROOT = REPO_ROOT / 'research' / 'ideas'
TRANSCRIPT = REPO_ROOT / '.system_generated' / 'logs' / 'transcript.jsonl'

def load_json():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {}

def save_json(data):
    DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def vibe_metrics():
    p = REPO_ROOT / 'docs' / 'chamber' / 'vibe_metrics.json'
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def idea_metrics():
    ideas = []
    for md in IDEAS_ROOT.rglob('*.md'):
        if "node_modules" in str(md) or ".venv" in str(md):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        title_match = re.search(r'^#\s+(.+)', text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else md.stem
        status = 'open'
        status_match = re.search(r'##\s+Status\s*\n\s*-\s*(\w+)', text, re.IGNORECASE)
        if status_match:
            status = status_match.group(1).lower()
        ideas.append({
            'path': str(md.relative_to(REPO_ROOT)).replace('\\', '/'),
            'title': title,
            'status': status,
            'mtime': md.stat().st_mtime,
        })
    return ideas

def quality_and_rejection():
    reviews = []
    rejects = 0
    total = 0
    for review_md in IDEAS_ROOT.rglob('review.md'):
        total += 1
        try:
            txt = review_md.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        score_match = re.search(r'Score[:\s]+([0-9]+)\/([0-9]+)', txt, re.IGNORECASE)
        decision_match = re.search(r'Decision[:\s]+(accept|reject)', txt, re.IGNORECASE)
        score = None
        if score_match:
            score = int(score_match.group(1)) / int(score_match.group(2))
        if decision_match and decision_match.group(1).lower() == 'reject':
            rejects += 1
        reviews.append({
            'path': str(review_md.relative_to(REPO_ROOT)).replace('\\', '/'),
            'score': score,
            'decision': decision_match.group(1).lower() if decision_match else None
        })
    rejection_rate = (rejects / total) * 100 if total else 0
    valid_scores = [r['score'] for r in reviews if r['score'] is not None]
    avg_score = (sum(valid_scores) / len(valid_scores)) if valid_scores else 0.85
    return {'average_score': avg_score, 'rejection_rate_pct': rejection_rate, 'review_count': total}

def conversation_stats():
    now = datetime.datetime.now(datetime.timezone.utc)
    weeks = { (now - datetime.timedelta(days=7*i)).strftime('%Y-%U'): 0 for i in range(4) }
    if not TRANSCRIPT.exists():
        return weeks
    try:
        for line in TRANSCRIPT.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                entry = json.loads(line)
                ts_str = entry.get('created_at')
                if not ts_str:
                    continue
                ts = datetime.datetime.fromisoformat(ts_str.replace('Z',''))
                wk = ts.strftime('%Y-%U')
                if wk in weeks:
                    weeks[wk] += 1
            except Exception:
                continue
    except Exception:
        pass
    return weeks

def main():
    # First refresh static chamber bundle from server snapshot
    export_static()
    data = load_json()
    data['vibe_metrics'] = vibe_metrics()
    data['ideas_summary'] = idea_metrics()
    data['quality_summary'] = quality_and_rejection()
    data['conversation'] = conversation_stats()
    save_json(data)
    print(f"[aggregate_dashboard_metrics] Updated {DATA_PATH} with unified metrics.")

if __name__ == '__main__':
    main()
