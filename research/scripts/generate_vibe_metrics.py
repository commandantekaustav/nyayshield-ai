#!/usr/bin/env python3
"""Generate Vibe‑Coding metrics for the whole repository.
Outputs a JSON fragment that will be merged into `docs/chamber/data.json`.
Metrics collected:
  * Commits in the last week
  * Lines added / removed in the last week
  * Distinct file extensions touched
"""
import subprocess, json, pathlib, datetime, os

def run(cmd):
    return subprocess.check_output(cmd, text=True).strip()

def week_timestamp():
    # start of current week (Monday 00:00 UTC)
    now = datetime.datetime.utcnow()
    start = now - datetime.timedelta(days=now.weekday())
    return start.isoformat() + "Z"

def recent_commits(limit=200):
    log = run(["git", "log", f"-n{limit}", "--pretty=%ct %H"]).splitlines()
    now_ts = datetime.datetime.utcnow().timestamp()
    week_secs = 7 * 24 * 3600
    recent = []
    for line in log:
        ts_str, sha = line.split()
        ts = int(ts_str)
        if now_ts - ts < week_secs:
            recent.append(sha)
    return recent

def commit_stats():
    commits = recent_commits()
    added = removed = 0
    for sha in commits:
        diff = run(["git", "show", "--numstat", sha])
        for dline in diff.splitlines():
            parts = dline.split('\t')
            if len(parts) >= 3 and parts[0].isdigit():
                added += int(parts[0])
                removed += int(parts[1])
    return {
        "commits_last_week": len(commits),
        "lines_added_last_week": added,
        "lines_removed_last_week": removed,
    }

def language_diversity():
    files = run(["git", "ls-files"]).splitlines()
    exts = {os.path.splitext(f)[1].lower() for f in files if f}
    return {"distinct_extensions": len(exts), "extensions": sorted(list(exts))}

def main():
    data = {
        "timestamp": week_timestamp(),
        **commit_stats(),
        **language_diversity(),
    }
    out_path = pathlib.Path('docs/chamber/vibe_metrics.json')
    out_path.write_text(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
