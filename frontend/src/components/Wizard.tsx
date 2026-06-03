import { useState } from "react";
import type { ICPDefinition, SeedContact } from "../types";

interface Props {
  onSubmit: (payload: {
    company_name: string;
    seed_contacts: SeedContact[];
    icp: ICPDefinition;
    allow_shadow: boolean;
  }) => void;
  running: boolean;
  progress: number;
}

const splitList = (s: string): string[] =>
  s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

export default function Wizard({ onSubmit, running, progress }: Props) {
  const [company, setCompany] = useState("ACME No-Code GmbH");
  const [seeds, setSeeds] = useState("Anna Schmidt");
  const [roles, setRoles] = useState("Head of Operations, COO");
  const [seniority, setSeniority] = useState("C-Level, Head");
  const [keywords, setKeywords] = useState("operations, automation");
  const [allowShadow, setAllowShadow] = useState(false);

  const submit = () => {
    onSubmit({
      company_name: company,
      seed_contacts: splitList(seeds).map((full_name) => ({ full_name })),
      icp: {
        name: "ICP",
        roles: splitList(roles),
        functions: [],
        seniority: splitList(seniority),
        keywords: splitList(keywords),
      },
      allow_shadow: allowShadow,
    });
  };

  return (
    <div>
      <label>Unternehmen (Bestandskunde)</label>
      <input value={company} onChange={(e) => setCompany(e.target.value)} />

      <label>Bekannte Ansprechpartner (Komma-getrennt)</label>
      <input value={seeds} onChange={(e) => setSeeds(e.target.value)} />

      <label>ICP — relevante Rollen</label>
      <input value={roles} onChange={(e) => setRoles(e.target.value)} />

      <label>ICP — Seniorität</label>
      <input value={seniority} onChange={(e) => setSeniority(e.target.value)} />

      <label>ICP — Keywords</label>
      <input value={keywords} onChange={(e) => setKeywords(e.target.value)} />

      <div className="shadow-row">
        <input
          id="shadow"
          type="checkbox"
          checked={allowShadow}
          onChange={(e) => setAllowShadow(e.target.checked)}
        />
        <label htmlFor="shadow" style={{ margin: 0 }}>
          Shadow-Quellen erlauben (nur falls serverseitig aktiviert)
        </label>
      </div>
      <div className="hint">
        Standardmäßig werden ausschließlich compliant Quellen genutzt.
      </div>

      <button onClick={submit} disabled={running}>
        {running ? "Analysiere…" : "Analyse starten"}
      </button>

      {running && (
        <div className="progress">
          <div style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
}
