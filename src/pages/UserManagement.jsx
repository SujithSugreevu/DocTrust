import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Bell, Check, ChevronLeft, ChevronRight, CircleSlash,
  Filter, LayoutDashboard, FileText, Activity, ShieldCheck,
  Shield, SlidersHorizontal, UserRound, LogOut, Search,
  Pencil, Plus, X,
} from 'lucide-react'

const initialUsers = [
  { id: 1, name: 'John Doe', email: 'john@example.com', role: 'Employee', status: 'Active', lastLogin: '20 Oct 2026' },
  { id: 2, name: 'Sara Smith', email: 'sara@example.com', role: 'Employee', status: 'Active', lastLogin: '20 Oct 2026' },
  { id: 3, name: 'Anna Green', email: 'anna@example.com', role: 'Employee', status: 'Suspended', lastLogin: '13 Oct 2026' },
  { id: 4, name: 'Tom Wilson', email: 'tom@example.com', role: 'Employee', status: 'Active', lastLogin: '19 Oct 2026' },
  { id: 5, name: 'Lisa White', email: 'lisa@example.com', role: 'Employee', status: 'Active', lastLogin: '19 Oct 2026' },
  { id: 6, name: 'David Lee', email: 'david@example.com', role: 'Employee', status: 'Active', lastLogin: '18 Oct 2026' },
  { id: 7, name: 'Emma Davis', email: 'emma@example.com', role: 'Employee', status: 'Active', lastLogin: '17 Oct 2026' },
  { id: 8, name: 'Admin User', email: 'admin@example.com', role: 'Administrator', status: 'Active', lastLogin: '20 Oct 2026', self: true },
  { id: 9, name: 'Ryan Clark', email: 'ryan@example.com', role: 'Employee', status: 'Active', lastLogin: '16 Oct 2026' },
  { id: 10, name: 'Mia Taylor', email: 'mia@example.com', role: 'Employee', status: 'Active', lastLogin: '15 Oct 2026' },
]

const navItems = [
  ['Dashboard', LayoutDashboard],
  ['User Management', UserRound],
  ['Document Overview', FileText],
  ['Activity Logs', Activity],
  ['Permission Audit', ShieldCheck],
  ['Security Monitoring', Shield],
  ['System Settings', SlidersHorizontal],
  ['Profile', UserRound],
  ['Logout', LogOut],
]

function AdminSidebar() {
  const navigate = useNavigate()
  const currentPath = window.location.pathname

  
const routes = {
  Dashboard: '/admin/dashboard',
  'User Management': '/admin/users',
  'Document Overview': '/admin/documents',
  'Activity Logs': '/admin/activity',
  'Permission Audit': '/admin/permissions',
  'Security Monitoring': '/admin/security',
  'System Settings': '/admin/settings',
  Profile: '/admin/profile',
  Logout: '/logout',
}

  return (
    <aside className="w-full shrink-0 bg-gradient-to-b from-[#07523f] to-[#00372b] p-4 text-white md:min-h-screen md:w-56">
      <div className="mb-5 flex items-center gap-2 px-2 text-lg font-bold">
        <ShieldCheck size={22} />
        DocTrust
      </div>

      <div className="mb-5 w-fit rounded-full bg-white/15 px-3 py-1 text-xs">
        <ShieldCheck size={13} className="mr-1 inline" />
        Administrator
      </div>

      <nav aria-label="Administrator navigation" className="grid grid-cols-2 gap-1 md:flex md:flex-col">
        {navItems.map(([label, Icon]) => {
          const target = routes[label]
          const active = target === currentPath

          return (
            <button
              type="button"
              key={label}
              aria-current={active ? 'page' : undefined}
              disabled={!target}
              onClick={() => target && navigate(target)}
              className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-left text-xs ${
                active
                  ? 'bg-emerald-700 font-semibold text-white'
                  : target
                    ? 'text-white/80 hover:bg-white/10'
                    : 'cursor-not-allowed text-white/50'
              }`}
            >
              <Icon size={15} />
              {label}
            </button>
          )
        })}
      </nav>
    </aside>
  )
}

function Status({ value }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-semibold ${
      value === 'Active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
    }`}>
      <span className="size-1.5 rounded-full bg-current" />
      {value}
    </span>
  )
}

export default function UserManagement() {
  const [searchParams] = useSearchParams()
  const [users, setUsers] = useState(initialUsers)
  const [search, setSearch] = useState('')
  const initialRole = searchParams.get('role') === 'Employee' ? 'Employee' : 'All roles'
  const [role, setRole] = useState(initialRole)
  const [status, setStatus] = useState('All statuses')
  const [applied, setApplied] = useState({ search: '', role: initialRole, status: 'All statuses' })
  const [page, setPage] = useState(1)
  const [dialog, setDialog] = useState(null)
  const [draft, setDraft] = useState({ name: '', email: '', role: 'Employee' })
  const [notice, setNotice] = useState('')

  const filteredUsers = useMemo(() => users.filter((user) => {
    const matchesSearch = `${user.name} ${user.email}`.toLowerCase().includes(applied.search.toLowerCase())
    const matchesRole = applied.role === 'All roles' || user.role === applied.role
    const matchesStatus = applied.status === 'All statuses' || user.status === applied.status
    return matchesSearch && matchesRole && matchesStatus
  }), [users, applied])

  const pageSize = 8
  const pageCount = Math.max(1, Math.ceil(filteredUsers.length / pageSize))
  const visibleUsers = filteredUsers.slice((page - 1) * pageSize, page * pageSize)

  function applyFilters() {
    setApplied({ search, role, status })
    setPage(1)
  }

  function confirmAction() {
    if (!dialog) return

    if (dialog.type === 'status') {
      setUsers((current) => current.map((user) =>
        user.id === dialog.user.id
          ? { ...user, status: user.status === 'Active' ? 'Suspended' : 'Active' }
          : user
      ))
      setNotice(`${dialog.user.name}'s account status was updated in this demo.`)
    }

    if (dialog.type === 'edit') {
      setUsers((current) => current.map((user) =>
        user.id === dialog.user.id
          ? { ...user, name: draft.name.trim(), email: draft.email.trim(), role: draft.role }
          : user
      ))
      setNotice('User details updated in this demo.')
    }

    if (dialog.type === 'add') {
      setUsers((current) => [
        ...current,
        {
          id: Math.max(0, ...current.map((user) => user.id)) + 1,
          name: draft.name.trim(),
          email: draft.email.trim(),
          role: draft.role,
          status: 'Active',
          lastLogin: 'Never',
        },
      ])
      setNotice('Sample user added to this demo.')
    }

    setDialog(null)
  }

  function openEdit(user) {
    setDraft({ name: user.name, email: user.email, role: user.role })
    setDialog({ type: 'edit', user })
  }

  function openAdd() {
    setDraft({ name: '', email: '', role: 'Employee' })
    setDialog({ type: 'add' })
  }

  return (
    <main className="min-h-screen bg-[#eafbf3] text-slate-800 md:flex">
      <AdminSidebar />

      <div className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">User Management</h1>
            <p className="mt-1 text-sm text-slate-500">View, search and manage registered accounts</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setNotice('You have 3 sample notifications in this demo.')}
              className="relative flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold text-emerald-800"
            >
              <Bell size={15} /> Notifications
              <span className="absolute -right-1 -top-1 rounded-full bg-red-500 px-1 text-[10px] text-white">3</span>
            </button>

            <button
              type="button"
              onClick={() => setNotice('Profile page has not been built yet.')}
              className="flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs"
            >
              <UserRound size={15} /> Profile
            </button>

            <div className="hidden items-center gap-2 sm:flex">
              <span className="flex size-9 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-800">AD</span>
              <div className="text-xs">
                <p className="font-bold">Admin User</p>
                <p className="text-violet-800">Administrator</p>
              </div>
            </div>
          </div>
        </header>

        <section className="rounded-2xl bg-white p-4 shadow-sm sm:p-5">
          <div className="mb-4 grid grid-cols-1 items-end gap-3 sm:grid-cols-2 xl:grid-cols-[2fr_1fr_1fr_auto_auto]">
            <label className="block text-xs font-semibold">
              Search Users
              <span className="mt-1 flex items-center gap-2 rounded-xl border border-slate-300 px-3 py-2.5">
                <Search size={16} className="text-slate-500" />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  onKeyDown={(event) => event.key === 'Enter' && applyFilters()}
                  placeholder="Search by name or email"
                  className="min-w-0 flex-1 text-xs font-normal outline-none"
                />
              </span>
            </label>

            <label className="block text-xs font-semibold">
              Role
              <select value={role} onChange={(event) => setRole(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-xs font-normal">
                <option>All roles</option>
                <option>Administrator</option>
                <option>Employee</option>
              </select>
            </label>

            <label className="block text-xs font-semibold">
              Status
              <select value={status} onChange={(event) => setStatus(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-xs font-normal">
                <option>All statuses</option>
                <option>Active</option>
                <option>Suspended</option>
              </select>
            </label>

            <button type="button" onClick={applyFilters} className="flex items-center justify-center gap-2 rounded-full border border-slate-200 px-4 py-2.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-50">
              <Filter size={14} /> Apply Filters
            </button>

            <button type="button" onClick={openAdd} className="flex items-center justify-center gap-2 rounded-full bg-emerald-700 px-4 py-2.5 text-xs font-semibold text-white hover:bg-emerald-800">
              <Plus size={15} /> Add User
            </button>
          </div>

          {notice && (
            <div role="status" className="mb-3 flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
              {notice}
              <button type="button" onClick={() => setNotice('')} aria-label="Dismiss message">
                <X size={15} />
              </button>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="px-2 py-3 font-medium">User</th>
                  <th className="px-2 py-3 font-medium">Role</th>
                  <th className="px-2 py-3 font-medium">Status</th>
                  <th className="px-2 py-3 font-medium">Last login</th>
                  <th className="px-2 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleUsers.map((user) => (
                  <tr key={user.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-2 py-2.5">
                      <div className="flex items-center gap-2.5">
                        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-[10px] font-bold text-emerald-800">
                          {user.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}
                        </span>
                        <span>
                          <span className="block font-semibold">{user.name}</span>
                          <span className="text-slate-500">{user.email}</span>
                        </span>
                      </div>
                    </td>
                    <td className="px-2 py-2.5">{user.role}</td>
                    <td className="px-2 py-2.5"><Status value={user.status} /></td>
                    <td className="whitespace-nowrap px-2 py-2.5">{user.lastLogin}</td>
                    <td className="px-2 py-2.5">
                      {user.self ? (
                        <span className="rounded-full bg-slate-200 px-3 py-1.5 text-[10px] font-semibold text-slate-700">Your account</span>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          <button type="button" onClick={() => openEdit(user)} className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-3 py-1.5 font-semibold text-emerald-800 hover:bg-emerald-50">
                            <Pencil size={12} /> Edit User
                          </button>
                          <button
                            type="button"
                            onClick={() => setDialog({ type: 'status', user })}
                            className={`inline-flex items-center gap-1 rounded-full border px-3 py-1.5 font-semibold ${
                              user.status === 'Active'
                                ? 'border-red-200 text-red-700 hover:bg-red-50'
                                : 'border-emerald-700 bg-emerald-700 text-white hover:bg-emerald-800'
                            }`}
                          >
                            {user.status === 'Active'
                              ? <><CircleSlash size={12} /> Suspend Account</>
                              : <><Check size={12} /> Reactivate</>}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {visibleUsers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-slate-500">No users match these filters.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              Showing {filteredUsers.length ? (page - 1) * pageSize + 1 : 0}-{Math.min(page * pageSize, filteredUsers.length)} of {filteredUsers.length} users
            </p>
            <div className="flex flex-wrap items-center gap-1">
              <button type="button" disabled={page === 1} onClick={() => setPage((current) => current - 1)} className="rounded-full border px-3 py-2 text-xs disabled:opacity-40">
                <ChevronLeft size={13} className="inline" /> Previous
              </button>
              {Array.from({ length: Math.min(pageCount, 5) }, (_, index) => {
                const pageNumber = index + 1
                return (
                  <button key={pageNumber} type="button" onClick={() => setPage(pageNumber)} className={`size-8 rounded-full border text-xs ${page === pageNumber ? 'border-emerald-700 bg-emerald-700 text-white' : 'border-slate-200 hover:bg-emerald-50'}`}>
                    {pageNumber}
                  </button>
                )
              })}
              <button type="button" disabled={page === pageCount} onClick={() => setPage((current) => current + 1)} className="rounded-full border px-3 py-2 text-xs disabled:opacity-40">
                Next <ChevronRight size={13} className="inline" />
              </button>
            </div>
          </div>
        </section>

        <p className="mt-4 text-xs leading-relaxed text-slate-500">
          This page uses sample data stored temporarily in the browser state.
          Real account changes, database persistence and audit logging require the backend.
        </p>
      </div>

      {dialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setDialog(null)
        }}>
          <section role="dialog" aria-modal="true" aria-labelledby="dialog-title" className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-start justify-between gap-3">
              <h2 id="dialog-title" className="text-lg font-bold">
                {dialog.type === 'status'
                  ? `${dialog.user.status === 'Active' ? 'Suspend' : 'Reactivate'} account?`
                  : dialog.type === 'add' ? 'Add User' : 'Edit User'}
              </h2>
              <button type="button" onClick={() => setDialog(null)} aria-label="Close dialog">
                <X size={19} />
              </button>
            </div>

            {dialog.type === 'status' ? (
              <p className="text-sm leading-relaxed text-slate-600">
                Are you sure you want to {dialog.user.status === 'Active' ? 'suspend' : 'reactivate'} {dialog.user.name}'s account? This is a frontend demo; no real account will be changed.
              </p>
            ) : (
              <form id="user-form" onSubmit={(event) => {
                event.preventDefault()
                confirmAction()
              }} className="space-y-4">
                <label className="block text-sm font-medium">
                  Full name
                  <input required value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} className="mt-1 w-full rounded-xl border px-3 py-2.5" />
                </label>
                <label className="block text-sm font-medium">
                  Email
                  <input required type="email" value={draft.email} onChange={(event) => setDraft({ ...draft, email: event.target.value })} className="mt-1 w-full rounded-xl border px-3 py-2.5" />
                </label>
                <label className="block text-sm font-medium">
                  Role
                  <select value={draft.role} onChange={(event) => setDraft({ ...draft, role: event.target.value })} className="mt-1 w-full rounded-xl border bg-white px-3 py-2.5">
                    <option>Employee</option>
                    <option>Administrator</option>
                  </select>
                </label>
              </form>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={() => setDialog(null)} className="rounded-full border px-4 py-2 text-sm">
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  if (dialog.type === 'status') confirmAction()
                  else document.getElementById('user-form')?.requestSubmit()
                }}
                className="rounded-full bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
              >
                Confirm
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  )
}