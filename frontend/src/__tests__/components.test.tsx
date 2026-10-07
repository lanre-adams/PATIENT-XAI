import { render, screen } from "@testing-library/react";
import { DisclaimerBanner, DISCLAIMER_TEXT } from "../components/DisclaimerBanner";
import { ExplanationPanel } from "../components/ExplanationPanel";
import { CausalNote } from "../pages/Counterfactual";
import type { Narrative } from "../lib/api";

const narrative: Narrative = {
  technical: ["Model: GRU deep ensemble.", "Calibration caveat: slope 0.94."],
  plain_language: {
    prediction: "For this synthetic profile, the model estimated an elevated chance (24.0%).",
    association: "These are associations the model learned from synthetic data. They should not be interpreted as clinical causes.",
    uncertainty: "Different versions of the model gave estimates between 20.0% and 28.0%.",
    counterfactual: "In a 'what-if' simulation ... Counterfactual scenarios represent model-based simulations.",
    causality: "A prediction model learns patterns, not cause and effect.",
    disclaimer: "Research demonstrator only.",
  },
};

describe("DisclaimerBanner", () => {
  it("states that the system is not a medical device and uses synthetic data", () => {
    render(<DisclaimerBanner />);
    const note = screen.getByRole("note", { name: /research disclaimer/i });
    expect(note).toHaveTextContent("not a medical device");
    expect(note).toHaveTextContent("synthetic");
    expect(DISCLAIMER_TEXT).toMatch(/not for clinical decisions/);
  });
});

describe("ExplanationPanel", () => {
  it("renders the five separated concepts and the technical list", () => {
    render(<ExplanationPanel narrative={narrative} />);
    for (const t of ["Prediction", "Association", "Uncertainty", "Counterfactual simulation", "Causality"]) {
      expect(screen.getByText(t)).toBeInTheDocument();
    }
    expect(screen.getByText(/not be interpreted as clinical causes/)).toBeInTheDocument();
    expect(screen.getByText(/Calibration caveat/)).toBeInTheDocument();
  });

  it("omits the counterfactual section when no simulation was run", () => {
    render(<ExplanationPanel narrative={{ ...narrative, plain_language: { ...narrative.plain_language, counterfactual: null } }} />);
    expect(screen.queryByText("Counterfactual simulation")).not.toBeInTheDocument();
  });
});

describe("CausalNote", () => {
  it("explains why a counterfactual is not proof of causality", () => {
    render(<CausalNote caveat="Counterfactual scenarios represent model-based simulations and do not establish causation." />);
    expect(screen.getByRole("note")).toHaveTextContent(/not proof of causality/i);
    expect(screen.getByRole("note")).toHaveTextContent(/do not establish/);
  });
});
