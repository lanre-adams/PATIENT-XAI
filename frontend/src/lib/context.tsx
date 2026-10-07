import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Meta, type ModelKey } from "./api";

interface Ctx {
  meta: Meta | null; error: string | null;
  patientId: string; setPatientId: (id: string) => void;
  model: ModelKey; setModel: (m: ModelKey) => void;
  changes: Record<string, number>; setChanges: (c: Record<string, number>) => void;
}
const AppCtx = createContext<Ctx | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [patientId, setPatientIdRaw] = useState<string>("");
  const [model, setModel] = useState<ModelKey>("gru");
  const [changes, setChanges] = useState<Record<string, number>>({});
  const setPatientId = (id: string) => { setPatientIdRaw(id); setChanges({}); };

  useEffect(() => {
    api.meta().then(setMeta).catch((e) => setError(String(e)));
    api.patients("test", undefined, 1).then((r) => r.items[0] && setPatientIdRaw((p) => p || r.items[0].patient_id))
      .catch(() => undefined);
  }, []);
  return (
    <AppCtx.Provider value={{ meta, error, patientId, setPatientId, model, setModel, changes, setChanges }}>
      {children}
    </AppCtx.Provider>
  );
}

export function useApp(): Ctx {
  const c = useContext(AppCtx);
  if (!c) throw new Error("useApp outside AppProvider");
  return c;
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let live = true;
    setLoading(true); setError(null);
    fn().then((d) => live && setData(d)).catch((e) => live && setError(String(e))).finally(() => live && setLoading(false));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, error, loading };
}
