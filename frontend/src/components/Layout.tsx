import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/', label: '总览', end: true },
  { to: '/opportunities', label: '机会' },
  { to: '/import', label: '导入' },
  { to: '/holdings', label: '持仓' },
  { to: '/signals', label: '信号' },
  { to: '/analysis', label: '分析' },
  { to: '/settings', label: '设置' },
]

export default function Layout() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">基金量化助手</h1>
            <p className="text-sm text-slate-500">Portfolio overview & signals</p>
          </div>
          <nav className="flex flex-wrap gap-1">
            {navItems.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  [
                    'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                  ].join(' ')
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
