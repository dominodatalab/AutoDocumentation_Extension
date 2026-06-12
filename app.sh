#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--install-deps" ]]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  "${script_dir}/setup-deps.sh"
fi

exec ./auto_model_docs/app_studio.sh
