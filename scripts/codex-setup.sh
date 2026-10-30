#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"
python_bin=${ERP_PYTHON:-python3}

"$python_bin" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else "Use Python 3.12 para este projeto.")'
"$python_bin" -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt

echo "Dependências instaladas. Execute: sh scripts/codex-check.sh"
