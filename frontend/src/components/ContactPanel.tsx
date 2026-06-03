import type { GraphOut, PersonOut } from "../types";

function scoreColor(score: number | null): string {
  if (score == null) return "#999";
  if (score >= 70) return "#1d7a3a";
  if (score >= 45) return "#c47f17";
  return "#b42318";
}

function toCsv(graph: GraphOut): string {
  const header = ["name", "title", "department", "seniority", "score", "source", "rationale"];
  const rows = [...graph.nodes]
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .map((n) =>
      [
        n.full_name,
        n.current_title ?? "",
        n.department ?? "",
        n.seniority ?? "",
        n.score ?? "",
        n.source_mode,
        (n.rationale ?? "").replace(/"/g, "'"),
      ]
        .map((v) => `"${v}"`)
        .join(","),
    );
  return [header.join(","), ...rows].join("\n");
}

export default function ContactPanel({ graph }: { graph: GraphOut }) {
  const ranked: PersonOut[] = [...graph.nodes].sort(
    (a, b) => (b.score ?? 0) - (a.score ?? 0),
  );

  const exportCsv = () => {
    const blob = new Blob([toCsv(graph)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${graph.company_name}-contacts.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <h3 style={{ marginTop: 0 }}>{graph.company_name}</h3>
      <div className="hint">
        {graph.nodes.length} Kontakte · {graph.edges.length} Beziehungen
      </div>
      <button onClick={exportCsv}>CSV exportieren</button>

      <div style={{ marginTop: 16 }}>
        {ranked.map((p) => (
          <div className="contact" key={p.id}>
            <span
              className="score"
              style={{ background: scoreColor(p.score) }}
            >
              {p.score ?? "—"}
            </span>
            <div className="name">
              {p.full_name}
              {p.is_seed && <span className="badge seed">seed</span>}
              <span className={`badge ${p.source_mode}`}>{p.source_mode}</span>
            </div>
            <div className="meta">
              {p.current_title ?? "?"} · {p.department ?? "?"}
            </div>
            {p.rationale && <div className="meta">{p.rationale}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
