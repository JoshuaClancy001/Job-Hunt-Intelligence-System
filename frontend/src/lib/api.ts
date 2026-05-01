const BASE = "/api";

export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  url: string;
  remote: boolean;
  experience_years: number | null;
  salary_min: number;
  salary_max: number;
  skills: string[];
  fit_score: number | null;
  fit_breakdown: FitBreakdown | null;
  scraped_at: string;
  parsed_at: string | null;
}

export interface FitBreakdown {
  skill_match: number;
  experience_match: number;
  role_match: number;
  salary_match: number;
  total: number;
  matched_skills: string[];
  missing_skills: string[];
  notes: string;
}

export interface Application {
  id: number;
  job_id: number;
  status: string;
  applied_at: string | null;
  notes: string;
  cover_letter: string;
  resume_bullets: string[];
  updated_at: string;
  rejection_reason: string;
  title?: string;
  company?: string;
  fit_score?: number | null;
  salary_min?: number;
  salary_max?: number;
  url?: string;
}

export interface InsightReport {
  total_applied: number;
  total_saved: number;
  phone_screens: number;
  onsites: number;
  offers: number;
  rejections: number;
  response_rate: number;
  avg_fit_responded: number;
  avg_fit_no_response: number;
  top_missing_skills: string[];
  days_in_pipeline: number;
}

export interface GeneratedContent {
  cover_letter: string;
  resume_bullets: string[];
  source: string;
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  getJobs: () => req<Job[]>("/jobs"),
  deleteJob: (id: number) => req<{ deleted: number }>(`/jobs/${id}`, { method: "DELETE" }),
  updateJob: (id: number, data: Partial<Job>) =>
    req<Job>(`/jobs/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  addJobManually: (data: { title: string; company: string; description: string; location?: string; url?: string }) =>
    req<Job>("/jobs/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getJob: (id: number) => req<Job>(`/jobs/${id}`),
  scrapeJob: (url: string) =>
    req<Job>("/jobs/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    }),
  scoreJob: (id: number) => req<{ fit_score: number; breakdown: FitBreakdown }>(`/jobs/${id}/score`, { method: "POST" }),
  generateContent: (id: number, content_type: string) =>
    req<GeneratedContent>(`/jobs/${id}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content_type }),
    }),

  getApplications: () => req<Application[]>("/applications"),
  createApplication: (job_id: number, status = "saved", notes = "") =>
    req<Application>("/applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id, status, notes }),
    }),
  updateApplication: (id: number, status: string, notes: string, rejection_reason = "") =>
    req<Application>(`/applications/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, notes, rejection_reason }),
    }),
  getApplicationHistory: (id: number) =>
    req<{ status: string; changed_at: string }[]>(`/applications/${id}/history`),

  getInsights: () => req<InsightReport>("/insights"),
  getProfile: () => req<Record<string, unknown>>("/profile"),
  reloadProfileFromFile: () => req<Record<string, unknown>>("/profile/reload", { method: "POST" }),
  updateProfile: (data: Record<string, unknown>) =>
    req<Record<string, unknown>>("/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
};
