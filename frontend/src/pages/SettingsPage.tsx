export function SettingsPage() {
  return (
    <section>
      <h2>Settings and Ops</h2>
      <ul className="list">
        <li className="card">Single-user mode (V1): no auth stack enabled.</li>
        <li className="card">Data-at-rest encryption enabled for stored files and LLM payload fields.</li>
        <li className="card">Daily Canvas sync schedule is server-managed via APScheduler.</li>
        <li className="card">Encrypted backups are available through the backup API endpoint.</li>
      </ul>
    </section>
  )
}
