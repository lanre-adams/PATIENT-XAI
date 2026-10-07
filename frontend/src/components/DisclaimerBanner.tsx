export const DISCLAIMER_TEXT =
  "Research demonstrator only — not a medical device, not clinically validated, not for clinical decisions. All patients are synthetic.";

export function DisclaimerBanner({ compact = false }: { compact?: boolean }) {
  return (
    <div role="note" aria-label="Research disclaimer" className={`disclaimer${compact ? " compact" : ""}`}>
      <span className="disclaimer-tag">RESEARCH DEMONSTRATOR</span>
      <span>{DISCLAIMER_TEXT}</span>
    </div>
  );
}
