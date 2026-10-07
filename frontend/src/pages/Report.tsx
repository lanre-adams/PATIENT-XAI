import { useState } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/context";
import { NeedPatient } from "../components/Status";

const FIELDS = ["Patient/sample identifier", "Model", "Prediction", "Uncertainty", "Important features",
  "Counterfactual result", "Known limitations", "Dataset type", "Model version", "Timestamp"];

export function Report() {
  const { patientId, model, changes } = useApp();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  if (!patientId) return <NeedPatient />;

  const download = async (fmt: "html" | "pdf") => {
    setBusy(fmt); setErr(null);
    try {
      const blob = await api.report(patientId, model, fmt, changes);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `patient-xai-report-${patientId}.${fmt}`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setErr(String(e)); } finally { setBusy(null); }
  };
  const showPreview = async () => {
    setBusy("preview");
    try { setPreview(await (await api.report(patientId, model, "html", changes)).text()); }
    catch (e) { setErr(String(e)); } finally { setBusy(null); }
  };
  return (
    <>
      <h1>Trustworthy AI report <span className="pid">{patientId}</span></h1>
      <section className="card">
        <p>Generates a structured record of the current prediction for <strong>{patientId}</strong> using the
          <strong> {model === "gru" ? "GRU ensemble" : "logistic baseline"}</strong>
          {Object.keys(changes).length ? <> and the counterfactual changes set in the explorer ({Object.keys(changes).join(", ")})</> : <> (no counterfactual set)</>}.</p>
        <p className="small muted">Contains: {FIELDS.join(" · ")}.</p>
        <div className="row-gap">
          <button className="primary" disabled={!!busy} onClick={() => download("html")}>{busy === "html" ? "Building…" : "Export HTML"}</button>
          <button className="primary" disabled={!!busy} onClick={() => download("pdf")}>{busy === "pdf" ? "Building…" : "Export PDF"}</button>
          <button disabled={!!busy} onClick={showPreview}>{busy === "preview" ? "Loading…" : "Preview here"}</button>
        </div>
        {err && <div className="error" role="alert">{err}</div>}
      </section>
      {preview && <iframe title="Report preview" className="report-frame" srcDoc={preview} sandbox="" />}
    </>
  );
}
