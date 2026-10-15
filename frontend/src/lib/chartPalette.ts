/**
 * Chart series colours, from the pastel reference palettes (Fruit Salad and the
 * pastel swatch sheet). Used by the pages outside the dashboard. Axes, gridlines
 * and status colours (danger, warning, info) are not part of this set.
 *
 * Pastels are light: on the ivory and white grounds the strokes sit near 1.5:1
 * contrast, below the 3:1 non-text guideline. Charts rely on hue plus labels.
 */
export const CHART_SERIES: string[] = [
  "#7e89ca", // Wave
  "#FFA7D7", // Watermelon Crush
  "#FFB598", // Mango Slushy
  "#D8BBF1", // Grape Attack
  "#a4c6e8", // Blush
  "#C08081", // Old Rose
  "#FFF2A8", // Lemon Meringue
  "#D8C3A5", // Hazelnut
];

/** The seven things a dashboard colour can say. Each has one meaning, never a position. */
export type Role = "positive" | "negative" | "volume" | "transfer" | "process" | "caution" | "pending";

/**
 * Dashboard colour roles, from the "Палитра для ваших проектов" sheet: Sea #ffd9ff,
 * Heaven #c7f3f6, Shine #fdfcf8, Blush #a4c6e8, Wave #7e89ca. Five swatches cannot
 * carry seven roles with distinct light and dark steps, so some roles use a
 * darker or lighter step of a sheet hue. Each step is noted in its comment.
 *
 *   fill    the bar, slice, area or tile
 *   stroke  an outline for fills that are pale against white (omitted otherwise)
 *   dash    a dashed outline: the role is "not known yet"
 *   ink     text and line colour on white, at least 4.5:1 (lines at least 3:1)
 *   icon    glyph colour on the fill, chosen for contrast
 */
export const ROLE: Record<Role, { fill: string; stroke?: string; dash?: string; ink: string; icon: string }> = {
  // Wave. Pregnant, or at or above the programme pregnancy rate.
  positive: { fill: "#7e89ca", ink: "#4f5aa8", icon: "#1B2030" },
  // Sea. Open, or below the programme rate. Outlined in a deeper mauve.
  negative: { fill: "#ffd9ff", stroke: "#9a5c9c", ink: "#8a4f8c", icon: "#1B2030" },
  // Blush. Counts of activity with no verdict. Outlined in a deeper blue.
  volume: { fill: "#a4c6e8", stroke: "#5f8fc4", ink: "#2f5f96", icon: "#1B2030" },
  // Heaven. A transfer event. Outlined in a deeper teal.
  transfer: { fill: "#c7f3f6", stroke: "#3f8f99", ink: "#2f7f88", icon: "#1B2030" },
  // Blush, deepened. Lab rates (maturation, cleavage, blastocyst).
  process: { fill: "#5f8fc4", ink: "#2f5f96", icon: "#1B2030" },
  // Wave, lightened. The model is not reliable enough to act on. Outlined in a deep Wave.
  caution: { fill: "#b8bee6", stroke: "#5a63a6", ink: "#5a63a6", icon: "#1B2030" },
  // Shine. Waiting: no outcome recorded yet. Hollow and dashed, so it reads as unknown.
  pending: { fill: "#fdfcf8", stroke: "#7d86a8", dash: "4 3", ink: "#5d6480", icon: "#1B2030" },
};

/** Fill per role, for code that needs only the colour. */
export const MEANING: Record<Role, string> = {
  positive: ROLE.positive.fill,
  negative: ROLE.negative.fill,
  volume: ROLE.volume.fill,
  transfer: ROLE.transfer.fill,
  process: ROLE.process.fill,
  caution: ROLE.caution.fill,
  pending: ROLE.pending.fill,
};

/** Props for a recharts Bar, Cell, Area or shape so that a role's fill and outline both apply. */
export function roleProps(role: Role) {
  const r = ROLE[role];
  return {
    fill: r.fill,
    stroke: r.stroke ?? r.fill,
    strokeWidth: r.stroke ? 1.25 : 0,
    strokeDasharray: r.dash,
  };
}

/**
 * 95% Wilson score interval for k successes in n, as fractions. Null when n is 0.
 * Used so a colour says something only when the data supports it.
 */
export function wilson(k: number, n: number): [number, number] | null {
  if (n <= 0) return null;
  const z = 1.96;
  const p = k / n;
  const denom = 1 + (z * z) / n;
  const centre = (p + (z * z) / (2 * n)) / denom;
  const half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / denom;
  return [Math.max(0, centre - half), Math.min(1, centre + half)];
}

/**
 * The verdict a group's colour gives, against the programme rate.
 *   positive  its whole 95% interval is above the programme rate: clearly higher
 *   negative  its whole interval is below it: clearly lower
 *   volume    the interval includes the programme rate: no clear difference
 * A bar that looks above or below by a point or two, with overlapping intervals,
 * is not coloured as if it were a finding.
 */
export function verdict(k: number, n: number, programme: number | null): Role {
  const ci = wilson(k, n);
  if (ci == null || programme == null) return "volume";
  if (ci[0] > programme) return "positive";
  if (ci[1] < programme) return "negative";
  return "volume";
}

/** Verdict from a rate and the number of transfers it is based on, when the counts are not to hand. */
export function verdictFromRate(rate: number | null | undefined, n: number, programme: number | null): Role {
  if (rate == null) return "volume";
  return verdict(Math.round(rate * n), n, programme);
}

const LABEL_INK = "#1B2030";

function luminance(hex: string): number {
  const h = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Label colour that reads best on a fill: white or the deep label ink. */
export function textOn(fill: string): string {
  const l = luminance(fill);
  const onWhite = 1.05 / (l + 0.05);
  const onInk = (l + 0.05) / (luminance(LABEL_INK) + 0.05);
  return onInk >= onWhite ? LABEL_INK : "#FFFFFF";
}
