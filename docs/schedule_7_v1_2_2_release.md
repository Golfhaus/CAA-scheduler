# Schedule 7 v1.2.2

Released October 6, 2026 at the user's instruction to resume loading v1.2.2.
The release contains the previously approved draft: twelve additional daily
flights on Routes 702, 704, 341, 504, 338, 514 and 515, using existing aircraft.
Later overnight candidates remain analysis-only proposals.

| Route | Flying | Local times |
|---|---|---|
| 702 | SFB–JAX–SFB | 20:05–20:53; 21:33–22:21 |
| 704 | SFB–BHM–SFB | 20:19 ET–20:45 CT; 23:15 CT–01:41 ET next day |
| 341 | MSY–JAX–MSY | 18:24 CT–20:59 ET; 21:39 ET–22:14 CT |
| 504 | CLT–JAX–CLT | 19:34–20:45; 21:25–22:36 |
| 338 | SAV–JAX–SAV | 20:00–20:45; 21:25–22:10 |
| 514 → 515 | PIE–JAX overnight; JAX–PIE | 20:14–21:08; 06:20–07:14 next line day |

JAX-B15 runs 20:45–21:45 Eastern. The first two existing Route 515 flights
move nine minutes later, leaving 50 minutes at PIE after the morning return
and retaining their SYR bank alignment. All other existing flights retain
their identities and times.

The release has 1,128 flights, 181 routes and 20 lines. Structural, operating,
overnight, planning and gate checks pass, with zero effective operating errors
or hard-stop failures. Stand use remains 15 claims and 4,277 minutes.
Demand analysis measures relative local and connection opportunities; it is
not a passenger-load forecast. The connection audit describes the configured
timetable connection window.

Rebuild and verify:

```bash
PYTHONPATH=src python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_2_2.json
PYTHONPATH=src bash scripts/run_latest_regression.sh
PYTHONPATH=src python -m caa_scheduler build-web --output dist
```
