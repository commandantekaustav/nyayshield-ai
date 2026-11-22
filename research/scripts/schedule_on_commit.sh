#!/usr/bin/env bash
# Installs the post-commit Git hook that triggers peer-review whenever
# a manuscript under research/ideas/**/manuscript.md is modified.
set -euo pipefail

HOOK_PATH=".git/hooks/post-commit"
cat <<'EOF' > "$HOOK_PATH"
#!/usr/bin/env bash
# Auto-run peer-review swarm on changed manuscripts under research/ideas/
git diff-tree --no-commit-id --name-only -r HEAD \
  | grep -E '^research/ideas/.*/manuscript\.md$' \
  | while read -r paper; do
      if [ -f "$paper" ]; then
        echo "[peer-review-factory] Auditing $paper ..."
        python research/scripts/run_review.py --paper "$paper" || true
      fi
    done
EOF

chmod +x "$HOOK_PATH"
echo "Installed on-commit hook at $HOOK_PATH"
