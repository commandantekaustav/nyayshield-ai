import subprocess
from collections import defaultdict
import os
import re
import json
import urllib.request

IGNORE_EXTS = {'.lock', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.ico', '.woff', '.ttf'}
IGNORE_FILES = {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'}
DOC_EXTS = {'.md', '.txt', '.rst', '.json', '.yml', '.yaml'}

def run_git(args):
    result = subprocess.run(['git'] + args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors='ignore')
    return result.stdout.strip()

def should_ignore(filepath):
    filename = os.path.basename(filepath)
    _, ext = os.path.splitext(filename)
    return filename in IGNORE_FILES or ext.lower() in IGNORE_EXTS

def get_github_collaboration():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    collab = defaultdict(lambda: {'prs_opened': 0, 'reviews_given': 0})
    
    if not token or not repo:
        return collab

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    try:
        req = urllib.request.Request(f"https://github.com{repo}/pulls?state=all&per_page=100", headers=headers)
        with urllib.request.urlopen(req) as resp:
            pulls = json.loads(resp.read().decode())
            for pr in pulls:
                user = pr['user']['login']
                collab[user]['prs_opened'] += 1
                
                rev_req = urllib.request.Request(f"https://github.com{repo}/pulls/{pr['number']}/reviews", headers=headers)
                with urllib.request.urlopen(rev_req) as rev_resp:
                    reviews = json.loads(rev_resp.read().decode())
                    for r in reviews:
                        reviewer = r['user']['login']
                        if reviewer != user:
                            collab[reviewer]['reviews_given'] += 1
    except Exception:
        pass
    return collab

def analyze_repo():
    stats = defaultdict(lambda: {
        'commits': 0, 'code_added': 0, 'docs_added': 0, 
        'deleted': 0, 'files': set(), 'surviving_lines': 0
    })
    
    log_output = run_git(['log', '--no-merges', '--numstat', '--format=COMMIT_START|%aN'])
    current_author = None

    for line in log_output.splitlines():
        if line.startswith('COMMIT_START|'):
            current_author = line.split('|', 1).strip()
            stats[current_author]['commits'] += 1
        elif line and current_author and '\t' in line:
            parts = line.split('\t')
            if len(parts) == 3:
                added, deleted, filepath = parts
                if should_ignore(filepath):
                    continue
                _, ext = os.path.splitext(filepath)
                if added.isdigit():
                    if ext.lower() in DOC_EXTS:
                        stats[current_author]['docs_added'] += int(added)
                    else:
                        stats[current_author]['code_added'] += int(added)
                if deleted.isdigit():
                    stats[current_author]['deleted'] += int(deleted)
                stats[current_author]['files'].add(filepath)

    tracked_files = run_git(['ls-files']).splitlines()
    for filepath in tracked_files:
        _, ext = os.path.splitext(filepath)
        if should_ignore(filepath) or ext.lower() in DOC_EXTS or not os.path.exists(filepath):
            continue
        blame_output = run_git(['blame', '--line-porcelain', filepath])
        for line in blame_output.splitlines():
            if line.startswith('author '):
                author = line[7:].strip()
                if author in stats:
                    stats[author]['surviving_lines'] += 1

    return stats

def generate_markdown(stats, collab):
    total_surviving = sum(d['surviving_lines'] for d in stats.values()) or 1
    total_commits = sum(d['commits'] for d in stats.values()) or 1
    
    scored = []
    for author, d in stats.items():
        if d['commits'] == 0:
            continue
        code_share = d['surviving_lines'] / total_surviving
        commit_share = d['commits'] / total_commits
        doc_factor = min(d['docs_added'] / 500, 1.0) * 0.1
        impact_score = (code_share * 60) + (commit_share * 30) + (doc_factor * 100)
        scored.append((author, d, impact_score))

    scored.sort(key=lambda x: x, reverse=True)

    lines = [
        "### 🏆 Comprehensive Project Contributions",
        "| Contributor | Commits | Core Code Added | Docs & Config | Refactored (Del) | Active Files | Final Code Ownership |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    for author, d, _ in scored:
        ownership = (d['surviving_lines'] / total_surviving) * 100
        lines.append(
            f"| **{author}** | {d['commits']} | +{d['code_added']:,} | +{d['docs_added']:,} | -{d['deleted']:,} | {len(d['files'])} | **{ownership:.1f}%** |"
        )

    if collab:
        lines.append("\n### 🤝 GitHub Pull Requests & Code Reviews")
        lines.append("| GitHub Handle | PRs Opened | Peer Reviews Given |")
        lines.append("| :--- | :---: | :---: |")
        for handle, c in sorted(collab.items(), key=lambda x: x['reviews_given'] + x['prs_opened'], reverse=True):
            lines.append(f"| **@{handle}** | {c['prs_opened']} | {c['reviews_given']} |")

    return "\n".join(lines)

def update_readme(markdown_table):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(<!-- CONTRIB_START -->)(.*?)(<!-- CONTRIB_END -->)"
    replacement = f"\\1\n{markdown_table}\n\\3"
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count > 0:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(new_content)

if __name__ == "__main__":
    repo_stats = analyze_repo()
    gh_collab = get_github_collaboration()
    table = generate_markdown(repo_stats, gh_collab)
    update_readme(table)
