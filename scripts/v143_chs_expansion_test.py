"""Smoke test the retained morning CHS connection in the canonical 12-flight v1.4.3 draft."""
import runpy,json
from pathlib import Path
runpy.run_path("scripts/build_schedule_7_v1_4_3_candidate.py",run_name="__main__")
c=json.loads(Path("data/schedules/schedule_7_v1_4_3_draft/canonical_schedule.json").read_text())
legs=[l for l in c["legs"] if l["route"]==178]
assert len(legs)==6
assert any((l["origin"],l["destination"],l["departureMinute"])==("SYR","CHS",310) for l in legs)
print("R178_CHS_MORNING_VALIDATED")
