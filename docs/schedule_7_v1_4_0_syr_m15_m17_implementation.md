# Schedule 7 v1.4.0 — accepted selective Syracuse mini-banks and R160 extension

**Unpublished working draft.** User authorized incorporation on October 19, 2026. The published `main` default remains v1.3.3.

## Accepted scope

Starting from published v1.3.3, the reproducible draft builder applies three consecutive overlays:

1. `config/optimizations/schedule_7_v1_4_0_r106.json` — accepted BTV–SYR–BTV late utilization.
2. `config/optimizations/schedule_7_v1_4_0_r110.json` — accepted DAY–SYR–DAY turn, including DAY-M0.
3. `config/optimizations/schedule_7_v1_4_0_syr_m15_m17_r160.json` — newly accepted SYR-M15/M17 selective return/onward pairs and R160 extension.

The selective mini-banks are **SYR-M15 14:45–15:45** and **SYR-M17 17:15–18:15**, raising the logical Syracuse bank count from 7 to 9, with no new physical gates/stands.

| Bank | Route | Inbound SYR | Onward from SYR |
| --- | --- | --- | --- |
| M15 | R110 | MHT–SYR 15:00 | SYR–PIT 15:40 |
| M17 | R106 | HPN–SYR 17:30 | SYR–BTV 18:10 |
| M17 | R130 | PWM–SYR 17:30 | SYR–BUF 18:10 |
| M17 | R131 | ALB–SYR 17:30 | SYR–ORH 18:10 |

R160 uses M15 with BTV–SYR at 14:08–15:00, SYR–PWM at 15:40–16:48, then adds **PWM–PHF 17:28–19:09** and **PHF–PWM 19:49–21:30**. It retains the ACY originator, PWM terminator and AM day-4 placement.

R160 inflight utilization increases from **5h44m to 9h06m** (506 minutes in the 06:00–22:00 critical window). R107 is not changed by this approval.

## Native validation and passenger-network qualification

Rebuilt `data/schedules/schedule_7_v1_4_0_draft/`:

- **1,259 flights, 188 routes, 17 routing lines**
- **Zero effective operating errors**; structural, overnight, planning and fixed gate/stand inventories all pass
- Fleet counts unchanged; published v1.3.3 canonical and app manifest not modified
- The selective four-return and R160 extension candidate was screened before acceptance in `outputs/schedule_7_v1_4_0_utilization/syr_selective_native.json`.

The candidate's directional passenger-network comparison versus the preceding 1,257-flight R106/R110-only draft found **one gained** geographically reasonable market (FWA→PWM, 0.6 underlying daily directional O-D), **one lost** (MCI→PWM, 7.2), **74 faster** and **53 slower** fastest reasonable itineraries. These counts are directional market comparisons, not passenger loads.

**Open commercial issue:** The new 15:40 SYR→PWM flight leaves before the existing MCI→SYR flight arrives at 16:42; the later SYR→PWM flight at 22:20 is outside the four-hour maximum connection window for that MCI arrival. Thus MCI→PWM loses its previously reasonable one-stop. No workaround has been adopted or silently assumed in this draft. Restore a reasonable connection (potentially an evening SYR→PWM frequency using another route) in a separately validated change if feasible. This is a documented tradeoff for user review, not a hard-stop operating error.

## Rebuild

Run `python scripts/build_schedule_7_v1_4_0_draft.py` to reproduce this cumulative accepted draft and all native structural, planning, overnight, timetable, gate and operating reports.

There is no v1.4.0 release package, web-default change, merge to `main`, or publication approval yet.
