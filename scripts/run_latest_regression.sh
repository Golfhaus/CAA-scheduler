#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tests/test_latest_schedule_release.py
python tests/test_latest_service_gains.py
python tests/test_latest_jax_bank.py
python tests/test_operating_validation.py
python tests/test_web_build.py
node --test tests/*.mjs

# v1.3.1 remains published while its discovered maintenance defect is repaired.
# Revalidate the pinned replacement draft as well; never accept new errors in it.
if [[ -f config/optimizations/schedule_7_v1_3_2_round_1.json ]]; then
  python scripts/build_schedule_7_v1_3_2_draft.py
  python tests/test_v1_3_2_maintenance_draft.py
  node scripts/audit_schedule_7_v1_3_2_maintenance.mjs --accepted
fi
