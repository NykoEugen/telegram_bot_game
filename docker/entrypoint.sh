#!/usr/bin/env bash
set -euo pipefail

# Allow skipping config validation during Alembic runs
export CONFIG_VALIDATE_ON_IMPORT=${CONFIG_VALIDATE_ON_IMPORT:-0}

alembic upgrade head

exec python start.py
