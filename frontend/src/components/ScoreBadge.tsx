interface ScoreBadgeProps {
  score: number | null;
}

export function ScoreBadge({ score }: ScoreBadgeProps) {
  if (score === null || score === undefined) {
    return <span className="text-gray-400 text-sm">—</span>;
  }
  const color =
    score >= 80 ? "bg-green-50 text-green-700 ring-green-200"
    : score >= 60 ? "bg-yellow-50 text-yellow-700 ring-yellow-200"
    : score >= 40 ? "bg-orange-50 text-orange-700 ring-orange-200"
    : "bg-red-50 text-red-700 ring-red-200";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-sm font-bold ring-1 ${color}`}>
      {score}
    </span>
  );
}
