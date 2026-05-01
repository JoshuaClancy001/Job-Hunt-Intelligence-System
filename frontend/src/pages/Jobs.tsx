import { useEffect, useState } from "react";
import { api, Job, GeneratedContent } from "../lib/api";
import { ScoreBadge } from "../components/ScoreBadge";

function fmtSalary(min: number, max: number): string {
  if (!min && !max) return "—";
  if (min === max || !max) return `$${Math.round(min / 1000)}k`;
  return `$${Math.round(min / 1000)}k–$${Math.round(max / 1000)}k`;
}

export function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Job | null>(null);
  const [minScore, setMinScore] = useState(0);
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<GeneratedContent | null>(null);
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [scraping, setScraping] = useState(false);
  const [trackStatus, setTrackStatus] = useState("applied");

  const load = () => api.getJobs().then(setJobs).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const filtered = jobs.filter(j =>
    (j.fit_score ?? 0) >= minScore && (!remoteOnly || j.remote)
  );

  const handleScrape = async () => {
    if (!scrapeUrl.trim()) return;
    setScraping(true);
    try {
      await api.scrapeJob(scrapeUrl);
      setScrapeUrl("");
      load();
    } catch (e) {
      alert("Scrape failed: " + (e as Error).message);
    } finally {
      setScraping(false);
    }
  };

  const handleGenerate = async (job: Job) => {
    setGenerating(true);
    setGenerated(null);
    try {
      const result = await api.generateContent(job.id, "both");
      setGenerated(result);
    } finally {
      setGenerating(false);
    }
  };

  const handleTrack = async (job: Job) => {
    try {
      await api.createApplication(job.id, trackStatus, "");
      alert(`Tracked as "${trackStatus}"`);
    } catch {
      alert("Already tracked or error — use the Applications page to update.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">
          Jobs <span className="text-gray-400 text-base font-normal">({filtered.length})</span>
        </h2>
      </div>

      {/* Scrape bar */}
      <div className="flex gap-2">
        <input
          className="flex-1 bg-white border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400"
          placeholder="Paste a job posting URL to scrape..."
          value={scrapeUrl}
          onChange={e => setScrapeUrl(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleScrape()}
        />
        <button
          onClick={handleScrape}
          disabled={scraping || !scrapeUrl.trim()}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-md transition-colors font-medium"
        >
          {scraping ? "Scraping…" : "Scrape"}
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-6 text-sm bg-white border border-gray-200 rounded-md px-4 py-2.5 shadow-sm">
        <label className="flex items-center gap-2 text-gray-600">
          Min score:
          <span className="text-indigo-600 font-semibold w-6">{minScore}</span>
          <input type="range" min={0} max={100} step={10} value={minScore}
            onChange={e => setMinScore(+e.target.value)}
            className="w-28 accent-indigo-600" />
        </label>
        <label className="flex items-center gap-2 text-gray-600 cursor-pointer select-none">
          <input type="checkbox" checked={remoteOnly} onChange={e => setRemoteOnly(e.target.checked)}
            className="accent-indigo-600" />
          Remote only
        </label>
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-gray-400 animate-pulse">Loading...</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
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
              {filtered.map(job => (
                <tr
                  key={job.id}
                  onClick={() => { setSelected(job); setGenerated(null); }}
                  className={`cursor-pointer transition-colors ${
                    selected?.id === job.id ? "bg-indigo-50" : "hover:bg-gray-50"
                  }`}
                >
                  <td className="px-4 py-2.5 text-gray-800 font-medium">{job.title}</td>
                  <td className="px-4 py-2.5 text-gray-500">{job.company}</td>
                  <td className="px-4 py-2.5 text-gray-400 hidden md:table-cell">{job.location || "—"}</td>
                  <td className="px-4 py-2.5 text-center text-sm">
                    {job.remote
                      ? <span className="text-green-600 font-medium">✓</span>
                      : <span className="text-gray-300">✗</span>}
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-400 hidden lg:table-cell">
                    {fmtSalary(job.salary_min, job.salary_max)}
                  </td>
                  <td className="px-4 py-2.5 text-right"><ScoreBadge score={job.fit_score} /></td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                    No jobs match your filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail drawer */}
      {selected && (
        <div className="fixed inset-y-0 right-0 w-[480px] bg-white border-l border-gray-200 shadow-xl overflow-y-auto z-50">
          <div className="p-5 space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selected.title}</h3>
                <p className="text-gray-500 text-sm">{selected.company} · {selected.location || "Unknown location"}</p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none p-1"
              >×</button>
            </div>

            <div className="flex gap-2 flex-wrap items-center">
              <ScoreBadge score={selected.fit_score} />
              {selected.remote && (
                <span className="bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded ring-1 ring-indigo-200 font-medium">
                  Remote
                </span>
              )}
              <span className="text-gray-500 text-sm">{fmtSalary(selected.salary_min, selected.salary_max)}</span>
              <span className="text-gray-400 text-sm">{selected.experience_years}+ yrs</span>
            </div>

            {/* Fit breakdown */}
            {selected.fit_breakdown && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2.5">
                <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Fit Breakdown</p>
                {[
                  ["Skill Match",  selected.fit_breakdown.skill_match,       40],
                  ["Experience",   selected.fit_breakdown.experience_match,  30],
                  ["Role Match",   selected.fit_breakdown.role_match,        20],
                  ["Salary",       selected.fit_breakdown.salary_match,      10],
                ].map(([label, val, max]) => (
                  <div key={label as string}>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>{label}</span>
                      <span className="font-medium text-gray-700">{val}/{max}</span>
                    </div>
                    <div className="bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-indigo-500 h-1.5 rounded-full transition-all"
                        style={{ width: `${((val as number) / (max as number)) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
                {selected.fit_breakdown.notes && (
                  <p className="text-xs text-gray-500 pt-1 border-t border-gray-200">
                    {selected.fit_breakdown.notes}
                  </p>
                )}
              </div>
            )}

            {/* Skills */}
            {selected.skills.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">Required Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {selected.skills.map(s => {
                    const matched = selected.fit_breakdown?.matched_skills.includes(s);
                    return (
                      <span key={s} className={`text-xs px-2 py-0.5 rounded font-medium ${
                        matched
                          ? "bg-green-50 text-green-700 ring-1 ring-green-200"
                          : "bg-gray-100 text-gray-500"
                      }`}>{s}</span>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 flex-wrap pt-1">
              <select
                value={trackStatus}
                onChange={e => setTrackStatus(e.target.value)}
                className="bg-white border border-gray-300 rounded text-sm text-gray-700 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              >
                {["saved","applied","phone","onsite","offer","rejected"].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <button
                onClick={() => handleTrack(selected)}
                className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm px-3 py-1.5 rounded transition-colors font-medium"
              >
                Track
              </button>
              <button
                onClick={() => handleGenerate(selected)}
                disabled={generating}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-3 py-1.5 rounded transition-colors font-medium"
              >
                {generating ? "Generating…" : "Generate Content"}
              </button>
            </div>

            {selected.url && selected.url !== "https://example.com/jobs/1" && (
              <a
                href={selected.url}
                target="_blank"
                rel="noreferrer"
                className="text-indigo-600 hover:text-indigo-800 text-sm font-medium block"
              >
                View job posting ↗
              </a>
            )}

            {/* Generated content */}
            {generated && (
              <div className="space-y-3 pt-1 border-t border-gray-200">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Generated Content</p>
                  <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                    via {generated.source}
                  </span>
                </div>
                {generated.cover_letter && (
                  <div>
                    <p className="text-xs text-gray-500 font-medium mb-1">Cover Letter</p>
                    <div className="bg-gray-50 border border-gray-200 rounded p-3 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                      {generated.cover_letter}
                    </div>
                  </div>
                )}
                {generated.resume_bullets.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-500 font-medium mb-1">Resume Bullets</p>
                    <ul className="space-y-1">
                      {generated.resume_bullets.map((b, i) => (
                        <li key={i} className="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded px-3 py-2">
                          • {b}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      {selected && (
        <div className="fixed inset-0 bg-black/20 z-40" onClick={() => setSelected(null)} />
      )}
    </div>
  );
}
