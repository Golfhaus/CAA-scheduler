// Shared geometry for every chart showing time through an operating day.
// Minutes stay unwrapped so midnight and extended route days retain their order.
export function buildOperatingDayGrid(start, end) {
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    throw new RangeError("Timeline requires a finite, increasing minute range");
  }
  const duration = end - start;
  const percent = (minute) => (minute - start) / duration * 100;
  const ticks = [];
  for (let minute = Math.ceil(start / 60) * 60; minute <= end; minute += 60) {
    const hour = ((Math.floor(minute / 60) % 24) + 24) % 24;
    ticks.push({minute, left: percent(minute), label: String(hour).padStart(2, "0"),
      day: Math.floor(minute / 1440)});
  }
  const bands = [];
  for (let minute = start; minute < end;) {
    const next = Math.min(end, (Math.floor(minute / 60) + 1) * 60);
    bands.push({left: percent(minute), width: (next - minute) / duration * 100,
      shaded: Math.abs(Math.floor(minute / 60) % 2) === 0});
    minute = next;
  }
  return {hours: duration / 60, ticks, bands};
}
