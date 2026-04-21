const modules = [
  'Canvas sync and historical snapshots',
  'Merged gradebook with local-first grading',
  'Student profile across classes',
  'Advising and interaction tracking',
  'Attendance with generated meeting dates',
  'Rubrics/checklists/scoring guides',
  'Document storage with extraction + versioning',
  'De-identified LLM workflow',
  'Branded PDF and PNG student reports',
  'Encrypted backups',
]

export function DashboardPage() {
  return (
    <section>
      <h2>Overview</h2>
      <p>
        Jon&apos;s Gradebook is a single-user workspace for teaching, advising, documentation, and AI-assisted analysis.
      </p>
      <div className="grid">
        {modules.map((module) => (
          <article key={module} className="card">
            <h3>{module}</h3>
          </article>
        ))}
      </div>
    </section>
  )
}
