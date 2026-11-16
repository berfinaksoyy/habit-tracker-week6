#!/usr/bin/env bash
# Run every guardrail the CI runs. Any failure stops the script with a non-zero exit code.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== ruff (lint) ==";    ruff check .
echo "== black (format) =="; black --check .
echo "== pytest (tests) =="; pytest
echo "All checks passed."
