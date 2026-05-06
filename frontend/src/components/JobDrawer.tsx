import { useState } from "react";
import { api, Job, GeneratedContent } from "../lib/api";
import { ScoreBadge } from "./ScoreBadge";
import { TagInput } from "./TagInput";

function fmtSalary(min: number, max: number): string {
  if (!min && !max) return "—";
  if (min === max || !max) return `$${Math.round(min / 1000)}k`;
  return `$${Math.round(min / 1000)}k–$${Math.round(max / 1000)}k`;
}

interface Props {
  job: Job;
  onClose: () => void;
  onRefresh: () => void;
}

export function JobDrawer({ job: initialJob, onClose, onRefresh }: Props) {
  const [job, setJob] = useState<Job>(initialJob);
  const [editing, setEditing] = useState(false);
  const [editDraft, setEditDraft] = useState<Partial<Job>>({});
  const [saving, setSaving] = useState(false);
  const [rescoring, setRescoring] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<GeneratedContent | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [trackStatus, setTrackStatus] = useState(job.application_id ? job.application_status ?? "applied" : "applied");

  const startEdit = () => {
    setEditDraft({ ...job });
    setEditing(true);
    setGenerated(null);
  };
  const cancelEdit = () => { setEditing(false); setEditDraft({}); };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await api.updateJob(job.id, editDraft);
      setJob({ ...updated, application_id: job.application_id, application_status: job.application_status });
      setEditing(false);
      onRefresh();
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAndRescore = async () => {
    setSaving(true);
    try {
      const updated = await api.updateJob(job.id, editDraft);
      setEditing(false);
      setRescoring(true);
      const scored = await api.scoreJob(job.id);
      setJob({ ...updated, application_id: job.application_id, application_status: job.application_status, fit_score: scored.fit_score, fit_breakdown: scored.breakdown });
      onRefresh();
    } finally {
      setSaving(false);
      setRescoring(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setGenerated(null);
    try {
      const result = await api.generateContent(job.id, "both");
      setGenerated(result);
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete "${job.title}" at ${job.company}? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await api.deleteJob(job.id);
      onRefresh();
      onClose();
    } finally {
      setDeleting(false);
    }
  };

  const handleTrack = async () => {
    try {
      if (job.application_id) {
        await api.updateApplication(job.application_id, trackStatus, "");
      } else {
        await api.createApplication(job.id, trackStatus, "");
      }
      onRefresh();
      onClose();
    } catch (e) {
      alert("Failed: " + (e as Error).message);
    }
  };

  const trackLabel = job.application_id ? "Update Status" : "Track";

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <div className="fixed inset-y-0 right-0 w-[500px] bg-white border-l border-gray-200 shadow-xl overflow-y-auto z-50">
        <div className="p-5 space-y-4">

          {/* Header */}
          <div className="flex justify-between items-start">
            <div className="flex-1 min-w-0 pr-2">
              <h3 className="text-lg font-semibold text-gray-900 leading-snug">{job.title}</h3>
              <p className="text-gray-500 text-sm">{job.company}{job.location ? ` · ${job.location}` : ""}</p>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              {!editing && (
                <button onClick={startEdit}
                  className="text-xs text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 px-2 py-1 rounded transition-colors font-medium">
                  Edit
                </button>
              )}
              <button onClick={handleDelete} disabled={deleting}
                className="text-xs text-red-400 hover:text-red-600 hover:bg-red-50 px-2 py-1 rounded transition-colors disabled:opacity-50">
                {deleting ? "…" : "Delete"}
              </button>
              <button onClick={onClose}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none p-1">×</button>
            </div>
          </div>

          {editing ? (
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
            <>
              <div className="flex gap-2 flex-wrap items-center">
                <ScoreBadge score={job.fit_score} />
                {rescoring && <span className="text-xs text-indigo-500 animate-pulse">Scoring…</span>}
                {job.remote && (
                  <span className="bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded ring-1 ring-indigo-200 font-medium">Remote</span>
                )}
                <span className="text-gray-500 text-sm">{fmtSalary(job.salary_min, job.salary_max)}</span>
                <span className="text-gray-400 text-sm">
                  {job.experience_years != null && job.experience_years > 0
                    ? `${job.experience_years}+ yrs exp required`
                    : "YOE not specified"}
                </span>
              </div>

              {job.fit_breakdown && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2.5">
                  <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Fit Breakdown</p>
                  {[
                    ["Skill Match",  job.fit_breakdown.skill_match,      40],
                    ["Experience",   job.fit_breakdown.experience_match, 30],
                    ["Role Match",   job.fit_breakdown.role_match,       20],
                    ["Salary",       job.fit_breakdown.salary_match,     10],
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
                  {job.fit_breakdown.notes && (
                    <p className="text-xs text-gray-500 pt-1 border-t border-gray-200">{job.fit_breakdown.notes}</p>
                  )}
                </div>
              )}

              {job.skills.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">Required Skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {job.skills.map(s => {
                      const matched = job.fit_breakdown?.matched_skills.includes(s.toLowerCase());
                      return (
                        <span key={s} className={`text-xs px-2 py-0.5 rounded font-medium ${
                          matched ? "bg-green-50 text-green-700 ring-1 ring-green-200" : "bg-gray-100 text-gray-500"
                        }`}>{s}</span>
                      );
                    })}
                  </div>
                </div>
              )}

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
                <button onClick={handleTrack}
                  className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm px-3 py-1.5 rounded transition-colors font-medium">
                  {trackLabel}
                </button>
                <button onClick={handleGenerate} disabled={generating}
                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-3 py-1.5 rounded transition-colors font-medium">
                  {generating ? "Generating…" : "Generate Content"}
                </button>
              </div>

              {job.url && !job.url.startsWith("https://example.com") && (
                <a href={job.url} target="_blank" rel="noreferrer"
                  className="text-indigo-600 hover:text-indigo-800 text-sm font-medium block">
                  {(() => {
                    const u = job.url.toLowerCase();
                    if (u.includes("linkedin.com"))   return "Apply on LinkedIn ↗";
                    if (u.includes("indeed.com"))     return "Apply on Indeed ↗";
                    if (u.includes("glassdoor.com"))  return "Apply on Glassdoor ↗";
                    if (u.includes("ziprecruiter.com")) return "Apply on ZipRecruiter ↗";
                    if (u.includes("lever.co"))       return "Apply on Lever ↗";
                    if (u.includes("greenhouse.io"))  return "Apply on Greenhouse ↗";
                    if (u.includes("workday.com"))    return "Apply on Workday ↗";
                    if (u.includes("myworkdayjobs.com")) return "Apply on Workday ↗";
                    if (u.includes("icims.com"))      return "Apply on iCIMS ↗";
                    if (u.includes("smartrecruiters.com")) return "Apply on SmartRecruiters ↗";
                    if (u.includes("wellfound.com") || u.includes("angel.co")) return "Apply on Wellfound ↗";
                    if (u.includes("dice.com"))       return "Apply on Dice ↗";
                    if (u.includes("builtin.com"))    return "Apply on Built In ↗";
                    return "Apply on company website ↗";
                  })()}
                </a>
              )}

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
  );
}
