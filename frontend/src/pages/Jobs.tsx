import { useEffect, useState } from "react";
import { api, Job } from "../lib/api";
import { ScoreBadge } from "../components/ScoreBadge";
import { JobDrawer } from "../components/JobDrawer";

function fmtSalary(min: number, max: number): string {
  if (!min && !max) return "—";
  if (min === max || !max) return `$${Math.round(min / 1000)}k`;
  return `$${Math.round(min / 1000)}k–$${Math.round(max / 1000)}k`;
}

// ---------------------------------------------------------------------------
// Add Job Modal
// ---------------------------------------------------------------------------

function AddJobModal({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const [tab, setTab] = useState<"url" | "manual">("url");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [scrapeUrl, setScrapeUrl] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [description, setDescription] = useState("");

  const handleScrape = async () => {
    if (!scrapeUrl.trim()) return;
    setError("");
    setLoading(true);
    try {
      await api.scrapeJob(scrapeUrl.trim());
      onAdded();
      onClose();
    } catch (e) {
      const msg = (e as Error).message;
      // 422 = filtered out by profile rules — show as amber warning, not red error
      setError(msg.includes("422") ? "Filtered: " + msg.split("422:")[1]?.trim() : "Scrape failed: " + msg);
    } finally {
      setLoading(false);
    }
  };

  const handleManual = async () => {
    if (!title.trim() || !company.trim() || !description.trim()) {
      setError("Title, company, and description are required.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await api.addJobManually({ title, company, location, url: jobUrl, description });
      onAdded();
      onClose();
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg.includes("422") ? "Filtered: " + msg.split("422:")[1]?.trim() : "Failed to add job: " + msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg border border-gray-200">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">Add Job</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        <div className="flex border-b border-gray-200">
          {(["url", "manual"] as const).map(t => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(""); }}
              className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                tab === t
                  ? "text-indigo-700 border-b-2 border-indigo-600"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "url" ? "Scrape URL" : "Paste Description"}
            </button>
          ))}
        </div>

        <div className="p-5 space-y-4">
          {tab === "url" ? (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Job Posting URL</label>
                <input
                  autoFocus
                  className="w-full bg-white border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400"
                  placeholder="https://jobs.lever.co/company/..."
                  value={scrapeUrl}
                  onChange={e => setScrapeUrl(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleScrape()}
                />
              </div>
              <p className="text-xs text-gray-400">
                Works best with Greenhouse, Lever, and Ashby job postings.
              </p>
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Job Title <span className="text-red-400">*</span></label>
                  <input
                    autoFocus
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                    placeholder="Senior Engineer"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Company <span className="text-red-400">*</span></label>
                  <input
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                    placeholder="Acme Corp"
                    value={company}
                    onChange={e => setCompany(e.target.value)}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Location</label>
                  <input
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                    placeholder="Remote or New York"
                    value={location}
                    onChange={e => setLocation(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">URL (optional)</label>
                  <input
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                    placeholder="https://..."
                    value={jobUrl}
                    onChange={e => setJobUrl(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Job Description <span className="text-red-400">*</span>
                  <span className="text-gray-400 font-normal ml-1">— paste the full posting text</span>
                </label>
                <textarea
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none font-mono"
                  rows={8}
                  placeholder="Paste the full job description here..."
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                />
              </div>
            </>
          )}

          {error && (
            <p className={`text-sm border rounded px-3 py-2 ${
              error.startsWith("Filtered:")
                ? "text-amber-700 bg-amber-50 border-amber-200"
                : "text-red-600 bg-red-50 border-red-200"
            }`}>{error}</p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors">
              Cancel
            </button>
            <button
              onClick={tab === "url" ? handleScrape : handleManual}
              disabled={loading || (tab === "url" ? !scrapeUrl.trim() : !title.trim() || !company.trim() || !description.trim())}
              className="px-4 py-2 text-sm text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors font-medium"
            >
              {loading ? "Adding…" : tab === "url" ? "Scrape & Add" : "Add Job"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// New Jobs page — jobs with no application yet
// ---------------------------------------------------------------------------

const SENIOR_RE = /\b(senior|sr\.?|principal|staff|lead|director|vp|vice\s+president|head\s+of|manager|architect|distinguished|fellow)\b/i;

type LocationFilter = "any" | "remote_utah" | "remote";

function ls<T>(key: string, fallback: T): T {
  try { const v = localStorage.getItem(key); return v !== null ? JSON.parse(v) : fallback; }
  catch { return fallback; }
}

export function NewJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Job | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [discoveryMsg, setDiscoveryMsg] = useState("");
  const [discoverySource, setDiscoverySource] = useState<string>("all");

  // Filters — persisted to localStorage
  const [minScore,      setMinScore]      = useState<number>(() => ls("nj_minscore", 0));
  const [locationFilter, setLocationFilter] = useState<LocationFilter>(() => ls("nj_location", "remote_utah"));
  const [hideSenior,    setHideSenior]    = useState<boolean>(() => ls("nj_hidesenior", true));

  const save = (key: string, val: unknown) => localStorage.setItem(key, JSON.stringify(val));

  const load = () => api.getJobs().then(setJobs).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const SOURCE_LABELS: Record<string, string> = {
    all: "All Sources", linkedin: "LinkedIn", indeed: "Indeed",
    remotive: "Remotive", remoteok: "RemoteOK", wwr: "We Work Remotely", arbeitnow: "Arbeitnow",
  };

  const handleDiscover = async () => {
    setDiscovering(true);
    const label = SOURCE_LABELS[discoverySource] ?? discoverySource;
    setDiscoveryMsg(`Searching ${label}…`);
    try {
      const result = await api.discoverJobs(discoverySource === "all" ? undefined : discoverySource);
      setDiscoveryMsg(`Found ${result.new} new job${result.new !== 1 ? "s" : ""} — ${result.sources.join(", ")}`);
      if (result.new > 0) load();
      setTimeout(() => setDiscoveryMsg(""), 8000);
    } catch (e) {
      setDiscoveryMsg("Discovery failed: " + (e as Error).message);
      setTimeout(() => setDiscoveryMsg(""), 5000);
    } finally {
      setDiscovering(false);
    }
  };

  const isUtah = (j: Job) => {
    const loc = (j.location || "").toLowerCase();
    return loc.includes("utah") || loc.includes(" ut") || loc.includes(",ut") ||
           loc.includes("provo") || loc.includes("salt lake") || loc.includes("orem");
  };

  // Only show jobs with no application at all + user filters
  const filtered = jobs.filter(j => {
    if (j.application_status) return false;
    if ((j.fit_score ?? 0) < minScore) return false;
    if (locationFilter === "remote" && !j.remote) return false;
    if (locationFilter === "remote_utah" && !j.remote && !isUtah(j)) return false;
    if (hideSenior && SENIOR_RE.test(j.title)) return false;
    return true;
  });

  const activeFilters = (locationFilter !== "any" ? 1 : 0) + (hideSenior ? 1 : 0) + (minScore > 0 ? 1 : 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-xl font-semibold text-gray-900">
          New Jobs <span className="text-gray-400 text-base font-normal">({filtered.length})</span>
        </h2>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md shadow-sm">
            <select
              value={discoverySource}
              onChange={e => setDiscoverySource(e.target.value)}
              disabled={discovering}
              className="border border-gray-300 border-r-0 rounded-l-md text-sm text-gray-700 bg-white px-2 py-2 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
            >
              {Object.entries(SOURCE_LABELS).map(([val, label]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
            <button
              onClick={handleDiscover}
              disabled={discovering}
              className="bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 text-gray-700 text-sm px-3 py-2 rounded-r-md font-medium transition-colors flex items-center gap-1.5"
            >
              {discovering
                ? <><span className="animate-spin inline-block">↻</span> Searching…</>
                : "↻ Search"}
            </button>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-md font-medium transition-colors"
          >
            + Add Job
          </button>
        </div>
      </div>

      {discoveryMsg && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-md px-4 py-2.5 text-sm text-indigo-700">
          {discoveryMsg}
        </div>
      )}

      {/* Filter bar */}
      <div className="bg-white border border-gray-200 rounded-md shadow-sm">
        <div className="flex items-center gap-1 px-3 py-2 border-b border-gray-100">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filters</span>
          {activeFilters > 0 && (
            <span className="ml-1 bg-indigo-100 text-indigo-700 text-xs font-semibold px-1.5 py-0.5 rounded-full">
              {activeFilters} active
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 text-sm">

          {/* Min score */}
          <label className="flex items-center gap-2 text-gray-600">
            Min score:
            <span className="text-indigo-600 font-semibold w-6">{minScore}</span>
            <input type="range" min={0} max={100} step={10} value={minScore}
              onChange={e => { const v = +e.target.value; setMinScore(v); save("nj_minscore", v); }}
              className="w-28 accent-indigo-600" />
          </label>

          {/* Location */}
          <div className="flex items-center gap-2 text-gray-600">
            <span>Location:</span>
            <div className="flex rounded-md border border-gray-300 overflow-hidden text-xs font-medium">
              {([ ["any", "Any"], ["remote_utah", "Remote / Utah"], ["remote", "Remote only"] ] as [LocationFilter, string][]).map(([val, label]) => (
                <button
                  key={val}
                  onClick={() => { setLocationFilter(val); save("nj_location", val); }}
                  className={`px-2.5 py-1.5 transition-colors border-r last:border-r-0 border-gray-300 ${
                    locationFilter === val
                      ? "bg-indigo-600 text-white"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Hide senior */}
          <label className="flex items-center gap-2 text-gray-600 cursor-pointer select-none">
            <input type="checkbox" checked={hideSenior}
              onChange={e => { setHideSenior(e.target.checked); save("nj_hidesenior", e.target.checked); }}
              className="accent-indigo-600" />
            Hide senior / lead roles
          </label>

        </div>
      </div>

      {loading ? (
        <p className="text-gray-400 animate-pulse">Loading...</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          {filtered.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <p className="text-lg font-medium text-gray-500">No new jobs</p>
              <p className="text-sm mt-1">Click <strong>+ Add Job</strong> to add one, or <strong>↻ Find New Jobs</strong> to search automatically</p>
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
                {filtered.map(job => (
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

      {showAddModal && (
        <AddJobModal
          onClose={() => setShowAddModal(false)}
          onAdded={() => { setLoading(true); load(); }}
        />
      )}
    </div>
  );
}

// Keep old export alias for any other imports
export { NewJobs as Jobs };
