import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Bell, Check, ChevronLeft, ChevronRight, CircleSlash,
  Filter, LayoutDashboard, FileText, Activity, ShieldCheck,
  Shield, SlidersHorizontal, UserRound, LogOut, Search,
  Pencil, Plus, X,
} from 'lucide-react'
import {
  createUser,
  getCurrentUser,
  listUsers,
  suspendUser,
  unsuspendUser,
  updateUser,
} from '../services/auth.js'

const PAGE_SIZE = 8

function formatUser(user, currentUserId) {
  return {
    ...user,
    name: user.display_name || [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username,
    role: user.role === 'ADMIN' ? 'Administrator' : 'Employee',
    status: user.status === 'SUSPENDED' ? 'Suspended' : 'Active',
    lastLogin: user.last_login
      ? new Date(user.last_login).toLocaleString()
      : 'Never',
    self: user.id === currentUserId,
  }
}

function suspensionPreview(selection) {
  const now = Date.now()
  if (selection.duration === 'manual') return null
  if (selection.duration === '1-hour') return new Date(now + 60 * 60 * 1000)
  if (selection.duration === '24-hours') return new Date(now + 24 * 60 * 60 * 1000)
  if (selection.duration === '7-days') return new Date(now + 7 * 24 * 60 * 60 * 1000)

  const amount = Number(selection.customAmount)
  if (!Number.isInteger(amount) || amount < 1 || amount > 365) return null
  const multiplier = selection.customUnit === 'days' ? 24 * 60 * 60 * 1000 : 60 * 60 * 1000
  return new Date(now + amount * multiplier)
}

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
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const initialSection = searchParams.get('role') === 'Employee' ? 'EMPLOYEE' : 'ADMIN'
  const [section, setSection] = useState(initialSection)
  const [status, setStatus] = useState('All statuses')
  const [applied, setApplied] = useState({ search: '', status: 'All statuses' })
  const [page, setPage] = useState(1)
  const [dialog, setDialog] = useState(null)
  const [draft, setDraft] = useState({ name: '', email: '', role: 'Employee' })
  const [suspension, setSuspension] = useState({
    duration: 'manual',
    customAmount: '1',
    customUnit: 'hours',
    reason: '',
  })
  const [currentUserId, setCurrentUserId] = useState(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const visibleUsers = useMemo(() => users.map((user) => formatUser(user, currentUserId)), [users, currentUserId])
  const expiryPreview = dialog?.type === 'status' && dialog.user.status === 'Active'
    ? suspension.duration === 'manual' ? 'manual' : suspensionPreview(suspension)
    : null

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const currentUser = await getCurrentUser()
        if (!currentUser) {
          navigate('/', {
            replace: true,
            state: { from: `${location.pathname}${location.search}` },
          })
          return
        }
        if (currentUser.role !== 'ADMIN') {
          navigate('/employee/dashboard', { replace: true })
          return
        }

        const userData = await listUsers({
          search: applied.search,
          status: applied.status === 'All statuses' ? '' : applied.status.toUpperCase(),
          role: section,
          page,
          pageSize: PAGE_SIZE,
        })
        if (cancelled) return
        setUsers(userData.results || [])
        setTotal(userData.total ?? 0)
        setCurrentUserId(currentUser?.id ?? null)
      } catch (loadError) {
        if (loadError.status === 401) {
          navigate('/', {
            replace: true,
            state: { from: `${location.pathname}${location.search}` },
          })
          return
        }
        if (!cancelled) setError(loadError.message || 'Unable to load users.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [section, applied, page, location.pathname, location.search, navigate])

  function applyFilters() {
    setApplied({ search, status })
    setPage(1)
  }

  async function confirmAction() {
    if (!dialog) return
    setSaving(true)
    setError('')
    try {
      if (dialog.type === 'status') {
        if (dialog.user.status === 'Active') {
          const reason = suspension.reason.trim()
          if (!reason) {
            setError('Enter a reason for suspending this account.')
            return
          }
          const amount = Number(suspension.customAmount)
          if (suspension.duration === 'custom' && (!Number.isInteger(amount) || amount < 1 || amount > 365)) {
            setError('Custom duration must be between 1 and 365 hours or days.')
            return
          }

          const duration = suspension.duration === 'manual'
            ? {}
            : suspension.duration === '1-hour'
            ? { duration_hours: 1 }
            : suspension.duration === '24-hours'
              ? { duration_hours: 24 }
              : suspension.duration === '7-days'
                ? { duration_days: 7 }
                : suspension.customUnit === 'days'
                  ? { duration_days: amount }
                  : { duration_hours: amount }
          const result = await suspendUser(dialog.user.id, { ...duration, reason })
          const statusMatches = applied.status === 'All statuses' || result.user.status === applied.status.toUpperCase()
          setUsers((current) => statusMatches
            ? current.map((user) => user.id === dialog.user.id ? result.user : user)
            : current.filter((user) => user.id !== dialog.user.id))
          if (!statusMatches) setTotal((current) => Math.max(0, current - 1))
          setNotice(`${dialog.user.name}'s account has been suspended.`)
        } else {
          const result = await unsuspendUser(dialog.user.id)
          const statusMatches = applied.status === 'All statuses' || result.user.status === applied.status.toUpperCase()
          setUsers((current) => statusMatches
            ? current.map((user) => user.id === dialog.user.id ? result.user : user)
            : current.filter((user) => user.id !== dialog.user.id))
          if (!statusMatches) setTotal((current) => Math.max(0, current - 1))
          setNotice(`${dialog.user.name}'s account has been reactivated.`)
        }
      } else if (dialog.type === 'edit') {
        const result = await updateUser(dialog.user.id, {
          name: draft.name.trim(),
          email: draft.email.trim(),
          role: draft.role === 'Administrator' ? 'ADMIN' : 'EMPLOYEE',
        })
        if (result.role === section) {
          setUsers((current) => current.map((user) => user.id === dialog.user.id ? result : user))
        } else {
          setUsers((current) => current.filter((user) => user.id !== dialog.user.id))
          setTotal((current) => Math.max(0, current - 1))
        }
        setNotice('User details updated.')
      } else if (dialog.type === 'add') {
        const result = await createUser({
          name: draft.name.trim(),
          email: draft.email.trim(),
          role: draft.role === 'Administrator' ? 'ADMIN' : 'EMPLOYEE',
        })
        setNotice('User account created.')
        if (result.role === section) {
          setPage(1)
          const userData = await listUsers({
            search: applied.search,
            status: applied.status === 'All statuses' ? '' : applied.status.toUpperCase(),
            role: section,
            page: 1,
            pageSize: PAGE_SIZE,
          })
          setUsers(userData.results || [])
          setTotal(userData.total ?? 0)
        }
      }
      setDialog(null)
    } catch (actionError) {
      setError(actionError.message || 'Unable to update the account.')
    } finally {
      setSaving(false)
    }
  }

  function openEdit(user) {
    setDraft({ name: user.name, email: user.email, role: user.role })
    setDialog({ type: 'edit', user })
  }

  function openAdd() {
    setDraft({ name: '', email: '', role: 'Employee' })
    setDialog({ type: 'add' })
  }

  function openStatusDialog(user) {
    setError('')
    setSuspension({ duration: 'manual', customAmount: '1', customUnit: 'hours', reason: '' })
    setDialog({ type: 'status', user })
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
              onClick={() => navigate('/admin/security')}
              className="relative flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold text-emerald-800"
            >
              <Bell size={15} /> Notifications
            </button>

            <button
              type="button"
              onClick={() => navigate('/admin/profile')}
              className="flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs"
            >
              <UserRound size={15} /> Profile
            </button>

            <div className="hidden items-center gap-2 sm:flex">
              <span className="flex size-9 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-800">AD</span>
              <div className="text-xs">
                <p className="font-bold">Administrator</p>
                <p className="text-violet-800">Administrator</p>
              </div>
            </div>
          </div>
        </header>

        <section className="rounded-2xl bg-white p-4 shadow-sm sm:p-5">
          <div className="mb-4 flex flex-wrap gap-2 border-b border-slate-100 pb-3" role="tablist" aria-label="User role">
            {[
              ['ADMIN', 'Administrators'],
              ['EMPLOYEE', 'Employees'],
            ].map(([roleValue, label]) => (
              <button
                key={roleValue}
                type="button"
                role="tab"
                aria-selected={section === roleValue}
                onClick={() => {
                  setSection(roleValue)
                  setPage(1)
                }}
                className={`rounded-full px-4 py-2 text-xs font-semibold ${
                  section === roleValue
                    ? 'bg-emerald-700 text-white'
                    : 'border border-slate-200 text-slate-600 hover:bg-emerald-50'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

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
              Section
              <span className="mt-1 flex min-h-[38px] items-center rounded-xl border border-slate-200 px-3 py-2.5 text-xs font-normal text-slate-500">
                {section === 'ADMIN' ? 'Administrators' : 'Employees'}
              </span>
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

          {error && (
            <div role="alert" className="mb-3 flex items-center justify-between rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">
              <span>{error}</span>
              <button type="button" onClick={() => setError('')} aria-label="Dismiss error">
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
                {loading && (
                  <tr><td colSpan={5} className="px-4 py-10 text-center text-slate-500">Loading users...</td></tr>
                )}
                {!loading && error && users.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-slate-500">
                      Unable to load accounts. Use the filters or try again.
                      <button type="button" onClick={() => setApplied({ ...applied })} className="ml-2 font-semibold text-emerald-800 underline">
                        Retry
                      </button>
                    </td>
                  </tr>
                )}
                {!loading && visibleUsers.map((user) => (
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
                    <td className="px-2 py-2.5">
                      <Status value={user.status} />
                      {user.status === 'Suspended' && user.suspension_end && (
                        <span className="mt-1 block text-[10px] text-slate-500">
                          Until {new Date(user.suspension_end).toLocaleString()}
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5">{user.lastLogin}</td>
                    <td className="px-2 py-2.5">
                      {user.self ? (
                        <span className="rounded-full bg-slate-200 px-3 py-1.5 text-[10px] font-semibold text-slate-700">Your account</span>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          <button type="button" onClick={() => openEdit(user)} className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-3 py-1.5 font-semibold text-emerald-800 hover:bg-emerald-50">
                            <Pencil size={12} /> Edit User
                          </button>
                          {section === 'EMPLOYEE' && (
                            <button
                              type="button"
                              onClick={() => openStatusDialog(user)}
                              className={`inline-flex items-center gap-1 rounded-full border px-3 py-1.5 font-semibold ${
                                user.status === 'Active'
                                  ? 'border-red-200 text-red-700 hover:bg-red-50'
                                  : 'border-emerald-700 bg-emerald-700 text-white hover:bg-emerald-800'
                              }`}
                            >
                              {user.status === 'Active'
                                ? <><CircleSlash size={12} /> Suspend Account</>
                                : <><Check size={12} /> Reactivate Account</>}
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
                {!loading && !error && visibleUsers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-slate-500">No {section === 'ADMIN' ? 'administrators' : 'employees'} match these filters.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              Showing {total ? (page - 1) * PAGE_SIZE + 1 : 0}-{Math.min(page * PAGE_SIZE, total)} of {total} users
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
              <button type="button" disabled={loading || page === pageCount} onClick={() => setPage((current) => current + 1)} className="rounded-full border px-3 py-2 text-xs disabled:opacity-40">
                Next <ChevronRight size={13} className="inline" />
              </button>
            </div>
          </div>
        </section>

        <p className="mt-4 text-xs leading-relaxed text-slate-500">
          Account changes are saved securely and recorded in the audit trail.
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

            {error && (
              <div role="alert" className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">
                {error}
              </div>
            )}

            {error && (
              <div role="alert" className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-800">
                {error}
              </div>
            )}

            {dialog.type === 'status' ? (
              dialog.user.status === 'Active' ? (
                <div className="space-y-4">
                  <p className="text-sm leading-relaxed text-slate-600">
                    Suspend <span className="font-semibold text-slate-800">{dialog.user.name}</span> ({dialog.user.email})?
                  </p>
                  <label className="block text-sm font-medium">
                    Suspension duration
                    <select
                      value={suspension.duration}
                      onChange={(event) => setSuspension({ ...suspension, duration: event.target.value })}
                      className="mt-1 w-full rounded-xl border bg-white px-3 py-2.5 text-sm"
                    >
                      <option value="manual">Until manually reactivated</option>
                      <option value="1-hour">1 hour</option>
                      <option value="24-hours">24 hours</option>
                      <option value="7-days">7 days</option>
                      <option value="custom">Custom duration</option>
                    </select>
                  </label>
                  {suspension.duration === 'custom' && (
                    <div className="grid grid-cols-[1fr_1fr] gap-3">
                      <label className="block text-sm font-medium">
                        Duration
                        <input
                          type="number"
                          min="1"
                          max="365"
                          required
                          value={suspension.customAmount}
                          onChange={(event) => setSuspension({ ...suspension, customAmount: event.target.value })}
                          className="mt-1 w-full rounded-xl border px-3 py-2.5 text-sm"
                        />
                      </label>
                      <label className="block text-sm font-medium">
                        Unit
                        <select
                          value={suspension.customUnit}
                          onChange={(event) => setSuspension({ ...suspension, customUnit: event.target.value })}
                          className="mt-1 w-full rounded-xl border bg-white px-3 py-2.5 text-sm"
                        >
                          <option value="hours">Hours</option>
                          <option value="days">Days</option>
                        </select>
                      </label>
                    </div>
                  )}
                  <label className="block text-sm font-medium">
                    Reason
                    <textarea
                      required
                      maxLength={1000}
                      value={suspension.reason}
                      onChange={(event) => setSuspension({ ...suspension, reason: event.target.value })}
                      className="mt-1 min-h-20 w-full rounded-xl border px-3 py-2.5 text-sm"
                      placeholder="Enter the reason for this suspension"
                    />
                  </label>
                  <p className="rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-900">
                    {expiryPreview === 'manual'
                      ? 'Suspension remains in effect until manually reactivated.'
                      : `Suspension expires: ${expiryPreview ? expiryPreview.toLocaleString() : 'Enter a valid duration'}`}
                  </p>
                </div>
              ) : (
                <p className="text-sm leading-relaxed text-slate-600">
                  Reactivate <span className="font-semibold text-slate-800">{dialog.user.name}</span> ({dialog.user.email}) now? This will end the current suspension immediately.
                </p>
              )
            ) : (
              <form id="user-form" onSubmit={(event) => {
                event.preventDefault()
                void confirmAction()
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
                disabled={saving || (dialog.type === 'status' && dialog.user.status === 'Active' && !expiryPreview)}
                onClick={() => {
                  if (dialog.type === 'status') void confirmAction()
                  else document.getElementById('user-form')?.requestSubmit()
                }}
                className="rounded-full bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Confirm'}
              </button>
            </div>
          </section>
        </div>
      )}
    </main>
  )
}