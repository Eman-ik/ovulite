/**
 * Chart series colours, from the pastel reference palettes (Fruit Salad and the
 * pastel swatch sheet). Every chart reads from here, so changing the palette is
 * one edit. Axes, gridlines and status colours (danger, warning, info) are not
 * part of this set.
 *
 * Pastels are light: on the ivory and white grounds the strokes sit near 1.5:1
 * contrast, below the 3:1 non-text guideline. Charts rely on hue plus labels.
 */
export const CHART_SERIES: string[] = [
  "#66CAC8", // Berry Kiss
  "#FFA7D7", // Watermelon Crush
  "#FFB598", // Mango Slushy
  "#D8BBF1", // Grape Attack
  "#C8E6A0", // Lime Dreams
  "#C08081", // Old Rose
  "#D8C3A5", // Hazelnut
  "#CFE8FF", // Delicate Blue
];
