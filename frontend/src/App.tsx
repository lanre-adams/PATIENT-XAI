import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AppProvider } from "./lib/context";
import { About } from "./pages/About";
import { Counterfactual } from "./pages/Counterfactual";
import { Explainability } from "./pages/Explainability";
import { Explorer } from "./pages/Explorer";
import { Overview } from "./pages/Overview";
import { Performance } from "./pages/Performance";
import { Prediction } from "./pages/Prediction";
import { Report } from "./pages/Report";

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="explorer" element={<Explorer />} />
            <Route path="prediction" element={<Prediction />} />
            <Route path="explain" element={<Explainability />} />
            <Route path="counterfactual" element={<Counterfactual />} />
            <Route path="performance" element={<Performance />} />
            <Route path="report" element={<Report />} />
            <Route path="about" element={<About />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
