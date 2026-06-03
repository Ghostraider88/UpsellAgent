import { useCallback, useRef, useState } from "react";
import Wizard from "./components/Wizard";
import OrgChart from "./components/OrgChart";
import ContactPanel from "./components/ContactPanel";
import { analyze, getGraph, getJob } from "./api";
import type { GraphOut, ICPDefinition, SeedContact } from "./types";

type View = "input" | "result";

export default function App() {
  const [view, setView] = useState<View>("input");
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [graph, setGraph] = useState<GraphOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const run = useCallback(
    async (payload: {
      company_name: string;
      seed_contacts: SeedContact[];
      icp: ICPDefinition;
      allow_shadow: boolean;
    }) => {
      setError(null);
      setRunning(true);
      setProgress(5);
      try {
        const job = await analyze(payload);
        // Poll job status until done/failed.
        await new Promise<void>((resolve, reject) => {
          pollRef.current = window.setInterval(async () => {
            try {
              const j = await getJob(job.id);
              setProgress(j.progress);
              if (j.status === "done" && j.company_id) {
                clearInterval(pollRef.current!);
                const g = await getGraph(j.company_id);
                setGraph(g);
                setView("result");
                resolve();
              } else if (j.status === "failed") {
                clearInterval(pollRef.current!);
                reject(new Error(j.error ?? "Job failed"));
              }
            } catch (e) {
              clearInterval(pollRef.current!);
              reject(e);
            }
          }, 800);
        });
      } catch (e) {
        setError(String(e));
      } finally {
        setRunning(false);
      }
    },
    [],
  );

  return (
    <div className="app">
      <div className="topbar">
        <h1>UpsellAgent</h1>
        <span className="sub">Org-Intelligence &amp; ICP-Matching für Sales</span>
        {view === "result" && (
          <button
            style={{ marginTop: 0, marginLeft: "auto", padding: "6px 12px" }}
            onClick={() => setView("input")}
          >
            Neue Analyse
          </button>
        )}
      </div>

      <div className="layout">
        <div className="panel">
          {view === "input" ? (
            <Wizard onSubmit={run} running={running} progress={progress} />
          ) : (
            graph && <ContactPanel graph={graph} />
          )}
          {error && <div style={{ color: "#b42318", marginTop: 12 }}>{error}</div>}
        </div>
        <div className="graph">
          {graph ? (
            <OrgChart graph={graph} />
          ) : (
            <div style={{ padding: 40, color: "#999" }}>
              Starte eine Analyse, um das Organigramm zu sehen.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
