import { useEffect, useState } from "react";
import { api, Job } from "../lib/api";
import { ScoreBadge } from "../components/ScoreBadge";
import { JobDrawer } from "../components/JobDrawer";

function fmtSalary(min: number, max: number): string {
  if (!min && !max) return "—";
  if (min === max || !max) return `$${Math.round(min / 1000)}k`;
  return `$${Math.round(min / 1000)}k–$${Math.round(max / 1000)}k`;
}

export function SavedJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Job | null>(null);
  const [remoteOnly, setRemoteOnly] = useState(false);

  const load = () => api.getJobs().then(setJobs).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const saved = jobs.filter(j =>
    j.application_status === "saved" && (!remoteOnly || j.remote)
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-xl font-semibold text-gray-900">
          Saved Jobs <span className="text-gray-400 text-base font-normal">({saved.length})</span>
        </h2>
        <p className="text-sm text-gray-400">Priority queue — jobs you want to apply to next</p>
      </div>

      <div className="flex items-center gap-6 text-sm bg-white border border-gray-200 rounded-md px-4 py-2.5 shadow-sm">
        <label className="flex items-center gap-2 text-gray-600 cursor-pointer select-none">
          <input type="checkbox" checked={remoteOnly} onChange={e => setRemoteOnly(e.target.checked)}
            className="accent-indigo-600" />
          Remote only
        </label>
      </div>

      {loading ? (
        <p className="text-gray-400 animate-pulse">Loading...</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          {saved.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <p className="text-lg font-medium text-gray-500">No saved jobs yet</p>
              <p className="text-sm mt-1">Go to <strong>New Jobs</strong>, open a job, and track it as <strong>saved</strong></p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs text-gray-500 border-b border-gray-200">
                  <th className="text-left px-4 py-2.5 font-medium">Title</th>
                  <th className="text-left px-4 py-2.5 font-medium">Company</th>
                  <th className="text-left px-4 py-2.5 font-medium hidden md:table-cell">Location</th>
                  <th className="text-center px-4 py-2.5 font-medium">Remote</th>
                  <th className="text-right px-4 py-2.5 font-medium hidden lg:table-cell">Salary</th>
                  <th className="text-right px-4 py-2.5 font-medium">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {saved.map(job => (
                  <tr
                    key={job.id}
                    onClick={() => setSelected(job)}
                    className={`cursor-pointer transition-colors ${
                      selected?.id === job.id ? "bg-indigo-50" : "hover:bg-gray-50"
                    }`}
                  >
                    <td className="px-4 py-2.5 text-gray-800 font-medium">{job.title}</td>
                    <td className="px-4 py-2.5 text-gray-500">{job.company}</td>
                    <td className="px-4 py-2.5 text-gray-400 hidden md:table-cell">{job.location || "—"}</td>
                    <td className="px-4 py-2.5 text-center text-sm">
                      {job.remote ? <span className="text-green-600 font-medium">✓</span> : <span className="text-gray-300">✗</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-400 hidden lg:table-cell">
                      {fmtSalary(job.salary_min, job.salary_max)}
                    </td>
                    <td className="px-4 py-2.5 text-right"><ScoreBadge score={job.fit_score} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {selected && (
        <JobDrawer
          job={selected}
          onClose={() => setSelected(null)}
          onRefresh={() => { load(); setSelected(null); }}
        />
      )}
    </div>
  );
}
