import { num, pct, riskBand, signedPts } from "../lib/format";

describe("format helpers", () => {
  it("formats percentages and missing values", () => {
    expect(pct(0.1234)).toBe("12.3%");
    expect(pct(null)).toBe("—");
    expect(num(undefined)).toBe("—");
    expect(num(3.14159, 3)).toBe("3.142");
  });
  it("formats signed percentage-point differences", () => {
    expect(signedPts(-0.0345)).toBe("−3.5 pts");
    expect(signedPts(0.02)).toBe("+2.0 pts");
    expect(signedPts(0)).toBe("±0.0 pts");
  });
  it("bands risk without clinical labels", () => {
    expect(riskBand(0.05)).toBe("lower");
    expect(riskBand(0.15)).toBe("intermediate");
    expect(riskBand(0.3)).toBe("elevated");
  });
});
