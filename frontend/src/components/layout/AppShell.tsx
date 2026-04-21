import { NavLink, Outlet } from 'react-router-dom'
import { useState } from 'react'

const navItems = [
  ['/', 'Dashboard'],
  ['/canvas-sync', 'Canvas Sync'],
  ['/courses', 'Courses'],
  ['/students', 'Students'],
  ['/advising', 'Advising'],
  ['/attendance', 'Attendance'],
  ['/interactions', 'Interactions'],
  ['/rubrics', 'Rubrics'],
  ['/documents', 'Documents'],
  ['/llm', 'LLM Workbench'],
  ['/reports', 'Reports'],
  ['/settings', 'Settings'],
] as const

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className={collapsed ? 'layout sidebar-collapsed' : 'layout'}>
      <aside className="sidebar">
        <button className="sidebar-toggle" onClick={() => setCollapsed((value) => !value)}>
          {collapsed ? 'Expand Menu' : 'Collapse Menu'}
        </button>
        <h1>Jon&apos;s Gradebook</h1>
        <p className="subtitle">Single-user advising and grading workspace</p>
        <nav>
          {navItems.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
              end={to === '/'}
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
