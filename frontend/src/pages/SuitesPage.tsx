import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Globe, FolderKanban, Trash2 } from 'lucide-react'
import { Card, CardContent } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { Button } from '../components/ui/Button'
import { Modal } from '../components/ui/Modal'
import { Input, Textarea } from '../components/ui/FormFields'
import { EmptyState, PageLoader, PageError } from '../components/ui/EmptyState'
import { suiteApi } from '../services/api'
import type { TestSuite, CreateTestSuiteRequest } from '../types'
import { formatDistanceToNow } from 'date-fns'

export function SuitesPage() {
  const navigate = useNavigate()
  const [suites, setSuites] = useState<TestSuite[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState<CreateTestSuiteRequest>({
    name: '',
    base_url: '',
    description: '',
    app_description: '',
  })

  const loadSuites = () => {
    setLoading(true)
    setError(null)
    suiteApi.list()
      .then(setSuites)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadSuites() }, [])

  const handleCreate = async () => {
    if (!form.name.trim() || !form.base_url.trim()) return
    setCreating(true)
    try {
      const suite = await suiteApi.create(form)
      setSuites(prev => [suite, ...prev])
      setShowCreate(false)
      setForm({ name: '', base_url: '', description: '', app_description: '' })
      navigate(`/suites/${suite.id}`)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (!confirm('Delete this test suite and all its test cases?')) return
    try {
      await suiteApi.delete(id)
      setSuites(prev => prev.filter(s => s.id !== id))
    } catch (e: any) {
      setError(e.message)
    }
  }

  if (loading) return <PageLoader />
  if (error) return <PageError message={error} onRetry={loadSuites} />

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Test Suites"
        description="Organize your tests into suites for different applications and features"
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4" />
            New Suite
          </Button>
        }
      />

      {suites.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No test suites yet"
          description="Create your first test suite to start automating your web application testing."
          action={
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4" />
              Create Suite
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {suites.map(suite => (
            <Card key={suite.id} hover onClick={() => navigate(`/suites/${suite.id}`)}>
              <CardContent>
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary-600/15 flex items-center justify-center">
                    <FolderKanban className="w-5 h-5 text-primary-400" />
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, suite.id)}
                    className="p-1.5 rounded-lg text-surface-500 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <h3 className="text-base font-semibold text-surface-100 mb-1">{suite.name}</h3>
                {suite.description && (
                  <p className="text-sm text-surface-400 line-clamp-2 mb-3">{suite.description}</p>
                )}
                <div className="flex items-center gap-1.5 text-xs text-surface-500">
                  <Globe className="w-3 h-3" />
                  <span className="truncate">{suite.base_url}</span>
                </div>
                <p className="text-xs text-surface-600 mt-2">
                  Updated {formatDistanceToNow(new Date(suite.updated_at), { addSuffix: true })}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Test Suite" size="md">
        <div className="space-y-4">
          <Input
            id="suite-name"
            label="Suite Name"
            placeholder="e.g. E-Commerce Checkout Tests"
            value={form.name}
            onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
          />
          <Input
            id="suite-url"
            label="Application URL"
            placeholder="https://example.com"
            value={form.base_url}
            onChange={e => setForm(prev => ({ ...prev, base_url: e.target.value }))}
          />
          <Textarea
            id="suite-desc"
            label="Description"
            placeholder="Brief description of what this suite tests..."
            rows={2}
            value={form.description}
            onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
          />
          <Textarea
            id="suite-app-desc"
            label="Application Description (for AI context)"
            placeholder="Describe the application so AI can better understand it..."
            rows={3}
            value={form.app_description}
            onChange={e => setForm(prev => ({ ...prev, app_description: e.target.value }))}
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button
              onClick={handleCreate}
              loading={creating}
              disabled={!form.name.trim() || !form.base_url.trim()}
            >
              Create Suite
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
