export function Loading({ what = "Loading" }: { what?: string }) {
  return <p className="muted" aria-live="polite">{what}…</p>;
}
export function ErrorBox({ error }: { error: string }) {
  return <div className="error" role="alert">Could not load: {error}</div>;
}
export function NeedPatient() {
  return <p className="muted">Select a synthetic patient in the toolbar above.</p>;
}
