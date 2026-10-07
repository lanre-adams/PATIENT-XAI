export const pct = (x: number | null | undefined, digits = 1) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : `${(100 * x).toFixed(digits)}%`;

export const signedPts = (x: number) => `${x > 0 ? "+" : x < 0 ? "−" : "±"}${Math.abs(100 * x).toFixed(1)} pts`;

export const num = (x: number | null | undefined, digits = 2) =>
  x === null || x === undefined || Number.isNaN(x) ? "—" : x.toFixed(digits);

export function riskBand(r: number): "lower" | "intermediate" | "elevated" {
  if (r < 0.1) return "lower";
  if (r < 0.2) return "intermediate";
  return "elevated";
}
