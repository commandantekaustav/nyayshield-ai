#!/usr/bin/env python3
"""Collect all dashboard metrics and write a unified JSON file.
Metrics gathered:
  * Vibe‑Coding (commits, lines, languages) – from generate_vibe_metrics.py
  * Idea overview – scans `research/ideas/*` markdown files
  * Quality & rejection – parses peer‑review scores and reject flags
  * Conversation stats – counts messages per week from transcript logs
The output overwrites `docs/chamber/data.json`.
"""
import json, pathlib, re, datetime, subprocess, os

DATA_PATH = pathlib.Path('docs/chamber/data.json')
IDEAS_ROOT = pathlib.Path('research/ideas')
TRANSCRIPT = pathlib.Path('.system_generated/logs/transcript.jsonl')

def load_json():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text())
    return {}

def save_json(data):
    DATA_PATH.write_text(json.dumps(data, indent=2))

def vibe_metrics():
    try:
        return json.load(open('docs/chamber/vibe_metrics.json'))
    except Exception:
        return {}

def idea_metrics():
    ideas = []
    for md in IDEAS_ROOT.rglob('*.md'):
        text = md.read_text()
        title_match = re.search(r'^#\s+(.+)', text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else md.stem
        status = 'open'
        status_match = re.search(r'##\s+Status\s*\n\s*-\s*(\w+)', text, re.IGNORECASE)
        if status_match:
            status = status_match.group(1).lower()
        ideas.append({
            'path': str(md),
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
        txt = review_md.read_text()
        score_match = re.search(r'Score[:\s]+([0-9]+)\/([0-9]+)', txt, re.IGNORECASE)
        decision_match = re.search(r'Decision[:\s]+(accept|reject)', txt, re.IGNORECASE)
        score = None
        if score_match:
            score = int(score_match.group(1)) / int(score_match.group(2))
        if decision_match and decision_match.group(1).lower() == 'reject':
            rejects += 1
        reviews.append({'path': str(review_md), 'score': score, 'decision': decision_match.group(1).lower() if decision_match else None})
    rejection_rate = (rejects / total) * 100 if total else 0
    avg_score = (sum(r['score'] for r in reviews if r['score'] is not None) / len([r for r in reviews if r['score'] is not None])) if reviews else None
    return {'average_score': avg_score, 'rejection_rate_pct': rejection_rate, 'review_count': total}

def conversation_stats():
    now = datetime.datetime.utcnow()
    weeks = { (now - datetime.timedelta(days=7*i)).strftime('%Y-%U'): 0 for i in range(4) }
    if not TRANSCRIPT.exists():
        return weeks
    for line in TRANSCRIPT.read_text().splitlines():
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
    return weeks

def main():
    data = load_json()
    data['vibe_metrics'] = vibe_metrics()
    data['ideas'] = idea_metrics()
    data['quality'] = quality_and_rejection()
    data['conversation'] = conversation_stats()
    save_json(data)

if __name__ == '__main__':
    main()
