import { NavLink, Outlet } from "react-router-dom";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { ModelToggle, PatientPicker } from "./PatientPicker";
import { useApp } from "../lib/context";

const NAV = [
  ["/", "Research overview"], ["/explorer", "Patient explorer"], ["/prediction", "Risk prediction"],
  ["/explain", "Explainability"], ["/counterfactual", "Counterfactual explorer"],
  ["/performance", "Model performance"], ["/report", "Trustworthy AI report"], ["/about", "About the research"],
] as const;

export function Layout() {
  const { meta, error } = useApp();
  return (
    <div className="shell">
      <header className="masthead">
        <div className="brand">
          <span className="brand-mark" aria-hidden>Px</span>
          <div>
            <div className="brand-name">PATIENT-XAI</div>
            <div className="brand-sub">Personalised AI for Longitudinal Health Trajectories, Explainability &amp; Counterfactual Prevention</div>
          </div>
        </div>
        <div className="brand-meta small muted">
          {meta ? <>Model {meta.model_version} · {meta.dataset_type.split(" (")[0]} data</> : error ? "API unavailable" : "Connecting…"}
        </div>
      </header>
      <DisclaimerBanner />
      <div className="body">
        <nav className="sidenav" aria-label="Sections">
          {NAV.map(([to, label], i) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
              <span className="nav-num">{i + 1}</span>{label}
            </NavLink>
          ))}
        </nav>
        <main>
          <div className="toolbar"><PatientPicker /><ModelToggle /></div>
          {error && <div className="error" role="alert">Cannot reach the API ({error}). Is the backend running on port 8000?</div>}
          <Outlet />
        </main>
      </div>
      <footer className="footer small muted">
        Pre-application research demonstrator · synthetic data only · MIT licence · not a medical device
      </footer>
    </div>
  );
}
