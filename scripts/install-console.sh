#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_dir"
command -v docker >/dev/null
command -v npm >/dev/null
docker info >/dev/null
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
if command -v uv >/dev/null; then
  uv pip install --python .venv/bin/python -e '.[console,dev]'
else
  .venv/bin/python -m ensurepip --upgrade
  .venv/bin/python -m pip install -e '.[console,dev]'
fi
npm ci --prefix console
npm run check --prefix console
npm run build --prefix console
image='envoyproxy/envoy@sha256:57e14a549d7bd43c8d3f6d03e8cfa653e037d4b38e133acd9b54f38c524401b4'
if ! docker image inspect "$image" >/dev/null 2>&1; then docker pull "$image"; fi
echo 'Installed. Run ./scripts/run-console.sh'
