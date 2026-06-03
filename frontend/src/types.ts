export interface SeedContact {
  full_name: string;
  title?: string;
}

export interface ICPDefinition {
  name: string;
  roles: string[];
  functions: string[];
  seniority: string[];
  keywords: string[];
}

export interface JobResponse {
  id: string;
  status: "pending" | "running" | "done" | "failed";
  progress: number;
  company_id?: string | null;
  error?: string | null;
}

export interface PersonOut {
  id: string;
  full_name: string;
  current_title: string | null;
  seniority: string | null;
  department: string | null;
  location: string | null;
  is_seed: boolean;
  score: number | null;
  rationale: string | null;
  matched_signals: string[];
  source_mode: string;
}

export interface EdgeOut {
  source_person_id: string;
  target_person_id: string;
  type: string;
  confidence: number;
  evidence_ref: string | null;
}

export interface GraphOut {
  company_id: string;
  company_name: string;
  nodes: PersonOut[];
  edges: EdgeOut[];
}
