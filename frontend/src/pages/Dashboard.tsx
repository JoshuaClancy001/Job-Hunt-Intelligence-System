import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Job, InsightReport } from "../lib/api";
import { ScoreBadge } from "../components/ScoreBadge";

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
      <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{label}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [insights, setInsights] = useState<InsightReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getJobs(), api.getInsights()])
      .then(([j, i]) => { setJobs(j); setInsights(i); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-400 animate-pulse">Loading...</p>;
  if (error) return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      <p className="font-semibold">Cannot connect to backend</p>
      <p className="text-sm mt-1">Start the API server: <code className="bg-red-100 px-1 rounded font-mono">python main.py</code></p>
      <p className="text-xs mt-2 text-red-400">{error}</p>
    </div>
  );

  const ls = (key: string, fallback: unknown) => {
    try { const v = localStorage.getItem(key); return v !== null ? JSON.parse(v) : fallback; } catch { return fallback; }
  };
  const SENIOR_RE = /\b(senior|sr\.?|principal|staff|lead|director|vp|vice\s+president|head\s+of|manager|architect|distinguished|fellow)\b/i;
  const minScore = ls("nj_minscore", 0) as number;
  const locationFilter = ls("nj_location", "remote_utah") as string;
  const hideSenior = ls("nj_hidesenior", true) as boolean;
  const isUtah = (j: Job) => {
    const loc = (j.location || "").toLowerCase();
    return loc.includes("utah") || loc.includes(" ut") || loc.includes(",ut") ||
           loc.includes("provo") || loc.includes("salt lake") || loc.includes("orem");
  };

  const scored = jobs.filter(j => j.fit_score !== null);
  const newJobs = jobs.filter(j => {
    if (j.application_status) return false;
    if ((j.fit_score ?? 0) < minScore) return false;
    if (locationFilter === "remote" && !j.remote) return false;
    if (locationFilter === "remote_utah" && !j.remote && !isUtah(j)) return false;
    if (hideSenior && SENIOR_RE.test(j.title)) return false;
    return true;
  });
  const applied = jobs.filter(j => !!j.application_status);
  const avgScore = scored.length
    ? Math.round(scored.reduce((s, j) => s + (j.fit_score ?? 0), 0) / scored.length)
    : 0;
  const top5 = [...jobs].sort((a, b) => (b.fit_score ?? 0) - (a.fit_score ?? 0)).slice(0, 5);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Dashboard</h2>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Jobs" value={newJobs.length + applied.length} sub={`${newJobs.length} new, ${applied.length} applied`} />
        <StatCard label="Avg Fit Score" value={avgScore || "—"} sub="across scored jobs" />
        <StatCard label="Applied" value={insights?.total_applied ?? 0} sub="applications sent" />
        <StatCard
          label="Response Rate"
          value={insights ? `${insights.response_rate}%` : "—"}
          sub="phone + onsite + offer"
        />
      </div>

      {/* Top jobs */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-sm font-semibold text-gray-700">Top Jobs by Fit Score</h3>
          <Link to="/jobs" className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
            View all →
          </Link>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-xs text-gray-500 border-b border-gray-200">
              <th className="text-left px-5 py-2 font-medium">Title</th>
              <th className="text-left px-5 py-2 font-medium">Company</th>
              <th className="text-right px-5 py-2 font-medium">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {top5.map(job => (
              <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-5 py-2.5 text-gray-800 font-medium">{job.title}</td>
                <td className="px-5 py-2.5 text-gray-500">{job.company}</td>
                <td className="px-5 py-2.5 text-right">
                  <ScoreBadge score={job.fit_score} />
                </td>
              </tr>
            ))}
            {top5.length === 0 && (
              <tr>
                <td colSpan={3} className="px-5 py-6 text-center text-gray-400 text-sm">
                  No jobs yet — run <code className="bg-gray-100 px-1 rounded font-mono text-xs">python cli.py demo</code>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Missing skills callout */}
      {insights && insights.top_missing_skills.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-2">
            Top Missing Skills (from rejected jobs)
          </p>
          <div className="flex flex-wrap gap-2">
            {insights.top_missing_skills.map(s => (
              <span key={s} className="bg-white border border-amber-200 text-amber-700 text-xs px-2 py-1 rounded font-medium">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
