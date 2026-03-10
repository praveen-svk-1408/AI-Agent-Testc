import { useState, useCallback } from "react";
import type { TestStep, UpdateTestStepData } from "@/types";

const ACTIONS = [
  "navigate", "click", "type", "fill", "select", "hover", "press",
  "clear", "scroll", "verify_text", "verify_element", "wait", "screenshot",
];

interface TestStepTableProps {
  steps: TestStep[];
  onSave?: (steps: UpdateTestStepData[]) => Promise<void>;
  saving?: boolean;
}

export default function TestStepTable({ steps, onSave, saving }: TestStepTableProps) {
  const [editSteps, setEditSteps] = useState<UpdateTestStepData[] | null>(null);
  const isEditing = editSteps !== null;

  const startEditing = useCallback(() => {
    setEditSteps(
      steps.map((s) => ({
        order: s.order,
        action: s.action,
        selector: s.selector,
        value: s.value,
        expected_result: s.expected_result,
        description: s.description,
      }))
    );
  }, [steps]);

  const cancelEditing = () => setEditSteps(null);

  const handleFieldChange = (index: number, field: keyof UpdateTestStepData, value: string) => {
    if (!editSteps) return;
    setEditSteps((prev) =>
      prev!.map((s, i) => (i === index ? { ...s, [field]: value || null } : s))
    );
  };

  const addStep = () => {
    if (!editSteps) return;
    const nextOrder = editSteps.length > 0 ? Math.max(...editSteps.map((s) => s.order)) + 1 : 1;
    setEditSteps([...editSteps, {
      order: nextOrder,
      action: "click",
      selector: null,
      value: null,
      expected_result: null,
      description: null,
    }]);
  };

  const removeStep = (index: number) => {
    if (!editSteps) return;
    const updated = editSteps.filter((_, i) => i !== index).map((s, i) => ({ ...s, order: i + 1 }));
    setEditSteps(updated);
  };

  const moveStep = (index: number, direction: "up" | "down") => {
    if (!editSteps) return;
    const target = direction === "up" ? index - 1 : index + 1;
    if (target < 0 || target >= editSteps.length) return;
    const updated = [...editSteps];
    [updated[index], updated[target]] = [updated[target], updated[index]];
    setEditSteps(updated.map((s, i) => ({ ...s, order: i + 1 })));
  };

  const handleSave = async () => {
    if (!editSteps || !onSave) return;
    await onSave(editSteps);
    setEditSteps(null);
  };

  if (steps.length === 0 && !isEditing) {
    return (
      <p className="py-8 text-center text-sm text-gray-400">
        No test steps generated yet.
      </p>
    );
  }

  const displaySteps = isEditing ? editSteps! : steps.map((s) => ({
    order: s.order,
    action: s.action,
    selector: s.selector,
    value: s.value,
    expected_result: s.expected_result,
    description: s.description,
  }));

  return (
    <div>
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-3 py-2">
        <span className="text-xs font-medium text-gray-500">
          {displaySteps.length} step{displaySteps.length !== 1 ? "s" : ""}
        </span>
        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button
                onClick={addStep}
                className="rounded bg-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300"
              >
                + Add Step
              </button>
              <button
                onClick={cancelEditing}
                disabled={saving}
                className="rounded bg-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Steps"}
              </button>
            </>
          ) : (
            onSave && (
              <button
                onClick={startEditing}
                className="rounded bg-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300"
              >
                Edit Steps
              </button>
            )
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-10 px-2 py-2 text-left text-xs font-medium uppercase text-gray-500">#</th>
              <th className="px-2 py-2 text-left text-xs font-medium uppercase text-gray-500">Action</th>
              <th className="px-2 py-2 text-left text-xs font-medium uppercase text-gray-500">Selector</th>
              <th className="px-2 py-2 text-left text-xs font-medium uppercase text-gray-500">Value</th>
              <th className="px-2 py-2 text-left text-xs font-medium uppercase text-gray-500">Expected</th>
              <th className="px-2 py-2 text-left text-xs font-medium uppercase text-gray-500">Description</th>
              {isEditing && (
                <th className="w-20 px-2 py-2 text-left text-xs font-medium uppercase text-gray-500">Actions</th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {displaySteps.map((step, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="whitespace-nowrap px-2 py-2 text-xs text-gray-500">{step.order}</td>
                <td className="px-2 py-2">
                  {isEditing ? (
                    <select
                      value={step.action}
                      onChange={(e) => handleFieldChange(i, "action", e.target.value)}
                      className="w-full rounded border border-gray-300 px-1.5 py-1 text-xs focus:border-blue-500 focus:outline-none"
                    >
                      {ACTIONS.map((a) => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  ) : (
                    <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                      {step.action}
                    </span>
                  )}
                </td>
                <td className="px-2 py-2">
                  {isEditing ? (
                    <input
                      type="text"
                      value={step.selector || ""}
                      onChange={(e) => handleFieldChange(i, "selector", e.target.value)}
                      placeholder="selector"
                      className="w-full rounded border border-gray-300 px-1.5 py-1 font-mono text-xs focus:border-blue-500 focus:outline-none"
                    />
                  ) : (
                    <span className="max-w-[180px] truncate font-mono text-xs text-gray-600 block">
                      {step.selector || "—"}
                    </span>
                  )}
                </td>
                <td className="px-2 py-2">
                  {isEditing ? (
                    <input
                      type="text"
                      value={step.value || ""}
                      onChange={(e) => handleFieldChange(i, "value", e.target.value)}
                      placeholder="value"
                      className="w-full rounded border border-gray-300 px-1.5 py-1 text-xs focus:border-blue-500 focus:outline-none"
                    />
                  ) : (
                    <span className="max-w-[140px] truncate text-xs text-gray-600 block">
                      {step.value || "—"}
                    </span>
                  )}
                </td>
                <td className="px-2 py-2">
                  {isEditing ? (
                    <input
                      type="text"
                      value={step.expected_result || ""}
                      onChange={(e) => handleFieldChange(i, "expected_result", e.target.value)}
                      placeholder="expected"
                      className="w-full rounded border border-gray-300 px-1.5 py-1 text-xs focus:border-blue-500 focus:outline-none"
                    />
                  ) : (
                    <span className="max-w-[180px] truncate text-xs text-gray-600 block">
                      {step.expected_result || "—"}
                    </span>
                  )}
                </td>
                <td className="px-2 py-2">
                  {isEditing ? (
                    <input
                      type="text"
                      value={step.description || ""}
                      onChange={(e) => handleFieldChange(i, "description", e.target.value)}
                      placeholder="description"
                      className="w-full rounded border border-gray-300 px-1.5 py-1 text-xs focus:border-blue-500 focus:outline-none"
                    />
                  ) : (
                    <span className="max-w-[180px] truncate text-xs text-gray-500 block">
                      {step.description || "—"}
                    </span>
                  )}
                </td>
                {isEditing && (
                  <td className="whitespace-nowrap px-2 py-2">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => moveStep(i, "up")}
                        disabled={i === 0}
                        className="rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-gray-600 disabled:opacity-30"
                        title="Move up"
                      >
                        ▲
                      </button>
                      <button
                        onClick={() => moveStep(i, "down")}
                        disabled={i === displaySteps.length - 1}
                        className="rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-gray-600 disabled:opacity-30"
                        title="Move down"
                      >
                        ▼
                      </button>
                      <button
                        onClick={() => removeStep(i)}
                        className="rounded p-0.5 text-red-400 hover:bg-red-100 hover:text-red-600"
                        title="Delete step"
                      >
                        ✕
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
