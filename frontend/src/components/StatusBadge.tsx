const STATUS_COLORS: Record<string, string> = {
  saved:    "bg-gray-100 text-gray-600 ring-gray-300",
  applied:  "bg-blue-50 text-blue-700 ring-blue-200",
  phone:    "bg-cyan-50 text-cyan-700 ring-cyan-200",
  onsite:   "bg-amber-50 text-amber-700 ring-amber-200",
  offer:    "bg-green-50 text-green-700 ring-green-200",
  rejected: "bg-red-50 text-red-600 ring-red-200",
};

export function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || STATUS_COLORS.saved;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ring-1 capitalize ${color}`}>
      {status}
    </span>
  );
}
