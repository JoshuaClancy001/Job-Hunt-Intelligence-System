import { useEffect, useState } from "react";
import { api, Application } from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { ScoreBadge } from "../components/ScoreBadge";

const STATUSES = ["saved", "applied", "phone", "onsite", "offer", "rejected"];

export function Applications() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState<number | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => api.getApplications().then(setApps).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const startEdit = (app: Application) => {
    setEditId(app.id);
    setEditStatus(app.status);
    setEditNotes(app.notes);
  };

  const saveEdit = async () => {
    if (editId === null) return;
    setSaving(true);
    try {
      await api.updateApplication(editId, editStatus, editNotes);
      setEditId(null);
      load();
    } finally {
      setSaving(false);
    }
  };

  const fmtDate = (s: string | null) => {
    if (!s) return "—";
    return new Date(s).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  if (loading) return <p className="text-gray-400 animate-pulse">Loading...</p>;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900">
        Applications <span className="text-gray-400 text-base font-normal">({apps.length})</span>
      </h2>

      {apps.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-8 text-center text-gray-500">
          <p className="font-medium">No applications tracked yet.</p>
          <p className="text-sm mt-1 text-gray-400">Use the Jobs page to track applications, or run:</p>
          <code className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded mt-2 inline-block font-mono">
            python cli.py apply --job-id 1 --status applied
          </code>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 border-b border-gray-200">
                <th className="text-left px-4 py-2.5 font-medium">Job</th>
                <th className="text-left px-4 py-2.5 font-medium">Status</th>
                <th className="text-right px-4 py-2.5 font-medium hidden md:table-cell">Score</th>
                <th className="text-right px-4 py-2.5 font-medium hidden lg:table-cell">Applied</th>
                <th className="text-right px-4 py-2.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {apps.map(app => (
                <tr key={app.id} className="hover:bg-gray-50 transition-colors">
                  {editId === app.id ? (
                    <td colSpan={5} className="px-4 py-3">
                      <div className="flex flex-wrap gap-3 items-center">
                        <div className="min-w-0">
                          <p className="text-gray-800 font-medium">{app.title}</p>
                          <p className="text-gray-400 text-xs">{app.company}</p>
                        </div>
                        <select
                          value={editStatus}
                          onChange={e => setEditStatus(e.target.value)}
                          className="bg-white border border-gray-300 rounded text-sm text-gray-700 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                        >
                          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                        <input
                          value={editNotes}
                          onChange={e => setEditNotes(e.target.value)}
                          placeholder="Notes..."
                          className="flex-1 min-w-48 bg-white border border-gray-300 rounded text-sm text-gray-700 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                        />
                        <div className="flex gap-2">
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
                  ) : (
                    <>
                      <td className="px-4 py-3">
                        <p className="text-gray-800 font-medium">{app.title}</p>
                        <p className="text-gray-400 text-xs">{app.company}</p>
                        {app.notes && <p className="text-gray-500 text-xs mt-0.5 italic">{app.notes}</p>}
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={app.status} /></td>
                      <td className="px-4 py-3 text-right hidden md:table-cell">
                        <ScoreBadge score={app.fit_score ?? null} />
                      </td>
                      <td className="px-4 py-3 text-right text-gray-400 hidden lg:table-cell">
                        {fmtDate(app.applied_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => startEdit(app)}
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors">
                          Edit
                        </button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
