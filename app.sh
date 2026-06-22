#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${1:-}" == "--install-deps" ]]; then
  "${script_dir}/setup-deps.sh"
fi

cd "${script_dir}"
exec ./auto_model_docs/app_studio.sh
