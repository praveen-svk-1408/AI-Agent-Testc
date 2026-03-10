import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Check,
  XCircle,
  Clock,
  Monitor,
  Download,
  Image,
  Video,
  FileText,
  Activity,
  AlertTriangle,
  Trash2,
} from 'lucide-react'
import { Card, CardContent, CardHeader } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { RunStatusBadge } from '../components/ui/StatusBadge'
import { PageLoader, PageError } from '../components/ui/EmptyState'
import { runApi } from '../services/api'
import type { TestRunDetail, Artifact } from '../types'
import { format } from 'date-fns'
import { useTestRunSocket } from '../hooks/useTestRunSocket'

const artifactIcons: Record<string, React.ElementType> = {
  screenshot: Image,
  video: Video,
  trace: Activity,
  log: FileText,
}

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [run, setRun] = useState<TestRunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Connect WS for live updates if run is pending/running
  const { steps: wsSteps, status: wsStatus } = useTestRunSocket(
    run?.status === 'pending' || run?.status === 'running' ? runId! : null
  )

  const loadRun = () => {
    if (!runId) return
    setLoading(true)
    runApi.get(runId)
      .then(setRun)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadRun() }, [runId])

  // Reload when WS indicates completion
  useEffect(() => {
    if (wsStatus && wsStatus !== 'running') {
      setTimeout(loadRun, 1000)
    }
  }, [wsStatus])

  if (loading) return <PageLoader />
  if (error || !run) return <PageError message={error || 'Run not found'} onRetry={loadRun} />

  const summary = run.result_summary
  const artifacts = run.artifacts ?? []

  return (
    <div className="animate-fade-in">
      <PageHeader
        title={`Test Run ${run.id.slice(0, 8)}`}
        breadcrumbs={[
          { label: 'Test Runs', href: '/runs' },
          { label: `Run ${run.id.slice(0, 8)}` },
        ]}
        actions={
          <Button
            variant="danger"
            size="sm"
            onClick={() => {
              if (confirm('Delete this test run?')) {
                runApi.delete(run.id).then(() => navigate('/runs'))
              }
            }}
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </Button>
        }
      />

      {/* Status & Info */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="flex items-center gap-3">
            <RunStatusBadge status={run.status} />
            <span className="text-sm font-medium text-surface-200 capitalize">{run.status}</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3">
            <Monitor className="w-4 h-4 text-surface-400" />
            <span className="text-sm text-surface-200 capitalize">{run.browser}</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3">
            <Clock className="w-4 h-4 text-surface-400" />
            <span className="text-sm text-surface-200">
              {run.duration_ms ? `${(run.duration_ms / 1000).toFixed(2)}s` : 'In progress...'}
            </span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3">
            <Activity className="w-4 h-4 text-surface-400" />
            <span className="text-sm text-surface-200">
              {run.started_at ? format(new Date(run.started_at), 'MMM d, HH:mm:ss') : 'Not started'}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Result Summary */}
      {summary && (
        <Card className="mb-6">
          <CardHeader>
            <h3 className="text-sm font-semibold text-surface-200">Result Summary</h3>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-surface-100">{summary.total}</p>
                <p className="text-xs text-surface-400">Total Steps</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-emerald-400">{summary.passed}</p>
                <p className="text-xs text-surface-400">Passed</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-red-400">{summary.failed}</p>
                <p className="text-xs text-surface-400">Failed</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-surface-400">{summary.skipped}</p>
                <p className="text-xs text-surface-400">Skipped</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Message */}
      {run.error_message && (
        <Card className="mb-6 border-red-800/40">
          <CardContent className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-red-300 mb-1">Error</h3>
              <pre className="text-xs text-red-400/80 whitespace-pre-wrap font-mono">{run.error_message}</pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Live Steps (from WebSocket) */}
      {wsSteps.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <h3 className="text-sm font-semibold text-surface-200">Live Execution</h3>
          </CardHeader>
          <div className="divide-y divide-surface-800">
            {wsSteps.map((ws, i) => (
              <div key={i} className="px-5 py-3 flex items-center gap-3">
                {ws.status === 'passed' ? (
                  <Check className="w-4 h-4 text-emerald-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-400" />
                )}
                <Badge variant={ws.status === 'passed' ? 'success' : 'danger'}>{ws.action}</Badge>
                <span className="text-sm text-surface-300 flex-1 truncate">{ws.step}</span>
                <span className="text-xs text-surface-500">{ws.duration_ms}ms</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Artifacts */}
      {artifacts.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold text-surface-200">Artifacts ({artifacts.length})</h3>
          </CardHeader>
          <div className="divide-y divide-surface-800">
            {artifacts.map(art => {
              const Icon = artifactIcons[art.artifact_type] ?? FileText
              return (
                <div key={art.id} className="px-5 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 text-surface-400" />
                    <div>
                      <p className="text-sm text-surface-200">{art.file_name}</p>
                      <p className="text-xs text-surface-500">
                        {art.artifact_type} • {art.file_size ? `${(art.file_size / 1024).toFixed(1)} KB` : ''}
                      </p>
                    </div>
                  </div>
                  <a
                    href={runApi.downloadArtifact(run.id, art.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg text-surface-400 hover:text-primary-400 hover:bg-surface-800 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                </div>
              )
            })}
          </div>
        </Card>
      )}
    </div>
  )
}
