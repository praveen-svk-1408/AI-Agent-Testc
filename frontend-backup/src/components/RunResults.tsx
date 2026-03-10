import type { Artifact } from "@/types";
import { RUN_STATUSES } from "@/lib/constants";
import { formatDuration } from "@/lib/utils";
import { getArtifactDownloadUrl } from "@/services/api";
import type { TestRunDetail } from "@/types";

interface RunResultsProps {
  run: TestRunDetail;
}

export default function RunResults({ run }: RunResultsProps) {
  const statusConfig = RUN_STATUSES[run.status] || RUN_STATUSES.pending;

  // Group artifacts by type
  const screenshots = run.artifacts.filter((a) => a.artifact_type === "screenshot");
  const videos = run.artifacts.filter((a) => a.artifact_type === "video");
  const traces = run.artifacts.filter((a) => a.artifact_type === "trace");
  const logs = run.artifacts.filter((a) => a.artifact_type === "log");

  return (
    <div className="space-y-6">
      {/* Status Banner */}
      <div className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4">
        <span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${statusConfig.color}`}>
          {statusConfig.label}
        </span>
        <span className="text-sm text-gray-500">Browser: {run.browser}</span>
        <span className="text-sm text-gray-500">
          Duration: {formatDuration(run.duration_ms)}
        </span>
        {run.headed && (
          <span className="text-sm text-gray-500">Headed mode</span>
        )}
      </div>

      {/* Error Message */}
      {run.error_message && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h4 className="text-sm font-medium text-red-800">Error</h4>
          <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-sm text-red-700">
            {run.error_message}
          </pre>
        </div>
      )}

      {/* Screenshots */}
      {screenshots.length > 0 && (
        <div>
          <h4 className="mb-3 text-sm font-medium text-gray-700">
            Screenshots ({screenshots.length})
          </h4>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {screenshots.map((artifact) => (
              <a
                key={artifact.id}
                href={getArtifactDownloadUrl(run.id, artifact.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="group overflow-hidden rounded-lg border border-gray-200 bg-white transition-shadow hover:shadow-md"
              >
                <img
                  src={getArtifactDownloadUrl(run.id, artifact.id)}
                  alt={artifact.file_name}
                  className="h-40 w-full object-cover object-top"
                />
                <div className="p-2">
                  <p className="truncate text-xs font-medium text-gray-700 group-hover:text-blue-600">
                    {artifact.file_name}
                  </p>
                  {artifact.file_size && (
                    <p className="text-xs text-gray-400">
                      {(artifact.file_size / 1024).toFixed(1)} KB
                    </p>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Videos */}
      {videos.length > 0 && (
        <div>
          <h4 className="mb-3 text-sm font-medium text-gray-700">
            Videos ({videos.length})
          </h4>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {videos.map((artifact) => (
              <div key={artifact.id} className="overflow-hidden rounded-lg border border-gray-200 bg-white">
                <video
                  controls
                  className="w-full"
                  src={getArtifactDownloadUrl(run.id, artifact.id)}
                />
                <div className="p-2">
                  <p className="truncate text-xs font-medium text-gray-700">
                    {artifact.file_name}
                  </p>
                  {artifact.file_size && (
                    <p className="text-xs text-gray-400">
                      {(artifact.file_size / 1024).toFixed(1)} KB
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Other Artifacts (traces, logs) */}
      {(traces.length > 0 || logs.length > 0) && (
        <div>
          <h4 className="mb-3 text-sm font-medium text-gray-700">Other Artifacts</h4>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...traces, ...logs].map((artifact) => (
              <ArtifactCard key={artifact.id} artifact={artifact} runId={run.id} />
            ))}
          </div>
        </div>
      )}

      {/* Result Summary */}
      {run.result_summary && (
        <div>
          <h4 className="mb-3 text-sm font-medium text-gray-700">Result Summary</h4>
          <div className="grid grid-cols-4 gap-3">
            <SummaryCard label="Total" value={run.result_summary.total as number} />
            <SummaryCard label="Passed" value={run.result_summary.passed as number} color="text-green-600" />
            <SummaryCard label="Failed" value={run.result_summary.failed as number} color="text-red-600" />
            <SummaryCard label="Skipped" value={run.result_summary.skipped as number} color="text-gray-500" />
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  color = "text-gray-900",
}: {
  label: string;
  value?: number;
  color?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
      <p className="text-xs font-medium uppercase text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color}`}>{value ?? "—"}</p>
    </div>
  );
}

function ArtifactCard({ artifact, runId }: { artifact: Artifact; runId: string }) {
  const iconMap: Record<string, string> = {
    screenshot: "🖼️",
    video: "🎬",
    trace: "📊",
    log: "📄",
  };

  return (
    <a
      href={getArtifactDownloadUrl(runId, artifact.id)}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md"
    >
      <span className="text-lg">{iconMap[artifact.artifact_type] || "📎"}</span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-900">{artifact.file_name}</p>
        <p className="text-xs text-gray-500">
          {artifact.artifact_type}
          {artifact.file_size ? ` · ${(artifact.file_size / 1024).toFixed(1)} KB` : ""}
        </p>
      </div>
      <svg className="h-4 w-4 flex-shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
    </a>
  );
}
