#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
if [[ "${1:-core}" == "full" ]]; then
  python -m pip install -r requirements-full.txt
else
  python -m pip install -r requirements-core.txt
fi
printf '\nSetup complete. Start with: ./scripts/start_mac.sh\n'
