import { TEST_CASE_STATUSES, RUN_STATUSES } from "@/lib/constants";

interface StatusBadgeProps {
  status: string;
  type: "case" | "run";
}

export default function StatusBadge({ status, type }: StatusBadgeProps) {
  const config =
    type === "case"
      ? TEST_CASE_STATUSES[status as keyof typeof TEST_CASE_STATUSES]
      : RUN_STATUSES[status as keyof typeof RUN_STATUSES];

  if (!config) {
    return (
      <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
        {status}
      </span>
    );
  }

  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${config.color}`}>
      {config.label}
    </span>
  );
}
