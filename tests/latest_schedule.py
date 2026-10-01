"""Resolve current release fixtures from the app's authoritative default."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "web/schedules.json").read_text())
SCHEDULE_ID = MANIFEST["defaultScheduleId"]
ENTRY = next(s for s in MANIFEST["schedules"] if s["id"] == SCHEDULE_ID)
DIRECTORY = (ROOT / ENTRY["files"]["canonical"]).parent
CANONICAL = json.loads((ROOT / ENTRY["files"]["canonical"]).read_text())
RELEASE_CONFIG = ROOT / CANONICAL["provenance"]["optimizationRelease"]["config"]["filename"]
