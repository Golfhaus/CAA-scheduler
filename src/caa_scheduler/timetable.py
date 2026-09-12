from __future__ import annotations

from typing import Any


def export_timetable(canonical: dict[str, Any]) -> dict[str, Any]:
    schedule = canonical["schedule"]
    connection_window = schedule["connectionWindowMinutes"]
    served_codes = {
        code
        for leg in canonical["legs"]
        for code in (leg["origin"], leg["destination"])
    }
    cities = [
        {
            "code": city["code"],
            "name": city["name"],
            "isHub": city["role"] == "hub",
            "isFocusCity": city["role"] == "focus_city",
        }
        for city in canonical["cities"]
        if city["code"] in served_codes
    ]
    flights = [
        {
            "origin": leg["origin"],
            "dest": leg["destination"],
            "dep": leg["departure"],
            "arr": leg["arrival"],
            "flight": leg["flight"],
            "fleet": leg["fleet"],
        }
        for leg in sorted(canonical["legs"], key=lambda item: item["flight"])
    ]
    return {
        "label": schedule["label"],
        "minConnect": connection_window["minimum"],
        "maxConnect": connection_window["maximum"],
        "flightCount": len(flights),
        "cityCount": len(cities),
        "cities": cities,
        "flights": flights,
    }
