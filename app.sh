#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${MODELDOCS_AUTO_INSTALL_PYDEPS:-}" == "1" ]]; then
  "${script_dir}/setup-deps.sh"
fi

cd "${script_dir}"
exec ./auto_model_docs/app_studio.sh
