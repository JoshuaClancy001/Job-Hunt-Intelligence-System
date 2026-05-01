import { useEffect, useState } from "react";
import { api, Job, GeneratedContent } from "../lib/api";
import { ScoreBadge } from "../components/ScoreBadge";
import { TagInput } from "../components/TagInput";

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

  // URL tab
  const [scrapeUrl, setScrapeUrl] = useState("");

  // Manual tab
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
      setError("Scrape failed: " + (e as Error).message);
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
      setError("Failed to add job: " + (e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg border border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="text-base font-semibold text-gray-900">Add Job</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        {/* Tabs */}
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
                  placeholder="https://jobs.lever.co/company/... or boards.greenhouse.io/..."
                  value={scrapeUrl}
                  onChange={e => setScrapeUrl(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleScrape()}
                />
              </div>
              <p className="text-xs text-gray-400">
                Works best with Greenhouse, Lever, and Ashby job postings. Title, company, and description are extracted automatically, then scored against your profile.
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
                  placeholder="Paste the full job description here. Skills, salary, experience requirements, and remote status will be extracted automatically..."
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                />
              </div>
            </>
          )}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
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
// Main Jobs page
// ---------------------------------------------------------------------------

export function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Job | null>(null);
  const [minScore, setMinScore] = useState(0);
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<GeneratedContent | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [trackStatus, setTrackStatus] = useState("applied");
  const [deleting, setDeleting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editDraft, setEditDraft] = useState<Partial<Job>>({});
  const [saving, setSaving] = useState(false);
  const [rescoring, setRescoring] = useState(false);

  const load = () => api.getJobs().then(setJobs).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const startEdit = (job: Job) => {
    setEditDraft({ ...job });
    setEditing(true);
    setGenerated(null);
  };

  const cancelEdit = () => { setEditing(false); setEditDraft({}); };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await api.updateJob(selected.id, editDraft);
      setSelected(updated);
      load();
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAndRescore = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await api.updateJob(selected.id, editDraft);
      setSelected(updated);
      load();
      setEditing(false);
      setRescoring(true);
      const scored = await api.scoreJob(selected.id);
      setSelected(prev => prev ? { ...prev, fit_score: scored.fit_score, fit_breakdown: scored.breakdown } : prev);
      load();
    } finally {
      setSaving(false);
      setRescoring(false);
    }
  };

  const filtered = jobs.filter(j =>
    (j.fit_score ?? 0) >= minScore && (!remoteOnly || j.remote)
  );

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

  const handleDelete = async (job: Job) => {
    if (!confirm(`Delete "${job.title}" at ${job.company}? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await api.deleteJob(job.id);
      setSelected(null);
      load();
    } finally {
      setDeleting(false);
    }
  };

  const handleTrack = async (job: Job) => {
    try {
      await api.createApplication(job.id, trackStatus, "");
      alert(`Tracked "${job.title}" as "${trackStatus}"`);
    } catch {
      alert("Already tracked — use the Applications page to update status.");
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">
          Jobs <span className="text-gray-400 text-base font-normal">({filtered.length})</span>
        </h2>
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-md font-medium transition-colors"
        >
          + Add Job
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
          {filtered.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <p className="text-lg font-medium text-gray-500">No jobs yet</p>
              <p className="text-sm mt-1">Click <strong>+ Add Job</strong> to scrape a URL or paste a job description</p>
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
                    onClick={() => { setSelected(job); setGenerated(null); }}
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

      {/* Detail drawer */}
      {selected && (
        <>
          <div className="fixed inset-0 bg-black/20 z-40" onClick={() => { setSelected(null); cancelEdit(); }} />
          <div className="fixed inset-y-0 right-0 w-[500px] bg-white border-l border-gray-200 shadow-xl overflow-y-auto z-50">
            <div className="p-5 space-y-4">

              {/* Drawer header */}
              <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0 pr-2">
                  <h3 className="text-lg font-semibold text-gray-900 leading-snug">{selected.title}</h3>
                  <p className="text-gray-500 text-sm">{selected.company}{selected.location ? ` · ${selected.location}` : ""}</p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {!editing && (
                    <button onClick={() => startEdit(selected)}
                      className="text-xs text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 px-2 py-1 rounded transition-colors font-medium">
                      Edit
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(selected)}
                    disabled={deleting}
                    className="text-xs text-red-400 hover:text-red-600 hover:bg-red-50 px-2 py-1 rounded transition-colors disabled:opacity-50"
                  >
                    {deleting ? "…" : "Delete"}
                  </button>
                  <button onClick={() => { setSelected(null); cancelEdit(); }}
                    className="text-gray-400 hover:text-gray-600 text-xl leading-none p-1">×</button>
                </div>
              </div>

              {editing ? (
                /* ── Edit form ── */
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
                      <input value={editDraft.title ?? ""} onChange={e => setEditDraft(d => ({ ...d, title: e.target.value }))}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Company</label>
                      <input value={editDraft.company ?? ""} onChange={e => setEditDraft(d => ({ ...d, company: e.target.value }))}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Location</label>
                      <input value={editDraft.location ?? ""} onChange={e => setEditDraft(d => ({ ...d, location: e.target.value }))}
                        placeholder="Remote, New York, etc."
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                    </div>
                    <div className="flex items-end pb-0.5">
                      <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer select-none">
                        <input type="checkbox" checked={editDraft.remote ?? false}
                          onChange={e => setEditDraft(d => ({ ...d, remote: e.target.checked }))}
                          className="accent-indigo-600 w-4 h-4" />
                        Remote position
                      </label>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Salary Min ($)</label>
                      <input type="number" min={0} step={5000}
                        value={editDraft.salary_min ?? 0}
                        onChange={e => setEditDraft(d => ({ ...d, salary_min: parseInt(e.target.value) || 0 }))}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Salary Max ($)</label>
                      <input type="number" min={0} step={5000}
                        value={editDraft.salary_max ?? 0}
                        onChange={e => setEditDraft(d => ({ ...d, salary_max: parseInt(e.target.value) || 0 }))}
                        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Exp. Required (years)</label>
                    <input type="number" min={0} max={20} step={0.5}
                      value={editDraft.experience_years ?? 0}
                      onChange={e => setEditDraft(d => ({ ...d, experience_years: parseFloat(e.target.value) || 0 }))}
                      className="w-32 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Apply URL</label>
                    <input value={editDraft.url ?? ""} onChange={e => setEditDraft(d => ({ ...d, url: e.target.value }))}
                      placeholder="https://..."
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                  </div>

                  <TagInput
                    label="Required Skills"
                    values={editDraft.skills ?? []}
                    onChange={skills => setEditDraft(d => ({ ...d, skills }))}
                    placeholder="react, python, typescript…"
                  />

                  <div className="flex gap-2 pt-1">
                    <button onClick={handleSaveAndRescore} disabled={saving || rescoring}
                      className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-md font-medium transition-colors">
                      {saving ? "Saving…" : rescoring ? "Scoring…" : "Save & Re-score"}
                    </button>
                    <button onClick={handleSave} disabled={saving}
                      className="bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 text-gray-700 text-sm px-4 py-2 rounded-md font-medium transition-colors">
                      Save Only
                    </button>
                    <button onClick={cancelEdit}
                      className="text-gray-500 hover:text-gray-700 text-sm px-3 py-2 transition-colors">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                /* ── Read-only view ── */
                <>
                  <div className="flex gap-2 flex-wrap items-center">
                    <ScoreBadge score={selected.fit_score} />
                    {rescoring && <span className="text-xs text-indigo-500 animate-pulse">Scoring…</span>}
                    {selected.remote && (
                      <span className="bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded ring-1 ring-indigo-200 font-medium">Remote</span>
                    )}
                    <span className="text-gray-500 text-sm">{fmtSalary(selected.salary_min, selected.salary_max)}</span>
                    <span className="text-gray-400 text-sm">
                      {selected.experience_years != null && selected.experience_years > 0
                        ? `${selected.experience_years}+ yrs exp required`
                        : "YOE not specified"}
                    </span>
                  </div>

                  {/* Fit breakdown */}
                  {selected.fit_breakdown && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2.5">
                      <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Fit Breakdown</p>
                      {[
                        ["Skill Match",  selected.fit_breakdown.skill_match,      40],
                        ["Experience",   selected.fit_breakdown.experience_match, 30],
                        ["Role Match",   selected.fit_breakdown.role_match,       20],
                        ["Salary",       selected.fit_breakdown.salary_match,     10],
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
                        <p className="text-xs text-gray-500 pt-1 border-t border-gray-200">{selected.fit_breakdown.notes}</p>
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
                              matched ? "bg-green-50 text-green-700 ring-1 ring-green-200" : "bg-gray-100 text-gray-500"
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
                    <button onClick={() => handleTrack(selected)}
                      className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm px-3 py-1.5 rounded transition-colors font-medium">
                      Track
                    </button>
                    <button onClick={() => handleGenerate(selected)} disabled={generating}
                      className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-3 py-1.5 rounded transition-colors font-medium">
                      {generating ? "Generating…" : "Generate Content"}
                    </button>
                  </div>

                  {selected.url && !selected.url.startsWith("https://example.com") && (
                    <a href={selected.url} target="_blank" rel="noreferrer"
                      className="text-indigo-600 hover:text-indigo-800 text-sm font-medium block">
                      {selected.url.includes("linkedin.com")
                        ? "Apply on LinkedIn ↗"
                        : "Apply on company website ↗"}
                    </a>
                  )}

                  {/* Generated content */}
                  {generated && (
                    <div className="space-y-3 pt-1 border-t border-gray-200">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Generated Content</p>
                        <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">via {generated.source}</span>
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
                              <li key={i} className="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded px-3 py-2">• {b}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </>
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
