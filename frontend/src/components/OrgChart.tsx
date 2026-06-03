import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphOut } from "../types";

function nodeColor(score: number | null): string {
  if (score == null) return "#cfcfe0";
  if (score >= 70) return "#1d7a3a";
  if (score >= 45) return "#c47f17";
  return "#b42318";
}

/** Assign a vertical level to each person from the reports_to hierarchy. */
function computeLevels(graph: GraphOut): Record<string, number> {
  const bossOf: Record<string, string> = {};
  for (const e of graph.edges) {
    if (e.type === "reports_to") bossOf[e.source_person_id] = e.target_person_id;
  }
  const level: Record<string, number> = {};
  const depth = (id: string, seen: Set<string>): number => {
    if (level[id] !== undefined) return level[id];
    if (seen.has(id)) return 0; // cycle guard
    seen.add(id);
    const boss = bossOf[id];
    const d = boss ? depth(boss, seen) + 1 : 0;
    level[id] = d;
    return d;
  };
  for (const n of graph.nodes) depth(n.id, new Set());
  return level;
}

export default function OrgChart({ graph }: { graph: GraphOut }) {
  const { nodes, edges } = useMemo(() => {
    const level = computeLevels(graph);
    const perLevel: Record<number, number> = {};

    const nodes: Node[] = graph.nodes.map((p) => {
      const lvl = level[p.id] ?? 0;
      const col = perLevel[lvl] ?? 0;
      perLevel[lvl] = col + 1;
      return {
        id: p.id,
        position: { x: col * 220 + 40, y: lvl * 140 + 40 },
        data: {
          label: (
            <div style={{ textAlign: "center", padding: 4 }}>
              <strong>{p.full_name}</strong>
              <div style={{ fontSize: 11 }}>{p.current_title ?? ""}</div>
              <div style={{ fontSize: 10, opacity: 0.8 }}>
                {p.department ?? ""} · Score {p.score ?? "—"}
              </div>
            </div>
          ),
        },
        style: {
          border: `2px solid ${nodeColor(p.score)}`,
          borderRadius: 8,
          background: "#fff",
          width: 190,
          fontSize: 12,
        },
      };
    });

    const edges: Edge[] = graph.edges.map((e, i) => {
      const isHierarchy = e.type === "reports_to";
      return {
        id: `e${i}`,
        source: e.source_person_id,
        target: e.target_person_id,
        label: e.type,
        animated: e.type === "co_mentioned",
        style: {
          stroke: isHierarchy ? "#4b3fff" : "#9aa0b5",
          strokeDasharray: isHierarchy ? undefined : "5 4",
          opacity: 0.4 + e.confidence * 0.6,
        },
        labelStyle: { fontSize: 9, fill: "#666" },
        markerEnd: isHierarchy
          ? { type: MarkerType.ArrowClosed, color: "#4b3fff" }
          : undefined,
      };
    });

    return { nodes, edges };
  }, [graph]);

  return (
    <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.2}>
      <Background />
      <Controls />
    </ReactFlow>
  );
}
