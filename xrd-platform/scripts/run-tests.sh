#!/usr/bin/env bash
set -eu

repo_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    python_bin="$VIRTUAL_ENV/bin/python"
elif [ -x "$repo_root/xrd-platform/.venv/bin/python" ]; then
    python_bin="$repo_root/xrd-platform/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    python_bin="$(command -v python3)"
else
    echo "XRD tests require an executable Python interpreter" >&2
    exit 1
fi

cd "$repo_root"
exec "$python_bin" -m pytest -q xrd-platform/tests
