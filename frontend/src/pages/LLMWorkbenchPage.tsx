import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type Student = { id: number; name: string; email?: string | null; student_number?: string | null }
type SourceDocument = {
  id: number
  title: string
  category: string
  document_type: string
  owner_id: number
  linked_student_ids: number[]
}
type Rubric = { id: number; name: string; description?: string | null; max_points?: number | null }
type ProviderTarget = { value: string; label: string; default_model: string; local: boolean }
type InstructionTemplate = {
  id: number
  name: string
  description?: string | null
  task_type: string
  instructions: string
  output_guidance?: string | null
  rubric_guidance?: string | null
  is_active: boolean
  is_default: boolean
  archived_at?: string | null
}
type RunDetail = {
  id: number
  preview: string
  deidentify_map: Record<string, string>
  outputs: { output_id: number; output_text: string; edited_text?: string | null }[]
}
type WorkbenchJob = {
  id: number
  student_profile_id: number
  student_name?: string | null
  source_document_id: number
  source_document_title?: string | null
  instruction_template_id: number
  instruction_template_name?: string | null
  rubric_id?: number | null
  rubric_name?: string | null
  final_document_id?: number | null
  final_document_title?: string | null
  provider: string
  model: string
  status: string
  final_feedback?: string | null
  metadata_json: Record<string, unknown>
  created_at?: string | null
  updated_at?: string | null
  run?: RunDetail | null
}
type Targets = {
  students: Student[]
  documents: SourceDocument[]
  rubrics: Rubric[]
  providers: ProviderTarget[]
}

const DEFAULT_TARGETS: Targets = { students: [], documents: [], rubrics: [], providers: [] }

function latestOutput(job: WorkbenchJob | null) {
  const outputs = job?.run?.outputs || []
  return outputs.length ? outputs[outputs.length - 1].edited_text || outputs[outputs.length - 1].output_text : ''
}

export function LLMWorkbenchPage() {
  const [targets, setTargets] = useState<Targets>(DEFAULT_TARGETS)
  const [templates, setTemplates] = useState<InstructionTemplate[]>([])
  const [jobs, setJobs] = useState<WorkbenchJob[]>([])
  const [selectedJob, setSelectedJob] = useState<WorkbenchJob | null>(null)
  const [studentId, setStudentId] = useState('')
  const [sourceMode, setSourceMode] = useState<'existing' | 'upload'>('upload')
  const [sourceDocumentId, setSourceDocumentId] = useState('')
  const [instructionTemplateId, setInstructionTemplateId] = useState('')
  const [rubricId, setRubricId] = useState('')
  const [provider, setProvider] = useState('ollama')
  const [model, setModel] = useState('llama3.1')
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [pastedOutput, setPastedOutput] = useState('')
  const [finalFeedback, setFinalFeedback] = useState('')
  const [templateDraft, setTemplateDraft] = useState<InstructionTemplate | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const activeTemplates = templates.filter((template) => template.archived_at === null || template.archived_at === undefined)
  const selectedStudent = targets.students.find((student) => String(student.id) === studentId)
  const selectedProvider = targets.providers.find((item) => item.value === provider)
  const studentDocuments = useMemo(() => {
    if (!studentId) return targets.documents
    const parsed = Number(studentId)
    return targets.documents.filter((document) => document.owner_id === parsed || document.linked_student_ids.includes(parsed))
  }, [studentId, targets.documents])

  async function loadAll() {
    const [targetPayload, templatePayload, jobPayload] = await Promise.all([
      api.get<Targets>('/llm/targets'),
      api.get<InstructionTemplate[]>('/llm/instructions'),
      api.get<WorkbenchJob[]>('/llm/workbench/jobs'),
    ])
    setTargets(targetPayload)
    setTemplates(templatePayload)
    setJobs(jobPayload)
    if (!instructionTemplateId && templatePayload.length) {
      const defaultTemplate = templatePayload.find((template) => template.is_default) || templatePayload[0]
      setInstructionTemplateId(String(defaultTemplate.id))
      setTemplateDraft(defaultTemplate)
    }
  }

  async function refreshJob(jobId: number) {
    const job = await api.get<WorkbenchJob>(`/llm/workbench/jobs/${jobId}`)
    setSelectedJob(job)
    setFinalFeedback(job.final_feedback || latestOutput(job))
    setPastedOutput('')
    const jobPayload = await api.get<WorkbenchJob[]>('/llm/workbench/jobs')
    setJobs(jobPayload)
  }

  async function handleCreateJob(event: FormEvent) {
    event.preventDefault()
    setError('')
    setMessage('')
    const data = new FormData()
    data.set('student_id', studentId)
    data.set('instruction_template_id', instructionTemplateId)
    data.set('provider', provider)
    data.set('model', model)
    if (rubricId) data.set('rubric_id', rubricId)
    if (title) data.set('title', title)
    if (sourceMode === 'existing') data.set('source_document_id', sourceDocumentId)
    if (sourceMode === 'upload' && file) data.set('file', file)
    try {
      const job = await api.post<WorkbenchJob>('/llm/workbench/jobs', data)
      setSelectedJob(job)
      setFinalFeedback('')
      setMessage('Workbench job created. Prepare the de-identified prompt when ready.')
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create workbench job')
    }
  }

  async function prepareJob() {
    if (!selectedJob) return
    setError('')
    try {
      const job = await api.post<WorkbenchJob>(`/llm/workbench/jobs/${selectedJob.id}/prepare`)
      setSelectedJob(job)
      setMessage('De-identified prompt is ready for review and copy/local send.')
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not prepare prompt')
    }
  }

  async function copyPrompt() {
    const prompt = selectedJob?.run?.preview || ''
    if (!prompt) return
    await navigator.clipboard?.writeText(prompt)
    setMessage('Prompt copied. Paste it into your chosen LLM, then paste the result back here.')
  }

  async function sendLocal() {
    if (!selectedJob) return
    setError('')
    try {
      await api.post(`/llm/workbench/jobs/${selectedJob.id}/send-local`)
      await refreshJob(selectedJob.id)
      setMessage('Local Ollama output saved in LLM history.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Local send failed')
    }
  }

  async function savePastedOutput() {
    if (!selectedJob || !pastedOutput.trim()) return
    setError('')
    try {
      await api.post(`/llm/workbench/jobs/${selectedJob.id}/paste-output`, { output_text: pastedOutput })
      await refreshJob(selectedJob.id)
      setMessage('Pasted output saved in LLM history.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save pasted output')
    }
  }

  async function saveFinalFeedback() {
    if (!selectedJob || !finalFeedback.trim()) return
    setError('')
    try {
      const job = await api.patch<WorkbenchJob>(`/llm/workbench/jobs/${selectedJob.id}/final-feedback`, { final_feedback: finalFeedback })
      setSelectedJob(job)
      setMessage('Final feedback draft saved.')
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save final feedback')
    }
  }

  async function finalizeJob() {
    if (!selectedJob) return
    setError('')
    try {
      const job = await api.post<WorkbenchJob>(`/llm/workbench/jobs/${selectedJob.id}/finalize`, {
        title: `${selectedJob.student_name || 'Student'} - Final Feedback`,
      })
      setSelectedJob(job)
      setMessage('Final feedback document saved to the student profile.')
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not finalize feedback')
    }
  }

  async function saveTemplate() {
    if (!templateDraft) return
    setError('')
    const payload = {
      name: templateDraft.name,
      description: templateDraft.description,
      task_type: templateDraft.task_type,
      instructions: templateDraft.instructions,
      output_guidance: templateDraft.output_guidance,
      rubric_guidance: templateDraft.rubric_guidance,
      is_active: templateDraft.is_active,
      is_default: templateDraft.is_default,
    }
    try {
      const saved = templateDraft.id
        ? await api.patch<InstructionTemplate>(`/llm/instructions/${templateDraft.id}`, payload)
        : await api.post<InstructionTemplate>('/llm/instructions', payload)
      setTemplateDraft(saved)
      setInstructionTemplateId(String(saved.id))
      setMessage('Instruction template saved.')
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save instruction template')
    }
  }

  async function duplicateTemplate() {
    if (!templateDraft?.id) return
    const copy = await api.post<InstructionTemplate>(`/llm/instructions/${templateDraft.id}/duplicate`)
    setTemplateDraft(copy)
    setInstructionTemplateId(String(copy.id))
    await loadAll()
  }

  async function archiveTemplate() {
    if (!templateDraft?.id) return
    await api.patch<InstructionTemplate>(`/llm/instructions/${templateDraft.id}`, { archived: true })
    setTemplateDraft(null)
    await loadAll()
  }

  useEffect(() => {
    void loadAll()
  }, [])

  useEffect(() => {
    const template = templates.find((item) => String(item.id) === instructionTemplateId)
    if (template) setTemplateDraft(template)
  }, [instructionTemplateId, templates])

  useEffect(() => {
    if (selectedProvider) setModel(selectedProvider.default_model)
  }, [provider])

  return (
    <section>
      <div className="page-heading">
        <div>
          <h2>Student Feedback Workbench</h2>
          <p className="subtitle">Upload or select student work, review a de-identified prompt, then save only the original and final instructor-approved feedback to the student file.</p>
        </div>
      </div>

      {message ? <p className="success">{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}

      <div className="llm-workbench-layout">
        <aside className="card llm-rail">
          <h3>New Workflow</h3>
          <form className="form" onSubmit={handleCreateJob}>
            <label>
              Student
              <select value={studentId} onChange={(event) => setStudentId(event.target.value)} required>
                <option value="">Select student</option>
                {targets.students.map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.name} {student.student_number ? `(${student.student_number})` : ''}
                  </option>
                ))}
              </select>
            </label>
            <div className="segmented-tabs full">
              <button type="button" className={sourceMode === 'upload' ? 'active' : ''} onClick={() => setSourceMode('upload')}>
                Upload
              </button>
              <button type="button" className={sourceMode === 'existing' ? 'active' : ''} onClick={() => setSourceMode('existing')}>
                Existing
              </button>
            </div>
            {sourceMode === 'upload' ? (
              <>
                <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Document title" />
                <input type="file" accept=".txt,.pdf,.docx,text/plain,application/pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} />
              </>
            ) : (
              <select value={sourceDocumentId} onChange={(event) => setSourceDocumentId(event.target.value)} required>
                <option value="">Select document</option>
                {studentDocuments.map((document) => (
                  <option key={document.id} value={document.id}>
                    {document.title} - {document.category}
                  </option>
                ))}
              </select>
            )}
            <select value={instructionTemplateId} onChange={(event) => setInstructionTemplateId(event.target.value)} required>
              <option value="">Instruction template</option>
              {activeTemplates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name}
                </option>
              ))}
            </select>
            <select value={rubricId} onChange={(event) => setRubricId(event.target.value)}>
              <option value="">No rubric context</option>
              {targets.rubrics.map((rubric) => (
                <option key={rubric.id} value={rubric.id}>
                  {rubric.name}
                </option>
              ))}
            </select>
            <div className="gradebook-toolbar compact-grid">
              <select value={provider} onChange={(event) => setProvider(event.target.value)}>
                {targets.providers.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              <input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Model" />
            </div>
            <button type="submit">Create Job</button>
          </form>

          <h3>Recent Jobs</h3>
          <ul className="list compact">
            {jobs.map((job) => (
              <li key={job.id} className={`card llm-job-card ${selectedJob?.id === job.id ? 'active' : ''}`}>
                <button type="button" onClick={() => refreshJob(job.id)}>
                  Job #{job.id}
                </button>
                <span>{job.student_name || `Student ${job.student_profile_id}`}</span>
                <small>{job.status.replace(/_/g, ' ')}</small>
              </li>
            ))}
          </ul>
        </aside>

        <main className="llm-main-flow">
          <article className="card">
            <div className="llm-step-header">
              <div>
                <h3>Prompt Preview</h3>
                <p className="subtitle">{selectedJob ? `${selectedJob.source_document_title || 'Source document'} using ${selectedJob.instruction_template_name}` : 'Create or select a job to begin.'}</p>
              </div>
              <div className="llm-actions">
                <button type="button" onClick={prepareJob} disabled={!selectedJob}>
                  Prepare Prompt
                </button>
                <button type="button" className="secondary-button" onClick={copyPrompt} disabled={!selectedJob?.run?.preview}>
                  Copy Prompt
                </button>
                <button type="button" className="secondary-button" onClick={sendLocal} disabled={!selectedJob?.run?.preview || selectedJob.provider !== 'ollama'}>
                  Run Ollama
                </button>
              </div>
            </div>
            <pre className="llm-prompt-preview">{selectedJob?.run?.preview || 'The de-identified prompt will appear here after preparation.'}</pre>
          </article>

          <article className="card">
            <h3>LLM Result</h3>
            <textarea
              value={pastedOutput}
              onChange={(event) => setPastedOutput(event.target.value)}
              placeholder="Paste the LLM result here, or run local Ollama after preparing the prompt."
            />
            <div className="llm-actions">
              <button type="button" onClick={savePastedOutput} disabled={!selectedJob || !pastedOutput.trim()}>
                Save Pasted Output
              </button>
            </div>
            {latestOutput(selectedJob) ? (
              <>
                <p className="subtitle">Latest saved output</p>
                <pre className="llm-output-preview">{latestOutput(selectedJob)}</pre>
              </>
            ) : null}
          </article>

          <article className="card">
            <h3>Final Instructor Feedback</h3>
            <textarea
              value={finalFeedback}
              onChange={(event) => setFinalFeedback(event.target.value)}
              placeholder="Edit the LLM output into final feedback. This is the text saved to the student profile."
            />
            <div className="llm-actions">
              <button type="button" onClick={() => setFinalFeedback(latestOutput(selectedJob))} disabled={!latestOutput(selectedJob)}>
                Use Latest Output
              </button>
              <button type="button" className="secondary-button" onClick={saveFinalFeedback} disabled={!selectedJob || !finalFeedback.trim()}>
                Save Draft
              </button>
              <button type="button" onClick={finalizeJob} disabled={!selectedJob || !finalFeedback.trim()}>
                Save Final Document
              </button>
            </div>
            {selectedJob?.final_document_id ? <p className="success">Saved as document #{selectedJob.final_document_id}: {selectedJob.final_document_title}</p> : null}
          </article>
        </main>

        <aside className="card llm-inspector">
          <h3>Inspector</h3>
          <div className="llm-inspector-grid">
            <strong>Default privacy mode</strong>
            <span>Local/copy first</span>
            <strong>Student</strong>
            <span>{selectedStudent?.name || selectedJob?.student_name || 'Not selected'}</span>
            <strong>Provider</strong>
            <span>{provider === 'ollama' ? 'Local Ollama' : `${provider} requires explicit review`}</span>
            <strong>Artifacts</strong>
            <span>Original + final only</span>
          </div>

          <h3>Replacement Map</h3>
          <pre className="llm-map-preview">{selectedJob?.run?.deidentify_map ? JSON.stringify(selectedJob.run.deidentify_map, null, 2) : '{}'}</pre>

          <h3>Instruction Template</h3>
          {templateDraft ? (
            <div className="form compact-form">
              <input value={templateDraft.name} onChange={(event) => setTemplateDraft({ ...templateDraft, name: event.target.value })} />
              <input value={templateDraft.task_type} onChange={(event) => setTemplateDraft({ ...templateDraft, task_type: event.target.value })} />
              <textarea value={templateDraft.instructions} onChange={(event) => setTemplateDraft({ ...templateDraft, instructions: event.target.value })} />
              <textarea
                value={templateDraft.output_guidance || ''}
                onChange={(event) => setTemplateDraft({ ...templateDraft, output_guidance: event.target.value })}
                placeholder="Output guidance"
              />
              <label className="inline-check">
                <input
                  type="checkbox"
                  checked={templateDraft.is_default}
                  onChange={(event) => setTemplateDraft({ ...templateDraft, is_default: event.target.checked })}
                />
                Default
              </label>
              <div className="llm-actions">
                <button type="button" onClick={saveTemplate}>
                  Save
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() =>
                    setTemplateDraft({
                      id: 0,
                      name: 'New Feedback Template',
                      task_type: 'feedback',
                      instructions: '',
                      output_guidance: '',
                      rubric_guidance: '',
                      is_active: true,
                      is_default: false,
                    })
                  }
                >
                  New
                </button>
                <button type="button" className="secondary-button" onClick={duplicateTemplate}>
                  Duplicate
                </button>
                <button type="button" className="danger-button" onClick={archiveTemplate}>
                  Archive
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() =>
                setTemplateDraft({
                  id: 0,
                  name: 'New Feedback Template',
                  task_type: 'feedback',
                  instructions: '',
                  output_guidance: '',
                  rubric_guidance: '',
                  is_active: true,
                  is_default: false,
                })
              }
            >
              New Template
            </button>
          )}
        </aside>
      </div>
    </section>
  )
}
