#!/usr/bin/env bash
set -euo pipefail

echo "Brain Dump installer"
echo "===================="

if ! command -v uv &>/dev/null; then
  echo "uv is required. Install it:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  # or: pip install uv"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating .venv and installing dependencies with uv..."
uv sync --all-groups

echo ""
echo "Installed brain-dump CLI into .venv"
echo ""
echo "Activate the environment:"
echo "  source .venv/bin/activate   # Linux/macOS"
echo "  .venv\\Scripts\\activate     # Windows"
echo ""
echo "Or run commands via uv:"
echo "  uv run brain-dump discover"
echo ""
echo "Next steps:"
echo "  1. uv run brain-dump init-config"
echo "  2. uv run brain-dump discover"
echo "  3. uv run brain-dump upload -y"
echo "  4. uv run brain-dump profile --open"
echo ""
echo "Optional: claude --plugin-dir ./plugin"
