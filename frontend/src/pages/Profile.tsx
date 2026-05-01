import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { TagInput } from "../components/TagInput";

interface ProfileData {
  name: string;
  skills: string[];
  experience_years: number;
  preferred_roles: string[];
  preferred_locations: string[];
  min_salary: number;
  summary: string;
}

export function Profile() {
  const [profile, setProfile] = useState<ProfileData>({
    name: "",
    skills: [],
    experience_years: 0,
    preferred_roles: [],
    preferred_locations: [],
    min_salary: 0,
    summary: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getProfile()
      .then(data => setProfile(data as unknown as ProfileData))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleReload = async () => {
    setReloading(true);
    setError("");
    try {
      const data = await api.reloadProfileFromFile();
      setProfile(data as unknown as ProfileData);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setReloading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await api.updateProfile(profile as unknown as Record<string, unknown>);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const set = (key: keyof ProfileData) => (value: ProfileData[typeof key]) =>
    setProfile(p => ({ ...p, [key]: value }));

  if (loading) return <p className="text-gray-400 animate-pulse">Loading...</p>;

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">Candidate Profile</h2>
        <div className="flex gap-2">
          <button
            onClick={handleReload}
            disabled={reloading}
            className="bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 text-gray-600 text-sm px-3 py-2 rounded-md font-medium transition-colors"
            title="Overwrite with data from profile.json on disk"
          >
            {reloading ? "Loading…" : "↺ Load from profile.json"}
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-md font-medium transition-colors"
          >
            {saving ? "Saving…" : saved ? "✓ Saved" : "Save Profile"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 space-y-5">
        <h3 className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-3">
          Personal Info
        </h3>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Full Name</label>
          <input
            value={profile.name}
            onChange={e => set("name")(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            placeholder="Your name"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Professional Summary</label>
          <textarea
            value={profile.summary}
            onChange={e => set("summary")(e.target.value)}
            rows={4}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
            placeholder="Brief summary of your background and what you're looking for..."
          />
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 space-y-5">
        <h3 className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-3">
          Experience & Skills
        </h3>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">
            Years of Experience
          </label>
          <input
            type="number"
            min={0}
            max={40}
            step={0.5}
            value={profile.experience_years}
            onChange={e => set("experience_years")(parseFloat(e.target.value) || 0)}
            className="w-32 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
        </div>

        <TagInput
          label="Skills"
          values={profile.skills}
          onChange={set("skills")}
          placeholder="python, react, typescript…"
        />
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 space-y-5">
        <h3 className="text-sm font-semibold text-gray-700 border-b border-gray-100 pb-3">
          Job Preferences
        </h3>

        <TagInput
          label="Preferred Role Titles"
          values={profile.preferred_roles}
          onChange={set("preferred_roles")}
          placeholder="software engineer, full stack engineer…"
        />

        <TagInput
          label="Preferred Locations"
          values={profile.preferred_locations}
          onChange={set("preferred_locations")}
          placeholder="remote, san francisco, new york…"
        />

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">
            Minimum Salary (USD/year)
          </label>
          <div className="relative w-48">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
            <input
              type="number"
              min={0}
              step={5000}
              value={profile.min_salary || ""}
              onChange={e => set("min_salary")(parseInt(e.target.value) || 0)}
              className="w-full border border-gray-300 rounded-md pl-7 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
              placeholder="90000"
            />
          </div>
          {profile.min_salary > 0 && (
            <p className="text-xs text-gray-400 mt-1">
              ${profile.min_salary.toLocaleString()}/yr
            </p>
          )}
        </div>
      </div>

      {/* Scoring explainer */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4 text-xs text-indigo-700 space-y-1">
        <p className="font-semibold">How your profile affects fit scores</p>
        <p>Skills match → up to 40 pts · Experience → up to 30 pts · Role title → up to 20 pts · Salary → up to 10 pts</p>
        <p className="text-indigo-500">After saving, re-analyze jobs to update scores: go to Jobs and use the backend <code className="bg-indigo-100 px-1 rounded">POST /jobs/&#123;id&#125;/score</code> or run <code className="bg-indigo-100 px-1 rounded">python cli.py analyze</code>.</p>
      </div>

      <div className="flex justify-end pb-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-6 py-2 rounded-md font-medium transition-colors"
        >
          {saving ? "Saving…" : saved ? "✓ Saved" : "Save Profile"}
        </button>
      </div>
    </div>
  );
}
