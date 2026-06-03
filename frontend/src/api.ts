import type { GraphOut, ICPDefinition, JobResponse, SeedContact } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function json<T>(resp: Response): Promise<T> {
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return resp.json() as Promise<T>;
}

export async function analyze(payload: {
  company_name: string;
  seed_contacts: SeedContact[];
  icp: ICPDefinition;
  allow_shadow: boolean;
}): Promise<JobResponse> {
  return json(
    await fetch(`${BASE}/companies/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function getJob(id: string): Promise<JobResponse> {
  return json(await fetch(`${BASE}/jobs/${id}`));
}

export async function getGraph(companyId: string): Promise<GraphOut> {
  return json(await fetch(`${BASE}/companies/${companyId}/graph`));
}
