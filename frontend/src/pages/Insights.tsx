import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, CartesianGrid,
} from "recharts";
import { api, InsightReport, Job } from "../lib/api";

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

const FUNNEL_COLORS: Record<string, string> = {
  Saved:         "#e5e7eb",
  Applied:       "#6366f1",
  "Phone Screen":"#06b6d4",
  Onsite:        "#f59e0b",
  Offer:         "#22c55e",
  Rejected:      "#f87171",
};

const TOOLTIP_STYLE = {
  contentStyle: {
    background: "#ffffff",
    border: "1px solid #e5e7eb",
    borderRadius: 6,
    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
  },
  labelStyle: { color: "#374151", fontWeight: 600 },
  itemStyle:  { color: "#6b7280" },
};

export function Insights() {
  const [report, setReport] = useState<InsightReport | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getInsights(), api.getJobs()])
      .then(([r, j]) => { setReport(r); setJobs(j); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-400 animate-pulse">Loading...</p>;
  if (error || !report) return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
      <p className="font-semibold">Cannot load insights — is the backend running?</p>
      <p className="text-xs mt-1">{error}</p>
    </div>
  );

  const funnelData = [
    { name: "Saved",        value: report.total_saved },
    { name: "Applied",      value: report.total_applied },
    { name: "Phone Screen", value: report.phone_screens },
    { name: "Onsite",       value: report.onsites },
    { name: "Offer",        value: report.offers },
    { name: "Rejected",     value: report.rejections },
  ];

  const bins = [
    { range: "0–20",   count: 0 },
    { range: "20–40",  count: 0 },
    { range: "40–60",  count: 0 },
    { range: "60–80",  count: 0 },
    { range: "80–100", count: 0 },
  ];
  jobs.forEach(j => {
    if (j.fit_score === null) return;
    bins[Math.min(Math.floor(j.fit_score / 20), 4)].count++;
  });

  const missingSkillsData = report.top_missing_skills.map((s, i) => ({
    skill: s,
    count: report.top_missing_skills.length - i,
  }));

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Insights</h2>

      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Response Rate"
          value={`${report.response_rate}%`}
          sub="phone + onsite + offer / applied"
        />
        <MetricCard
          label="Avg Score (Responded)"
          value={report.avg_fit_responded || "—"}
          sub="jobs that got responses"
        />
        <MetricCard
          label="Avg Score (No Response)"
          value={report.avg_fit_no_response || "—"}
          sub="ghosted applications"
        />
        <MetricCard
          label="Avg Days in Pipeline"
          value={report.days_in_pipeline || "—"}
          sub="applied → terminal status"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Funnel chart */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Application Funnel</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={funnelData} layout="vertical" margin={{ left: 16, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} width={90} axisLine={false} tickLine={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {funnelData.map(entry => (
                  <Cell key={entry.name} fill={FUNNEL_COLORS[entry.name] || "#e5e7eb"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Score histogram */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Fit Score Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={bins} margin={{ left: 0, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="range" tick={{ fill: "#9ca3af", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Missing skills */}
      {missingSkillsData.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Top Missing Skills (Rejected Jobs)</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={missingSkillsData} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <YAxis type="category" dataKey="skill" tick={{ fill: "#6b7280", fontSize: 11 }} width={110} axisLine={false} tickLine={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {missingSkillsData.length === 0 && report.rejections === 0 && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 text-center text-gray-400">
          <p>No rejection data yet — track applications to unlock insights.</p>
        </div>
      )}
    </div>
  );
}
