#!/usr/bin/env bash
# Збирає звіт {{PARTNER_DISPLAY}} локально і публікує на GitHub Pages
# (лише index.html у публічному репо {{PUBLIC_REPO}}).
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "→ Installing Python deps (if needed)..."
python3 -m pip install -q -r requirements.txt

echo "→ Generating index.html from Databricks..."
python3 generate_report.py

DEPLOY_DIR=$(mktemp -d)
trap 'rm -rf "$DEPLOY_DIR"' EXIT

echo "→ Publishing to {{PUBLIC_REPO}} (index.html only)..."
git clone --depth 1 https://github.com/mykhailobrynchak-dev/{{PUBLIC_REPO}}.git "$DEPLOY_DIR"
cp index.html "$DEPLOY_DIR/index.html"
cd "$DEPLOY_DIR"
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add index.html
if git diff --cached --quiet; then
  echo "Nothing to commit (report unchanged on Pages)."
else
  git commit -m "Оновлення звіту {{PARTNER_DISPLAY}}: $(date +'%Y-%m-%d %H:%M')"
  git push origin main
fi

echo "✓ Published: https://mykhailobrynchak-dev.github.io/{{PUBLIC_REPO}}/"
echo "  Refresh the page in ~30s (Cmd+Shift+R)."
