import { useEffect, useMemo, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { readLocalStorage, writeLocalStorage } from '../../utils/storage'

type NavItem = {
  to: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: 'DB' },
  { to: '/tasks', label: 'Tasks', icon: 'TK' },
  { to: '/canvas-sync', label: 'Canvas Sync', icon: 'CS' },
  { to: '/courses', label: 'Courses', icon: 'CR' },
  { to: '/students', label: 'Students', icon: 'ST' },
  { to: '/advising', label: 'Advising', icon: 'AD' },
  { to: '/attendance', label: 'Attendance', icon: 'AT' },
  { to: '/interactions', label: 'Interactions', icon: 'IN' },
  { to: '/rubrics', label: 'Rubrics', icon: 'RB' },
  { to: '/documents', label: 'Documents', icon: 'DC' },
  { to: '/llm', label: 'LLM Workbench', icon: 'AI' },
  { to: '/reports', label: 'Reports', icon: 'RP' },
  { to: '/settings', label: 'Settings', icon: 'SE' },
]

export function AppShell() {
  const navigate = useNavigate()

  const [collapsed, setCollapsed] = useState(false)
  const [density, setDensity] = useState<'comfortable' | 'compact'>(() => {
    const cached = readLocalStorage('gradebook-ui-density')
    return cached === 'compact' ? 'compact' : 'comfortable'
  })

  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')

  const commandItems = useMemo(
    () => [
      ...navItems.map((item) => ({ id: item.to, label: `Go to ${item.label}`, run: () => navigate(item.to) })),
      { id: 'cmd-new-task', label: 'Create new task', run: () => navigate('/tasks') },
      { id: 'cmd-new-interaction', label: 'Log interaction', run: () => navigate('/interactions') },
      { id: 'cmd-open-advising', label: 'Open advising meetings', run: () => navigate('/advising') },
      { id: 'cmd-open-docs', label: 'Open documents', run: () => navigate('/documents') },
    ],
    [navigate],
  )

  const filteredCommands = useMemo(() => {
    const query = paletteQuery.trim().toLowerCase()
    if (!query) return commandItems

    const studentJumpMatch = query.match(/^student\s+(\d+)$/)
    if (studentJumpMatch) {
      const studentId = studentJumpMatch[1]
      return [{ id: `student-${studentId}`, label: `Jump to student #${studentId}`, run: () => navigate(`/students/${studentId}`) }]
    }

    return commandItems.filter((item) => item.label.toLowerCase().includes(query))
  }, [commandItems, navigate, paletteQuery])

  useEffect(() => {
    writeLocalStorage('gradebook-ui-density', density)
  }, [density])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen((current) => !current)
      }
      if (event.key === 'Escape') {
        setPaletteOpen(false)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  function runCommand(index: number) {
    const command = filteredCommands[index]
    if (!command) return
    command.run()
    setPaletteOpen(false)
    setPaletteQuery('')
  }

  const layoutClasses = ['layout']
  if (collapsed) layoutClasses.push('sidebar-collapsed')
  if (density === 'compact') layoutClasses.push('density-compact')

  return (
    <div className={layoutClasses.join(' ')}>
      <aside className="sidebar">
        <div className="sidebar-top-row">
          <button className="sidebar-toggle" onClick={() => setCollapsed((value) => !value)}>
            {collapsed ? 'Expand' : 'Collapse'}
          </button>
          <button
            className="sidebar-toggle"
            onClick={() => setDensity((value) => (value === 'comfortable' ? 'compact' : 'comfortable'))}
            title="Toggle table density"
          >
            Density: {density === 'comfortable' ? 'Comfort' : 'Compact'}
          </button>
        </div>
        <h1>Jon&apos;s Gradebook</h1>
        <p className="subtitle">Single-user advising and grading workspace</p>
        <button className="sidebar-toggle" onClick={() => setPaletteOpen(true)} title="Command palette (Ctrl/Cmd+K)">
          Command Palette
        </button>
        <nav>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
              end={item.to === '/'}
              title={collapsed ? item.label : undefined}
            >
              <span className="nav-icon" aria-hidden>{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>

      {paletteOpen ? (
        <div className="command-palette-backdrop" onClick={() => setPaletteOpen(false)}>
          <div className="command-palette" onClick={(event) => event.stopPropagation()}>
            <input
              autoFocus
              placeholder="Type a command (or 'student <id>')"
              value={paletteQuery}
              onChange={(event) => setPaletteQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  runCommand(0)
                }
              }}
            />
            <ul className="list compact">
              {filteredCommands.slice(0, 9).map((command, index) => (
                <li key={command.id} className="card">
                  <button type="button" onClick={() => runCommand(index)} style={{ width: '100%', textAlign: 'left' }}>
                    {command.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  )
}
