#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <code-root> <dataset-path>" >&2
  exit 1
}

[[ $# -eq 2 ]] || usage

CODE_ROOT="$1"
DATASET_PATH="$2"

HERE="$(cd "$(dirname "$0")" && pwd)"
SPEC="$HERE/doc_spec.yaml"

export DOMINO_PROJECT_ID="${DOMINO_PROJECT_ID:-REPLACE_WITH_YOUR_DOMINO_PROJECT_ID}"

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "error: export ANTHROPIC_API_KEY first" >&2
  exit 1
fi

if [[ "$DOMINO_PROJECT_ID" == "REPLACE_WITH_YOUR_DOMINO_PROJECT_ID" ]]; then
  echo "error: set DOMINO_PROJECT_ID in the environment or edit this script" >&2
  exit 1
fi

exec python "$HERE/main.py" \
  --spec "$SPEC" \
  --code-root "$CODE_ROOT" \
  --notebook \
  --dataset-path "$DATASET_PATH" \
  --provider anthropic
