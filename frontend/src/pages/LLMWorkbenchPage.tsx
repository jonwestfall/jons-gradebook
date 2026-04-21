import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'

type RunSummary = {
  id: number
  provider: string
  model: string
  status: string
  created_at: string
}

type RunDetail = {
  id: number
  preview: string
  deidentify_map: Record<string, string>
  outputs: { output_id: number; output_text: string; edited_text?: string | null }[]
}

export function LLMWorkbenchPage() {
  const [provider, setProvider] = useState('openai')
  const [model, setModel] = useState('gpt-5-mini')
  const [prompt, setPrompt] = useState('')
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [selectedRun, setSelectedRun] = useState<RunDetail | null>(null)

  async function loadRuns() {
    setRuns(await api.get<RunSummary[]>('/llm/runs'))
  }

  async function preview(event: FormEvent) {
    event.preventDefault()
    const run = await api.post<{ run_id: number }>('/llm/preview', { provider, model, prompt })
    setPrompt('')
    await loadRuns()
    await openRun(run.run_id)
  }

  async function send(runId: number) {
    await api.post(`/llm/runs/${runId}/send`)
    await openRun(runId)
    await loadRuns()
  }

  async function openRun(runId: number) {
    setSelectedRun(await api.get<RunDetail>(`/llm/runs/${runId}`))
  }

  useEffect(() => {
    void loadRuns()
  }, [])

  return (
    <section>
      <h2>LLM Workbench</h2>
      <p>Preview is always de-identified before any provider call.</p>
      <form className="form" onSubmit={preview}>
        <select value={provider} onChange={(event) => setProvider(event.target.value)}>
          <option value="openai">OpenAI</option>
          <option value="ollama">Ollama</option>
          <option value="gemini">Gemini</option>
        </select>
        <input value={model} onChange={(event) => setModel(event.target.value)} placeholder="Model" required />
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Prompt" required />
        <button type="submit">Create Preview</button>
      </form>

      <div className="grid">
        <article className="card">
          <h3>Runs</h3>
          <ul className="list compact">
            {runs.map((run) => (
              <li key={run.id} className="card">
                <button onClick={() => openRun(run.id)}>Run #{run.id}</button>
                <div>
                  {run.provider} / {run.model}
                </div>
                <div>Status: {run.status}</div>
                <button onClick={() => send(run.id)}>Send</button>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>Preview + Output</h3>
          {selectedRun ? (
            <>
              <p>
                <strong>De-identified preview</strong>
              </p>
              <pre>{selectedRun.preview}</pre>
              <p>
                <strong>Replacement map</strong>
              </p>
              <pre>{JSON.stringify(selectedRun.deidentify_map, null, 2)}</pre>
              <p>
                <strong>Outputs</strong>
              </p>
              {selectedRun.outputs.map((output) => (
                <pre key={output.output_id}>{output.edited_text || output.output_text}</pre>
              ))}
            </>
          ) : (
            <p>Select a run to inspect preview and output.</p>
          )}
        </article>
      </div>
    </section>
  )
}
