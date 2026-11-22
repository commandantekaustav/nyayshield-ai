import subprocess
from collections import defaultdict
import os
import re
import json
import urllib.request

IGNORE_EXTS = {'.lock', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.ico', '.woff', '.ttf'}
IGNORE_FILES = {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'}
DOC_EXTS = {'.md', '.txt', '.rst', '.json', '.yml', '.yaml'}

AUTHOR_MAP = {
    'vangaja rakshasha': 'Kaustav Basu',
}

# Core optical defect detection files refactored from Ishika's offline _ref_detection prototype
DETECTION_PROTOTYPE_FILES = {
    'backend/services/vision/image_prep.py',
    'backend/services/vision/geometry_guard.py',
    'frontend/src/components/AnnotationCanvas.tsx',
}

CONTRIBUTOR_ROLES = {
    'Kaustav Basu': (
        'Lead Architect — Full-Stack FastAPI/React, Vertex AI Pipeline, '
        'Production Refactoring, Crypto Vault, Legal Critic & GCP Deployment'
    ),
    'Ishika': (
        'Optical Defect Detection Prototype (Core Detection Logic in '
        '`services/vision/` & `AnnotationCanvas.tsx`, delivered offline via `.zip`)'
    ),
    'Anwesha': 'Pitch Deck & Presentation Slides *(Non-Code)*',
}


def normalize_author(author_name: str) -> str:
    author_name = author_name.strip()
    return AUTHOR_MAP.get(author_name, author_name)


def run_git(args):
    result = subprocess.run(
        ['git'] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        errors='ignore',
    )
    return result.stdout.strip()


def should_ignore(filepath: str) -> bool:
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
        "Accept": "application/vnd.github+json",
    }

    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/pulls?state=all&per_page=100",
            headers=headers,
        )
        with urllib.request.urlopen(req) as resp:
            pulls = json.loads(resp.read().decode())
            for pr in pulls:
                user = pr['user']['login']
                collab[user]['prs_opened'] += 1

                rev_req = urllib.request.Request(
                    f"https://api.github.com/repos/{repo}/pulls/{pr['number']}/reviews",
                    headers=headers,
                )
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
    stats = defaultdict(
        lambda: {
            'commits': 0,
            'code_added': 0,
            'docs_added': 0,
            'deleted': 0,
            'files': set(),
            'surviving_lines': 0,
        }
    )

    log_output = run_git(['log', '--no-merges', '--numstat', '--format=COMMIT_START|%aN'])
    current_author = None

    for line in log_output.splitlines():
        if line.startswith('COMMIT_START|'):
            raw_author = line.split('|', 1)[1].strip()
            current_author = normalize_author(raw_author)
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
        norm_path = filepath.replace('\\', '/')
        _, ext = os.path.splitext(norm_path)
        if should_ignore(norm_path) or ext.lower() in DOC_EXTS or not os.path.exists(filepath):
            continue

        # Attribute surviving lines of the 3 core optical detection files to Ishika
        # (offline _ref_detection prototype refactored & integrated into production by Kaustav)
        if norm_path in DETECTION_PROTOTYPE_FILES:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            stats['Ishika']['surviving_lines'] += line_count
            stats['Ishika']['code_added'] += line_count
            stats['Ishika']['files'].add(norm_path)
            if 'Kaustav Basu' in stats:
                stats['Kaustav Basu']['code_added'] = max(
                    0, stats['Kaustav Basu']['code_added'] - line_count
                )
                stats['Kaustav Basu']['files'].discard(norm_path)
            continue

        blame_output = run_git(['blame', '--line-porcelain', filepath])
        for line in blame_output.splitlines():
            if line.startswith('author '):
                author = normalize_author(line[7:])
                if author in stats:
                    stats[author]['surviving_lines'] += 1

    return stats


def generate_markdown(stats, collab):
    total_surviving = sum(d['surviving_lines'] for d in stats.values()) or 1
    total_commits = sum(d['commits'] for d in stats.values()) or 1

    scored = []
    for author, d in stats.items():
        if d['commits'] == 0 and d['surviving_lines'] == 0:
            continue
        code_share = d['surviving_lines'] / total_surviving
        commit_share = d['commits'] / total_commits
        doc_factor = min(d['docs_added'] / 500, 1.0) * 0.1
        impact_score = (code_share * 60) + (commit_share * 30) + (doc_factor * 100)
        scored.append((author, d, impact_score))

    scored.sort(key=lambda x: x[2], reverse=True)

    lines = [
        "### 🏆 Comprehensive Project Contributions",
        "| Contributor | Role & Contributed Scope | Git Commits | Core Code Added | Docs & Config | Refactored (Del) | Active Files | Final Code Ownership |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for author, d, _ in scored:
        ownership = (d['surviving_lines'] / total_surviving) * 100
        role = CONTRIBUTOR_ROLES.get(author, 'Contributor')
        commits_str = str(d['commits']) if d['commits'] > 0 else "— *(ported by Kaustav)*"
        docs_str = f"+{d['docs_added']:,}" if d['docs_added'] > 0 else "—"
        del_str = f"-{d['deleted']:,}" if d['deleted'] > 0 else "—"
        lines.append(
            f"| **{author}** | {role} | {commits_str} | +{d['code_added']:,} | {docs_str} | {del_str} | {len(d['files'])} | **{ownership:.1f}%** |"
        )

    # Transparent non-code contribution row
    lines.append(
        f"| **Anwesha** | {CONTRIBUTOR_ROLES['Anwesha']} | — | — | — | — | — | **Slide Deck** |"
    )
    lines.append(
        "\n> *Methodology & mathematical formulas governing code ownership, offline prototype porting, and future scoring are documented in [`team/boardroom/CONTRIBUTION_METHODOLOGY.md`](team/boardroom/CONTRIBUTION_METHODOLOGY.md).*"
    )

    if collab:
        lines.append("\n### 🤝 GitHub Pull Requests & Code Reviews")
        lines.append("| GitHub Handle | PRs Opened | Peer Reviews Given |")
        lines.append("| :--- | :---: | :---: |")
        for handle, c in sorted(
            collab.items(),
            key=lambda x: x[1]['reviews_given'] + x[1]['prs_opened'],
            reverse=True,
        ):
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
