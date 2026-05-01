import { useState, KeyboardEvent } from "react";

export function TagInput({
  label,
  values,
  onChange,
  placeholder,
}: {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");

  const add = () => {
    const val = input.trim().toLowerCase();
    if (val && !values.includes(val)) onChange([...values, val]);
    setInput("");
  };

  const remove = (v: string) => onChange(values.filter(x => x !== v));

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add();
    } else if (e.key === "Backspace" && !input && values.length) {
      remove(values[values.length - 1]);
    }
  };

  return (
    <div>
      {label && <label className="block text-xs font-medium text-gray-600 mb-1.5">{label}</label>}
      <div className="min-h-[38px] flex flex-wrap gap-1.5 bg-white border border-gray-300 rounded-md px-2.5 py-2 focus-within:ring-2 focus-within:ring-indigo-300 focus-within:border-indigo-400">
        {values.map(v => (
          <span key={v} className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded ring-1 ring-indigo-200">
            {v}
            <button type="button" onClick={() => remove(v)}
              className="text-indigo-400 hover:text-indigo-700 leading-none">×</button>
          </span>
        ))}
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          onBlur={add}
          placeholder={values.length === 0 ? placeholder : ""}
          className="flex-1 min-w-24 text-sm outline-none placeholder-gray-400 bg-transparent"
        />
      </div>
      <p className="text-xs text-gray-400 mt-1">Enter or comma to add</p>
    </div>
  );
}
