import { NavLink, Outlet } from 'react-router'

import { cn } from '@/lib/utils'

const navItems: { to: string; label: string; end?: boolean }[] = [
  { to: '/', label: 'Live View', end: true },
  { to: '/config', label: 'Config' },
  { to: '/runs', label: 'Runs' },
  { to: '/errors', label: 'Errors' },
]

export function AppShell() {
  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[220px_1fr]">
      <aside className="border-b border-sidebar-border bg-sidebar px-4 py-6 md:border-b-0 md:border-r">
        <div className="mb-6 font-display text-lg font-bold tracking-wide text-primary">
          TradingZero
        </div>
        <nav aria-label="primary" className="flex gap-1 overflow-x-auto md:grid md:gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'block rounded-md px-3 py-2 text-sm whitespace-nowrap text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  isActive && 'border border-primary/30 bg-primary/10 text-foreground',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="min-w-0">
        <Outlet />
      </div>
    </div>
  )
}
