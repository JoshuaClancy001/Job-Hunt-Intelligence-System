import { useEffect, useState, Fragment } from "react";
import { api, Application } from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { ScoreBadge } from "../components/ScoreBadge";

const STATUSES = ["saved", "applied", "phone", "onsite", "offer", "rejected"];

const STATUS_LABELS: Record<string, string> = {
  saved:    "Saved",
  applied:  "Applied",
  phone:    "Interviewing",
  onsite:   "Onsite",
  offer:    "Offer",
  rejected: "Rejected",
};

const STATUS_DOT: Record<string, string> = {
  saved:    "bg-gray-400",
  applied:  "bg-blue-500",
  phone:    "bg-cyan-500",
  onsite:   "bg-amber-500",
  offer:    "bg-green-500",
  rejected: "bg-red-400",
};

interface HistoryEntry { status: string; changed_at: string; }

function fmtDate(s: string | null) {
  if (!s) return "—";
  return new Date(s + (s.includes("T") ? "" : "T00:00:00")).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function fmtDateTime(s: string) {
  return new Date(s + "Z").toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function fmtSalary(min?: number, max?: number) {
  if (!min && !max) return "—";
  const fmt = (n: number) => n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${n}`;
  if (!max || min === max) return fmt(min!);
  return `${fmt(min!)} – ${fmt(max)}`;
}

function Timeline({ appId }: { appId: number }) {
  const [history, setHistory] = useState<HistoryEntry[] | null>(null);
  useEffect(() => { api.getApplicationHistory(appId).then(setHistory); }, [appId]);

  if (!history) return <p className="text-xs text-gray-400 animate-pulse py-1">Loading…</p>;
  if (history.length === 0) return <p className="text-xs text-gray-400 py-1">No history yet.</p>;

  return (
    <ol className="flex flex-col gap-0">
      {history.map((entry, i) => (
        <li key={i} className="flex items-start gap-2.5">
          <div className="flex flex-col items-center">
            <div className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${STATUS_DOT[entry.status] ?? "bg-gray-400"}`} />
            {i < history.length - 1 && <div className="w-px flex-1 bg-gray-200 my-0.5" style={{ minHeight: 14 }} />}
          </div>
          <div className="pb-2.5">
            <span className="text-xs font-medium text-gray-700">{STATUS_LABELS[entry.status] ?? entry.status}</span>
            <span className="text-xs text-gray-400 ml-1.5">{fmtDateTime(entry.changed_at)}</span>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function Applications() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editRejection, setEditRejection] = useState("");
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const load = () => api.getApplications().then(setApps).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const startEdit = (app: Application) => {
    setEditId(app.id);
    setEditStatus(app.status);
    setEditNotes(app.notes || "");
    setEditRejection(app.rejection_reason || "");
    setExpandedId(null);
  };

  const saveEdit = async () => {
    if (editId === null) return;
    setSaving(true);
    try {
      await api.updateApplication(editId, editStatus, editNotes, editRejection);
      setEditId(null);
      load();
    } finally {
      setSaving(false);
    }
  };

  const toggleHistory = (id: number) =>
    setExpandedId(prev => prev === id ? null : id);

  if (loading) return <p className="text-gray-400 animate-pulse">Loading...</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">
          Applications <span className="text-gray-400 text-base font-normal">({apps.length})</span>
        </h2>
      </div>

      {apps.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 text-center text-gray-500">
          <p className="font-medium">No applications tracked yet.</p>
          <p className="text-sm mt-1 text-gray-400">Go to the Jobs page and click "Track Application" on any job.</p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead>
                <tr className="bg-gray-50 text-xs text-gray-500 border-b border-gray-200">
                  <th className="text-left px-4 py-2.5 font-medium w-36">Company</th>
                  <th className="text-left px-4 py-2.5 font-medium">Role</th>
                  <th className="text-left px-4 py-2.5 font-medium w-28">Status</th>
                  <th className="text-right px-4 py-2.5 font-medium w-24">Salary</th>
                  <th className="text-right px-4 py-2.5 font-medium w-28">Score</th>
                  <th className="text-right px-4 py-2.5 font-medium w-24">Submitted</th>
                  <th className="text-left px-4 py-2.5 font-medium w-40">Rejection Reason</th>
                  <th className="text-right px-4 py-2.5 font-medium w-28">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {apps.map(app => (
                  <Fragment key={app.id}>
                    {editId === app.id ? (
                      <tr className="bg-indigo-50/40">
                        <td colSpan={8} className="px-4 py-3">
                          <div className="flex flex-wrap gap-3 items-start">
                            <div className="min-w-0 flex-shrink-0">
                              <p className="text-gray-800 font-medium">{app.company}</p>
                              <p className="text-gray-500 text-xs">{app.title}</p>
                            </div>
                            <div className="flex flex-wrap gap-2 flex-1">
                              <div className="flex flex-col gap-1">
                                <label className="text-xs text-gray-500">Status</label>
                                <select
                                  value={editStatus}
                                  onChange={e => setEditStatus(e.target.value)}
                                  className="bg-white border border-gray-300 rounded text-sm text-gray-700 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                                >
                                  {STATUSES.map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
                                </select>
                              </div>
                              {(editStatus === "rejected") && (
                                <div className="flex flex-col gap-1 min-w-48">
                                  <label className="text-xs text-gray-500">Rejection Reason</label>
                                  <input
                                    value={editRejection}
                                    onChange={e => setEditRejection(e.target.value)}
                                    placeholder="e.g. Not a good fit"
                                    className="bg-white border border-gray-300 rounded text-sm text-gray-700 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                                  />
                                </div>
                              )}
                              <div className="flex flex-col gap-1 flex-1 min-w-48">
                                <label className="text-xs text-gray-500">Notes</label>
                                <input
                                  value={editNotes}
                                  onChange={e => setEditNotes(e.target.value)}
                                  placeholder="Notes..."
                                  className="w-full bg-white border border-gray-300 rounded text-sm text-gray-700 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                                />
                              </div>
                            </div>
                            <div className="flex gap-2 items-end pb-0.5">
                              <button onClick={saveEdit} disabled={saving}
                                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded transition-colors">
                                {saving ? "Saving…" : "Save"}
                              </button>
                              <button onClick={() => setEditId(null)}
                                className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-600 text-xs px-3 py-1.5 rounded transition-colors">
                                Cancel
                              </button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      <tr className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3">
                          <p className="text-gray-800 font-medium leading-tight">{app.company}</p>
                        </td>
                        <td className="px-4 py-3 text-gray-600">{app.title}</td>
                        <td className="px-4 py-3"><StatusBadge status={app.status} /></td>
                        <td className="px-4 py-3 text-right text-gray-500 text-xs tabular-nums">
                          {fmtSalary(app.salary_min, app.salary_max)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <ScoreBadge score={app.fit_score ?? null} />
                        </td>
                        <td className="px-4 py-3 text-right text-gray-400 text-xs tabular-nums whitespace-nowrap">
                          {fmtDate(app.applied_at)}
                        </td>
                        <td className="px-4 py-3 text-gray-400 text-xs">
                          {app.rejection_reason || (app.status === "rejected" ? <span className="italic">—</span> : "")}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end items-center gap-3">
                            {app.url && (
                              <a href={app.url} target="_blank" rel="noreferrer"
                                className="text-xs text-gray-400 hover:text-gray-600 transition-colors" title="Open job posting">
                                ↗
                              </a>
                            )}
                            <button
                              onClick={() => toggleHistory(app.id)}
                              className="text-xs text-gray-500 hover:text-gray-700 font-medium transition-colors"
                            >
                              {expandedId === app.id ? "▲" : "▾"}
                            </button>
                            <button onClick={() => startEdit(app)}
                              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors">
                              Edit
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}

                    {expandedId === app.id && editId !== app.id && (
                      <tr className="bg-gray-50/60">
                        <td colSpan={8} className="px-6 py-3 border-b border-gray-100">
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2.5">
                            Status Timeline
                          </p>
                          <Timeline appId={app.id} />
                          {app.notes && (
                            <p className="text-xs text-gray-500 mt-1 italic">Note: {app.notes}</p>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
