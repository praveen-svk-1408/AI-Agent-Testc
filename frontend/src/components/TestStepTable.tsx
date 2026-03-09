import type { TestStep } from "@/types";

interface TestStepTableProps {
  steps: TestStep[];
}

export default function TestStepTable({ steps }: TestStepTableProps) {
  if (steps.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-400">
        No test steps generated yet.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">#</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Action</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Selector</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Value</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Expected Result</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Description</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {steps.map((step) => (
            <tr key={step.id} className="hover:bg-gray-50">
              <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">{step.order}</td>
              <td className="whitespace-nowrap px-4 py-3">
                <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                  {step.action}
                </span>
              </td>
              <td className="max-w-[200px] truncate px-4 py-3 font-mono text-xs text-gray-600">
                {step.selector || "—"}
              </td>
              <td className="max-w-[150px] truncate px-4 py-3 text-sm text-gray-600">
                {step.value || "—"}
              </td>
              <td className="max-w-[200px] truncate px-4 py-3 text-sm text-gray-600">
                {step.expected_result || "—"}
              </td>
              <td className="max-w-[200px] truncate px-4 py-3 text-sm text-gray-500">
                {step.description || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
