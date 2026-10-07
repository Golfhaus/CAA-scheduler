"""Screen and fit low-frequency round trips into the four approved v1.2.1 holds."""
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_schedule_7_v1_2_two_day_growth import TwoStopScreen
from caa_scheduler.bank_placement import _block_minutes, TIMEZONE_OFFSETS
from caa_scheduler.gate_export import export_gate_schedule
from caa_scheduler.io import read_json, write_json
from caa_scheduler.spacing import pairing_spacing_rule

BASE = "data/schedules/schedule_7_v1_2_0/canonical_schedule.json"
HOLDS = {701: (2, 3), 123: (1, 2), 321: (3, 4), 129: (3, 4)}


class HoldSearch:
    def __init__(self, base=None, *, allocate_gates=True):
        self.base = base if base is not None else read_json(ROOT / BASE)
        self.screen = TwoStopScreen(self.base)
        self.profiles = {p["fleet"]: p for p in read_json(ROOT / "config/policies/planning_rules_v7.json")
                         ["frequencyAllocation"]["fleetProfiles"]}
        self.legs = {l["id"]: l for l in self.base["legs"]}
        self.arrivals, self.departures = defaultdict(list), defaultdict(list)
        self.pairs = defaultdict(list)
        self.clocks = {}
        for l in self.base["legs"]:
            self.arrivals[l["destination"]].append(l)
            self.departures[l["origin"]].append(l)
            self.pairs[l["origin"], l["destination"]].append(l["departureMinute"])
            self.clocks[l["id"]] = self.screen.utc(l)
        self.weights = {od: sum(c["weight"] for c in choices) for od, choices in self.screen.options.items()}
        self.one_from, self.one_to = defaultdict(list), defaultdict(list)
        # A two-leg subpath can exceed the circuity limit for its own endpoints
        # while becoming valid when extended to a different final O-D market.
        # Retain all timed subpaths here; filter circuity on the complete journey.
        for hub in self.screen.hubs:
            for first in self.arrivals[hub]:
                for last in self.departures[hub]:
                    wait = (self.clocks[last["id"]][0] - self.clocks[first["id"]][1]) % 1440
                    if first["origin"] != last["destination"] and 30 <= wait <= 240:
                        choice = {"legs": (first["id"], last["id"]),
                                  "elapsed": self.clocks[first["id"]][2] + wait + self.clocks[last["id"]][2]}
                        self.one_from[first["origin"]].append(choice)
                        self.one_to[last["destination"]].append(choice)
        # Retimed intermediate screens can overfill a hold that added flying
        # will resolve. Final candidates still require full gate validation.
        if not allocate_gates:
            return
        self.gates = export_gate_schedule(self.base)
        self.occupancy = {}
        self.gate_capacity = {}
        for city in self.gates["cities"]:
            self.gate_capacity[city["code"]] = city["nGates"]
            counts = [0] * 1440
            for claim in city["claims"]:
                if claim["rowType"] == "gate":
                    self.mark(counts, claim["start"], claim["end"], 1)
            self.occupancy[city["code"]] = counts

    @staticmethod
    def mark(counts, start, end, amount):
        for t in range(int(start), int(end)):
            counts[t % 1440] += amount

    def bank(self, city, minute):
        if city not in self.screen.hubs or city == "BHM":
            return ""
        minute %= 1440
        banks = [b["id"] for b in self.base["hubBanks"]
                 if b["hub"] == city and b["startMinute"] <= minute < b["endMinute"]]
        return banks[0] if len(banks) == 1 else None

    def leg(self, a, b, departure, fleet, identifier="NEW"):
        block = _block_minutes(a, b, self.profiles[fleet], self.screen.cities)
        arrival = (departure - TIMEZONE_OFFSETS[self.screen.cities[a]["timezone"]] + block
                   + TIMEZONE_OFFSETS[self.screen.cities[b]["timezone"]])
        return {"id": identifier, "origin": a, "destination": b,
                "departureMinute": departure, "arrivalMinute": arrival}

    def spacing(self, added):
        by_pair = defaultdict(list)
        stations = Counter(l["origin"] for l in self.base["legs"])
        for leg in added:
            by_pair[leg["origin"], leg["destination"]].append(leg["departureMinute"])
            stations[leg["origin"]] += 1
        for (a, b), new in by_pair.items():
            times = sorted(self.pairs[a, b] + new)
            rule = pairing_spacing_rule(a, b, len(times), stations[a], self.screen.hubs,
                                        self.base["operatingPolicy"]["section26"])
            # One daily departure repeats after 24 hours; modulo arithmetic
            # would incorrectly turn that sole cyclic gap into zero.
            gaps = [1440] if len(times) == 1 else [(y - x) % 1440 for x, y in zip(times, times[1:] + times[:1])]
            if min(gaps) < 30 or sum(g < rule["minimumGapMinutes"] for g in gaps) > rule["allowedExceptions"]:
                return False
        return True

    @lru_cache(maxsize=None)
    def marginal_choices(self, a, b, departure, arrival):
        """New itineraries containing one added leg and otherwise baseline flights."""
        new = {"id": "NEW", "origin": a, "destination": b,
               "departureMinute": departure, "arrivalMinute": arrival}
        nd, na, nb = self.screen.utc(new)
        weights = defaultdict(float)
        def add(airports, elapsed, stops):
            if len(set(airports)) != len(airports):
                return
            origin, dest = airports[0], airports[-1]
            if not self.screen.od[origin][dest]:
                return
            circuity = sum(self.screen.distances[x, y] for x, y in zip(airports, airports[1:])) / self.screen.distances[origin, dest]
            if circuity <= 2.25:
                weights[origin, dest] += 0.35 ** stops / elapsed ** 2 / circuity ** 2
        add([a, b], nb, 0)
        if b in self.screen.hubs:
            for last in self.departures[b]:
                ld, la, lb = self.clocks[last["id"]]
                wait = (ld - na) % 1440
                if 30 <= wait <= 240:
                    add([a, b, last["destination"]], nb + wait + lb, 1)
            for choice in self.one_from[b]:
                first, last = (self.legs[i] for i in choice["legs"])
                wait = (self.clocks[first["id"]][0] - na) % 1440
                if 30 <= wait <= 240:
                    add([a, b, first["destination"], last["destination"]], nb + wait + choice["elapsed"], 2)
        if a in self.screen.hubs:
            for first in self.arrivals[a]:
                fd, fa, fb = self.clocks[first["id"]]
                wait = (nd - fa) % 1440
                if 30 <= wait <= 240:
                    add([first["origin"], a, b], fb + wait + nb, 1)
            for choice in self.one_to[a]:
                first, last = (self.legs[i] for i in choice["legs"])
                wait = (nd - self.clocks[last["id"]][1]) % 1440
                if 30 <= wait <= 240:
                    add([first["origin"], first["destination"], a, b], choice["elapsed"] + wait + nb, 2)
        if a in self.screen.hubs and b in self.screen.hubs:
            for first in self.arrivals[a]:
                fd, fa, fb = self.clocks[first["id"]]
                wait1 = (nd - fa) % 1440
                if not 30 <= wait1 <= 240:
                    continue
                for last in self.departures[b]:
                    ld, la, lb = self.clocks[last["id"]]
                    wait2 = (ld - na) % 1440
                    if 30 <= wait2 <= 240:
                        add([first["origin"], a, b, last["destination"]], fb + wait1 + nb + wait2 + lb, 2)
        return dict(weights)

    def score(self, added):
        by_leg = [self.marginal_choices(l["origin"], l["destination"], l["departureMinute"], l["arrivalMinute"]) for l in added]
        total = defaultdict(float)
        for weights in by_leg:
            for od, w in weights.items():
                total[od] += w
        values = [sum(self.screen.od[a][b] * w / (self.weights.get((a, b), 0) + total[a, b])
                      for (a, b), w in weights.items()) for weights in by_leg]
        return sum(values), values

    def gate_screen(self, route, before, after, added):
        hub = before["destination"]
        counts = {c: self.occupancy[c][:] for c in {hub, *(l["destination"] for l in added)}}
        city = next(c for c in self.gates["cities"] if c["code"] == hub)
        for claim in city["claims"]:
            if (claim["label"] == str(route) and claim["rowType"] == "gate"
                    and before["arrivalMinute"] <= claim["start"] < after["departureMinute"]):
                self.mark(counts[hub], claim["start"], claim["end"], -1)
        # Conservative gate touches around long holds; full gate allocation follows.
        for left, right in zip([before] + added, added + [after]):
            city = left["destination"]
            start, end = left["arrivalMinute"], right["departureMinute"]
            if end - start <= 150:
                self.mark(counts[city], start, end, 1)
            else:
                self.mark(counts[city], start, start + 45, 1)
                self.mark(counts[city], end - 60, end, 1)
        return all(max(v) <= self.gate_capacity[c] for c, v in counts.items())

    @staticmethod
    def grid(start, end):
        return sorted({start, end, *range((start + 4) // 5 * 5, end + 1, 5)}) if end >= start else []

    def search(self, route, following_shift=0, hold=None):
        sequence = sorted((l for l in self.base["legs"] if l["route"] == route), key=lambda l: l["sequenceWithinRoute"])
        first, second = hold if hold is not None else HOLDS[route]
        before, after = sequence[first - 1], sequence[second - 1]
        after = {**after, "departureMinute": after["departureMinute"] + following_shift,
                 "arrivalMinute": after["arrivalMinute"] + following_shift}
        hub, fleet = before["destination"], before["fleet"]
        earliest, deadline = before["arrivalMinute"] + 40, after["departureMinute"] - 40
        loops = []
        markets = []
        for dest in sorted(self.screen.cities):
            frequency = len(self.pairs[hub, dest])
            if frequency not in (1, 2):
                continue
            duration = _block_minutes(hub, dest, self.profiles[fleet], self.screen.cities)
            markets.append({"city": dest, "frequency": frequency, "blockMinutes": duration,
                            "localOdBothDirections": self.screen.od[hub][dest] + self.screen.od[dest][hub]})
            for departure in self.grid(earliest, deadline - 2 * duration - 40):
                out = self.leg(hub, dest, departure, fleet)
                if self.bank(hub, departure) is None or self.bank(dest, out["arrivalMinute"]) is None:
                    continue
                for back in self.grid(out["arrivalMinute"] + 40, min(out["arrivalMinute"] + 180,
                                 deadline - duration + TIMEZONE_OFFSETS[self.screen.cities[dest]["timezone"]]
                                 - TIMEZONE_OFFSETS[self.screen.cities[hub]["timezone"]])):
                    incoming = self.leg(dest, hub, back, fleet)
                    maximum = 1410 if dest in self.screen.hubs else 1260
                    if (back > maximum or incoming["arrivalMinute"] > deadline
                            or self.bank(dest, back) is None or self.bank(hub, incoming["arrivalMinute"]) is None):
                        continue
                    legs = [out, incoming]
                    if not self.spacing(legs) or not self.gate_screen(route, before, after, legs):
                        continue
                    score, values = self.score(legs)
                    loops.append({"city": dest, "legs": legs, "score": score, "legScores": values})
        # Keep up to 12 distinct timings per market for combining two round trips.
        by_market = defaultdict(list)
        for loop in sorted(loops, key=lambda x: -x["score"]):
            rows = by_market[loop["city"]]
            if len(rows) < 12 and not any(abs(r["legs"][0]["departureMinute"] - loop["legs"][0]["departureMinute"]) < 15
                                        and abs(r["legs"][1]["departureMinute"] - loop["legs"][1]["departureMinute"]) < 15 for r in rows):
                rows.append(loop)
        retained = [l for rows in by_market.values() for l in rows]
        plans = list(retained)
        for one in retained:
            for two in retained:
                if one["city"] == two["city"] or one["legs"][1]["arrivalMinute"] + 40 > two["legs"][0]["departureMinute"]:
                    continue
                legs = one["legs"] + two["legs"]
                if self.spacing(legs) and self.gate_screen(route, before, after, legs):
                    score, values = self.score(legs)
                    plans.append({"city": one["city"] + "+" + two["city"], "legs": legs, "score": score, "legScores": values})
        best = {}
        for p in sorted(plans, key=lambda x: -x["score"]):
            best.setdefault(p["city"], p)
        return {"route": route, "hub": hub, "fleet": fleet, "line": before["line"], "day": before["day"],
                "arrival": before["arrival"], "departure": after["departure"], "holdMinutes": after["departureMinute"] - before["arrivalMinute"],
                "followingFlightShiftMinutes": following_shift,
                "candidateTimings": len(loops), "markets": markets, "plans": sorted(best.values(), key=lambda x: -x["score"])}

    def overlay(self, selections, retimings=None):
        insertions, assignments = [], []
        for route, plan in selections.items():
            for index, leg in enumerate(plan["legs"], 1):
                item = {**leg, "id": f"V121-R{route}-{index}-{leg['origin']}-{leg['destination']}", "route": route}
                insertions.append(item)
                for op, city, minute in (("departure", leg["origin"], leg["departureMinute"]),
                                        ("arrival", leg["destination"], leg["arrivalMinute"])):
                    bank = self.bank(city, minute)
                    if bank:
                        assignments.append({"legId": item["id"], "operation": op, "bankId": bank})
        return {"schemaVersion": "1.0.0", "id": "schedule-7-v1.2.1-ground-hold-round-1",
                "baseSchedule": {"scheduleId": self.base["schedule"]["id"]},
                "schedule": {"id": "schedule_7_v1_2_1_feasibility_01", "version": "1.2.1-draft",
                             "label": "Schedule 7 v1.2.1 ground-hold draft", "status": "draft"},
                "initiative": {"kind": "productive_day_hold_flying", "authorizedBy": "user",
                               "scope": "Fill hub holds on Routes 701, 123, 321 and 129 using existing aircraft. Minor timing changes allowed. Publication is reserved to the user."},
                "insertLegs": insertions, "bankAssignmentsToAdd": assignments,
                "retimeLegs": retimings or []}


def main():
    search = HoldSearch()
    reports = [search.search(route) for route in HOLDS]
    write_json(ROOT / "builds/schedule_7_v1_2_1_hold_search.json", {"baseline": search.base["schedule"]["id"], "holds": reports})
    for report in reports:
        print(json.dumps({**{k: v for k, v in report.items() if k not in ("plans", "markets")}, "topPlans": report["plans"][:8]}, indent=2))


if __name__ == "__main__":
    main()
