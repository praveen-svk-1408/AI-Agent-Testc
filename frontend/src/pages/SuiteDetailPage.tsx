import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Plus, FileCheck2, Trash2, Sparkles, Globe } from 'lucide-react'
import { Card, CardContent } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { Button } from '../components/ui/Button'
import { Modal } from '../components/ui/Modal'
import { Input, Textarea, Select } from '../components/ui/FormFields'
import { CaseStatusBadge } from '../components/ui/StatusBadge'
import { Badge } from '../components/ui/Badge'
import { EmptyState, PageLoader, PageError } from '../components/ui/EmptyState'
import { suiteApi, caseApi } from '../services/api'
import type { TestSuiteDetail, CreateTestCaseRequest, TestType } from '../types'
import { formatDistanceToNow } from 'date-fns'

const testTypes: { value: TestType; label: string }[] = [
  { value: 'functional', label: 'Functional' },
  { value: 'e2e', label: 'End-to-End' },
  { value: 'integration', label: 'Integration' },
  { value: 'accessibility', label: 'Accessibility' },
  { value: 'visual', label: 'Visual' },
  { value: 'performance', label: 'Performance' },
]

export function SuiteDetailPage() {
  const { suiteId } = useParams<{ suiteId: string }>()
  const navigate = useNavigate()
  const [suite, setSuite] = useState<TestSuiteDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<CreateTestCaseRequest>({
    title: '',
    description: '',
    test_type: 'functional',
  })

  const loadSuite = () => {
    if (!suiteId) return
    setLoading(true)
    setError(null)
    suiteApi.get(suiteId)
      .then(setSuite)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadSuite() }, [suiteId])

  const handleCreateCase = async () => {
    if (!suiteId || !form.title.trim() || !form.description.trim()) return
    setCreating(true)
    try {
      await caseApi.create(suiteId, form)
      setShowCreate(false)
      setForm({ title: '', description: '', test_type: 'functional' })
      loadSuite()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  const handleDeleteCase = async (e: React.MouseEvent, caseId: string) => {
    e.stopPropagation()
    if (!confirm('Delete this test case?')) return
    try {
      await caseApi.delete(caseId)
      loadSuite()
    } catch (e: any) {
      setError(e.message)
    }
  }

  if (loading) return <PageLoader />
  if (error || !suite) return <PageError message={error || 'Suite not found'} onRetry={loadSuite} />

  const cases = suite.test_cases ?? []

  return (
    <div className="animate-fade-in">
      <PageHeader
        title={suite.name}
        description={suite.description || undefined}
        breadcrumbs={[
          { label: 'Test Suites', href: '/suites' },
          { label: suite.name },
        ]}
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4" />
            Add Test Case
          </Button>
        }
      />

      {/* Suite Info */}
      <Card className="mb-6">
        <CardContent className="flex flex-wrap gap-6">
          <div className="flex items-center gap-2 text-sm text-surface-400">
            <Globe className="w-4 h-4" />
            <a
              href={suite.base_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-400 hover:text-primary-300 transition-colors"
            >
              {suite.base_url}
            </a>
          </div>
          <div className="flex items-center gap-2 text-sm text-surface-400">
            <FileCheck2 className="w-4 h-4" />
            {cases.length} test case{cases.length !== 1 ? 's' : ''}
          </div>
          {suite.app_description && (
            <p className="text-sm text-surface-400 w-full">{suite.app_description}</p>
          )}
        </CardContent>
      </Card>

      {/* Test Cases List */}
      {cases.length === 0 ? (
        <EmptyState
          icon={FileCheck2}
          title="No test cases"
          description="Add a test case and let AI generate executable test steps automatically."
          action={
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4" />
              Add Test Case
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {cases.map(tc => (
            <Card
              key={tc.id}
              hover
              onClick={() => navigate(`/suites/${suiteId}/cases/${tc.id}`)}
            >
              <CardContent className="flex items-center justify-between">
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0">
                    <FileCheck2 className="w-5 h-5 text-surface-400" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-medium text-surface-100 truncate">
                        {tc.title}
                      </h3>
                      <CaseStatusBadge status={tc.status} />
                      <Badge variant="default">{tc.test_type}</Badge>
                    </div>
                    <p className="text-xs text-surface-500 truncate mt-0.5">{tc.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  {tc.status === 'draft' && (
                    <div className="flex items-center gap-1 text-xs text-primary-400">
                      <Sparkles className="w-3 h-3" />
                      Generate
                    </div>
                  )}
                  <span className="text-xs text-surface-500">
                    {formatDistanceToNow(new Date(tc.updated_at), { addSuffix: true })}
                  </span>
                  <button
                    onClick={(e) => handleDeleteCase(e, tc.id)}
                    className="p-1.5 rounded-lg text-surface-500 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Test Case Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Test Case" size="md">
        <div className="space-y-4">
          <Input
            id="case-title"
            label="Test Title"
            placeholder="e.g. Verify user can login with valid credentials"
            value={form.title}
            onChange={e => setForm(prev => ({ ...prev, title: e.target.value }))}
          />
          <Textarea
            id="case-desc"
            label="Description (Natural Language)"
            placeholder="Describe what should be tested. AI will generate test steps from this.&#10;&#10;Example: Navigate to login, enter email and password, click login, verify dashboard loads."
            rows={4}
            value={form.description}
            onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
          />
          <Select
            id="case-type"
            label="Test Type"
            options={testTypes}
            value={form.test_type}
            onChange={e => setForm(prev => ({ ...prev, test_type: e.target.value as TestType }))}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button
              onClick={handleCreateCase}
              loading={creating}
              disabled={!form.title.trim() || !form.description.trim()}
            >
              <Sparkles className="w-4 h-4" />
              Create Test Case
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
