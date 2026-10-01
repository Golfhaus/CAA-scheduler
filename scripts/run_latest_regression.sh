#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tests/test_latest_schedule_release.py
python tests/test_v120_two_day_growth.py
python tests/test_operating_validation.py
python tests/test_web_build.py
node --test tests/*.mjs
