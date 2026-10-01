# Schedule 7 v1.2.0

Released October 1, 2026 on the user's instruction to publish the approved
cumulative changes to the app. The app defaults to `schedule_7_v1_2_0`.

The release has 1,096 flights, 181 routes and 20 lines. CRJ900 operates three
closed lines (AB 10 days, AG 9, AJ 9). MAX9 operates A 13 days and B 10,
using 23 of the configured 35 aircraft and leaving 12 spare. The 13-day A
length follows the specifically approved two-day insertion and remains a
visible warning against the unchanged ordinary 9–12-day guideline.

The new Route 703/A3 and Route 704/A4 sequence adds 16 daily flights. Both
route-days operate every calendar day at different aircraft positions.
DAY–JAX rises to four flights each way: three MAX9 frequencies plus the
unchanged CRJ700. JAX–SFB, JAX–FLL, DAY–CMH, DAY–CAK and DAY–IND each rise
from one to two flights each way. PGD, PIE, SRQ and PIT retain one flight
each way; DAY–RFD retains three under the approved second-service priority.

See `schedule_7_v1_2_two_day_growth.md` for all 16 flights, insertion boundary,
frequency times, opportunity analysis and tradeoffs. The prior consolidation
is documented in `schedule_7_v1_2_0_feasibility.md`. Existing flights are
preserved by the growth insertion; the consolidation retains its documented
SFB–ABE ten-minute retiming and rotation exchanges.

Structural, planning and overnight validation pass. Effective operating
errors and hard-stop failures are zero. Fixed gate/stand capacity and
passenger handling checks pass. Stand use is 20 claims / 5,552 minutes,
unchanged from the approved consolidated draft and below v1.1.6's 21 claims /
6,188 minutes. No new bank or curfew exceptions are introduced.

Commercial and recovery limitations remain visible: 05:09 DAY–JAX and
18:36 JAX–DAY have weak connecting feed; DAY's 12:14 departure has a one-minute
bank margin; JAX's 18:47 departure has two minutes before its full-gate
period. New MAX9 airport compatibility at CAK, CMH and IND and separate crew
relief planning remain unevaluated. Connection opportunity values assume full
CAA capture without seat caps and are not predicted passenger loads.

The reproducible release chain starts from the frozen v1.1.6 canonical input
and applies the two approved consolidation overlays followed by the approved
two-day growth overlay. Build it with:

```bash
python -m caa_scheduler build-optimization-release config/optimizations/schedule_7_v1_2_0.json
```

Authoritative artifacts are under `data/schedules/schedule_7_v1_2_0` and are
listed in `web/schedules.json`. The published BHM connection audit and the
timetable's existing connection display policy remain unchanged; two-stop
demand accounting is a separate planning analysis.

Regression now concerns the latest release only, as explicitly instructed by
the user. Run `bash scripts/run_latest_regression.sh`; CI and the manual
Latest Schedule Regression workflow use the same checks. Old schedule
fixtures and superseded proposal tests are skipped. Historical app entries
remain available for reference. See `regression_policy.md`.
