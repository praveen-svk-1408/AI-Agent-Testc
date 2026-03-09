"use client";

interface CodePreviewProps {
  code: string;
  fileName?: string;
}

export default function CodePreview({ code, fileName }: CodePreviewProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      {fileName && (
        <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-2">
          <span className="font-mono text-sm text-gray-600">{fileName}</span>
          <button
            onClick={() => navigator.clipboard.writeText(code)}
            className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-200 hover:text-gray-700"
          >
            Copy
          </button>
        </div>
      )}
      <pre className="overflow-x-auto bg-gray-900 p-4">
        <code className="text-sm leading-relaxed text-gray-100">{code}</code>
      </pre>
    </div>
  );
}
