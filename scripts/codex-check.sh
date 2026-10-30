#!/bin/sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"
python_bin=${ERP_PYTHON:-.venv/bin/python}

if [ ! -x "$python_bin" ]; then
    echo "Python não encontrado. Execute primeiro: sh scripts/codex-setup.sh" >&2
    exit 1
fi

# Este comando de desenvolvimento sempre verifica uma base SQLite local.
unset DB_HOST DB_NAME DB_USER DB_PASSWORD DB_PORT
export DJANGO_SETTINGS_MODULE=core.settings
export ERP_ENVIRONMENT=development DJANGO_DEBUG=1
export DJANGO_SECRET_KEY=codex-local-validation-only
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver
export DJANGO_SECURE_SSL_REDIRECT=0 DJANGO_SECURE_COOKIES=0
export PIX_ENABLED=1 PIX_SIMULATOR_WEBHOOK_TOKEN=codex-local-simulator-only

"$python_bin" -m ruff check .
"$python_bin" -m ruff format --check .
"$python_bin" manage.py check
"$python_bin" manage.py makemigrations --check --dry-run
"$python_bin" manage.py test
"$python_bin" -m unittest discover -s scripts/tests -v
sh -n erpctl instalar.sh atualizar.sh docker/entrypoint.sh scripts/codex-setup.sh scripts/codex-check.sh
