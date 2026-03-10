import Link from "next/link";
import type { TestSuite } from "@/types";
import { formatDate } from "@/lib/utils";

interface SuiteCardProps {
  suite: TestSuite;
  onDelete?: (id: string) => void;
}

export default function SuiteCard({ suite, onDelete }: SuiteCardProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <Link href={`/suites/${suite.id}`} className="group flex-1">
          <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600">
            {suite.name}
          </h3>
        </Link>
        {onDelete && (
          <button
            onClick={() => onDelete(suite.id)}
            className="ml-2 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
            title="Delete suite"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
      {suite.description && (
        <p className="mt-2 text-sm text-gray-500 line-clamp-2">{suite.description}</p>
      )}
      <div className="mt-4 flex items-center gap-4 text-sm text-gray-400">
        <span className="inline-flex items-center gap-1">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <span className="max-w-[200px] truncate text-gray-500">{suite.base_url}</span>
        </span>
        <span className="inline-flex items-center gap-1">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          {suite.test_case_count} case{suite.test_case_count !== 1 ? "s" : ""}
        </span>
      </div>
      <p className="mt-3 text-xs text-gray-400">Created {formatDate(suite.created_at)}</p>
    </div>
  );
}
