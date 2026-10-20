
import { useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  Bell,
  ChartNoAxesColumn,
  Eye,
  FileText,
  Folder,
  History,
  LockKeyhole,
  LogOut,
  Search,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  TriangleAlert,
  UserRound,
  Users,
  X,
  Check,
  CheckCheck,
  ExternalLink,
  Clock,
} from 'lucide-react'

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

const navigation = [
  { label: 'Dashboard', icon: ChartNoAxesColumn },
  { label: 'User Management', icon: Users },
  { label: 'Document Overview', icon: FileText },
  { label: 'Activity Logs', icon: Activity },
  { label: 'Permission Audit', icon: ShieldCheck },
  { label: 'Security Monitoring', icon: Shield },
  { label: 'System Settings', icon: SlidersHorizontal },
  { label: 'Profile', icon: UserRound },
  { label: 'Logout', icon: LogOut },
]

const stats = [
  { label: 'Registered Users', value: 152, icon: Users, color: 'blue', route: '/admin/users', description: 'Manage registered accounts' },
  { label: 'Total Documents', value: 486, icon: FileText, color: 'teal', route: '/admin/documents', description: 'Review document records' },
  { label: 'Document Owners', value: 48, icon: Folder, color: 'amber', route: '/admin/users', description: 'Find document owners' },
  { label: 'Viewers', value: 96, icon: Eye, color: 'purple', route: '/admin/users', description: 'Review viewer accounts' },
  { label: 'Administrators', value: 8, icon: Shield, color: 'rose', route: '/admin/users', description: 'Review administrator accounts' },
]

const activityByRange = {
  '7 days': [
    { day: 'Tue', value: 34 },
    { day: 'Wed', value: 48 },
    { day: 'Thu', value: 41 },
    { day: 'Fri', value: 62 },
    { day: 'Sat', value: 55 },
    { day: 'Sun', value: 29 },
    { day: 'Mon', value: 44 },
  ],
  '30 days': [
    { day: 'Week 1', value: 145 },
    { day: 'Week 2', value: 182 },
    { day: 'Week 3', value: 158 },
    { day: 'Week 4', value: 210 },
  ],
  '90 days': [
    { day: 'Month 1', value: 510 },
    { day: 'Month 2', value: 625 },
    { day: 'Month 3', value: 580 },
  ],
}

const initialActivities = [
  { id: 1, time: '20 Oct, 10:24', user: 'John Doe', action: 'Uploaded', document: 'Project_Report.pdf', result: 'Success', details: 'The document was uploaded successfully.', category: 'Document' },
  { id: 2, time: '20 Oct, 09:18', user: 'Sara Smith', action: 'Downloaded', document: 'Design_Specs.docx', result: 'Success', details: 'A permitted document download was recorded.', category: 'Document' },
  { id: 3, time: '19 Oct, 16:02', user: 'Mike Brown', action: 'Edited', document: 'Financial_Plan.xlsx', result: 'Success', details: 'The document was edited by an authorized user.', category: 'Document' },
  { id: 4, time: '19 Oct, 14:40', user: 'Anna Green', action: 'Viewed', document: 'Product_Manual.pdf', result: 'Denied', details: 'Access was denied because the user did not have permission.', category: 'Security' },
]

const permissionChanges = [
  { id: 1, document: 'Project_Report.pdf', status: 'Granted', permission: 'Read', user: 'Sara Smith', owner: 'John Doe', color: 'teal', time: '20 Oct, 10:15' },
  { id: 2, document: 'Design_Specs.docx', status: 'Updated', permission: 'Edit', user: 'Mike Brown', owner: 'John Doe', color: 'blue', time: '20 Oct, 09:40' },
  { id: 3, document: 'Financial_Plan.xlsx', status: 'Revoked', permission: 'Edit', user: 'Anna Green', owner: 'Mike Brown', color: 'rose', time: '19 Oct, 16:20' },
]

const initialNotifications = [
  { id: 1, title: 'Repeated failed login attempts', message: 'Five failed login attempts were detected for one account.', time: '10 minutes ago', read: false, route: '/admin/security' },
  { id: 2, title: 'Document access denied', message: 'A user attempted to open an unshared document.', time: '35 minutes ago', read: false, route: '/admin/security' },
  { id: 3, title: 'Permission updated', message: 'A document permission was changed.', time: '1 hour ago', read: false, route: '/admin/permissions' },
]

const initialAlerts = [
  { id: 1, title: 'Repeated failed login attempts', severity: 'High', status: 'Open', time: '20 Oct 2026, 09:15', details: 'Five unsuccessful login attempts were detected for the same account. Review the account activity and sign-in history.' },
  { id: 2, title: 'Access to an unshared file', severity: 'Medium', status: 'Review', time: '20 Oct 2026, 08:40', details: 'A user attempted to access a document without an applicable permission.' },
  { id: 3, title: 'Disallowed file type', severity: 'Medium', status: 'Review', time: '19 Oct 2026, 16:42', details: 'A file upload attempt used a file type that is not permitted in this demo.' },
]

function SectionCard({ title, icon: Icon, children, className = '' }) {
  return (
    <section className={`min-w-0 rounded-2xl bg-white p-4 shadow-sm sm:p-5 ${className}`}>
      <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-800">
        <Icon size={17} />
        {title}
      </h2>
      {children}
    </section>
  )
}

function StatusBadge({ children, color = 'teal' }) {
  const colors = {
    teal: 'bg-emerald-100 text-emerald-800',
    blue: 'bg-blue-100 text-blue-800',
    rose: 'bg-rose-100 text-rose-800',
    amber: 'bg-amber-100 text-amber-900',
  }

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-semibold ${colors[color] || colors.teal}`}>
      <span className="size-1.5 rounded-full bg-current" />
      {children}
    </span>
  )
}

function AdminSidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <aside className="flex w-full shrink-0 flex-col bg-gradient-to-b from-[#07523f] to-[#00372b] p-4 text-white md:min-h-screen md:w-56">
      <button
        type="button"
        onClick={() => navigate('/admin/dashboard')}
        className="mb-5 flex items-center gap-2 px-2 text-left"
      >
        <ShieldCheck size={23} />
        <span className="text-lg font-bold">DocTrust</span>
      </button>

      <div className="mb-5 w-fit rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
        <ShieldCheck size={13} className="mr-1 inline" />
        Administrator
      </div>

      <nav aria-label="Administrator navigation" className="grid grid-cols-2 gap-1 md:flex md:flex-col">
        {navigation.map(({ label, icon: Icon }) => {
          const target = routes[label]
          const active = target === location.pathname

          return (
            <button
              key={label}
              type="button"
              aria-current={active ? 'page' : undefined}
              onClick={() => navigate(target)}
              className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-left text-xs transition ${
                active
                  ? 'bg-emerald-700 font-semibold text-white'
                  : 'text-white/80 hover:bg-white/10 hover:text-white'
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

function DetailDialog({ title, data, onClose }) {
  if (!data) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="dashboard-dialog-title"
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 id="dashboard-dialog-title" className="text-lg font-bold">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close dialog" className="rounded-lg p-1 hover:bg-slate-100">
            <X size={19} />
          </button>
        </div>

        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="rounded-xl bg-slate-50 p-3">
              <dt className="text-xs capitalize text-slate-500">{key.replace(/([A-Z])/g, ' $1')}</dt>
              <dd className="mt-1 break-words text-sm font-semibold">{String(value)}</dd>
            </div>
          ))}
        </dl>

        <button type="button" onClick={onClose} className="mt-5 rounded-full bg-emerald-700 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-800">
          Close
        </button>
      </section>
    </div>
  )
}

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState(initialNotifications)
  const [notificationOpen, setNotificationOpen] = useState(false)
  const [range, setRange] = useState('7 days')
  const [activities] = useState(initialActivities)
  const [selectedActivity, setSelectedActivity] = useState(null)
  const [selectedPermission, setSelectedPermission] = useState(null)
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [notice, setNotice] = useState('')

  const unreadCount = useMemo(
    () => notifications.filter((item) => !item.read).length,
    [notifications],
  )

  const chartData = activityByRange[range]
  const maxChartValue = Math.max(...chartData.map((item) => item.value), 1)

  function markNotificationRead(id) {
    setNotifications((current) =>
      current.map((item) => item.id === id ? { ...item, read: true } : item),
    )
  }

  function openNotification(item) {
    markNotificationRead(item.id)
    setNotificationOpen(false)
    navigate(item.route)
  }

  function markAllNotificationsRead() {
    setNotifications((current) => current.map((item) => ({ ...item, read: true })))
    setNotice('All notifications have been marked as read in this demo.')
  }

  function openStat(stat) {
    if (stat.label === 'Document Owners') {
      navigate('/admin/users?role=Document%20Owner')
      return
    }

    if (stat.label === 'Viewers') {
      navigate('/admin/users?role=Viewer')
      return
    }

    if (stat.label === 'Administrators') {
      navigate('/admin/users?role=Administrator')
      return
    }

    navigate(stat.route)
  }

  return (
    <main className="min-h-screen bg-[#eafbf3] text-slate-800 md:flex">
      <AdminSidebar />

      <div className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
            <p className="mt-1 text-sm text-slate-500">Overview of system activity and security</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                type="button"
                aria-expanded={notificationOpen}
                aria-label={`Notifications, ${unreadCount} unread`}
                onClick={() => setNotificationOpen((open) => !open)}
                className="relative flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50"
              >
                <Bell size={15} />
                <span className="hidden sm:inline">Notifications</span>
                {unreadCount > 0 && (
                  <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white">
                    {unreadCount}
                  </span>
                )}
              </button>

              {notificationOpen && (
                <div className="absolute right-0 z-40 mt-3 w-[min(90vw,360px)] rounded-2xl border border-slate-100 bg-white p-3 shadow-xl">
                  <div className="mb-3 flex items-center justify-between gap-2 px-1">
                    <div>
                      <h2 className="text-sm font-bold">Notifications</h2>
                      <p className="text-xs text-slate-500">{unreadCount} unread</p>
                    </div>
                    <button
                      type="button"
                      onClick={markAllNotificationsRead}
                      disabled={unreadCount === 0}
                      className="text-xs font-semibold text-emerald-800 hover:underline disabled:opacity-40"
                    >
                      Mark all read
                    </button>
                  </div>

                  <div className="max-h-80 space-y-2 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <p className="px-3 py-8 text-center text-sm text-slate-500">You're all caught up.</p>
                    ) : (
                      notifications.map((item) => (
                        <button
                          type="button"
                          key={item.id}
                          onClick={() => openNotification(item)}
                          className={`w-full rounded-xl p-3 text-left transition hover:bg-emerald-50 ${item.read ? 'bg-white' : 'bg-emerald-50/70'}`}
                        >
                          <span className="flex items-start gap-2">
                            <span className={`mt-1.5 size-2 shrink-0 rounded-full ${item.read ? 'bg-slate-300' : 'bg-emerald-600'}`} />
                            <span className="min-w-0 flex-1">
                              <span className="block text-xs font-bold">{item.title}</span>
                              <span className="mt-1 block text-xs leading-relaxed text-slate-600">{item.message}</span>
                              <span className="mt-2 flex items-center gap-1 text-[10px] text-slate-400"><Clock size={11} /> {item.time}</span>
                            </span>
                            <ExternalLink size={13} className="shrink-0 text-slate-400" />
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            <button
              type="button"
              onClick={() => navigate('/admin/profile')}
              className="flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold hover:bg-emerald-50"
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

        {notice && (
          <div role="status" className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-white px-4 py-3 text-sm text-emerald-900">
            {notice}
            <button type="button" onClick={() => setNotice('')} aria-label="Dismiss message">
              <X size={16} />
            </button>
          </div>
        )}

        <section aria-label="System statistics" className="mb-4 grid grid-cols-2 gap-3 xl:grid-cols-5">
          {stats.map((stat) => {
            const Icon = stat.icon
            const iconColors = {
              blue: 'bg-blue-100 text-blue-800',
              teal: 'bg-emerald-100 text-emerald-800',
              amber: 'bg-amber-100 text-amber-900',
              purple: 'bg-purple-100 text-purple-800',
              rose: 'bg-rose-100 text-rose-800',
            }

            return (
              <button
                key={stat.label}
                type="button"
                onClick={() => openStat(stat)}
                title={stat.description}
                className="flex min-w-0 items-center gap-3 rounded-2xl bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-600"
              >
                <span className={`flex size-11 shrink-0 items-center justify-center rounded-xl ${iconColors[stat.color]}`}>
                  <Icon size={21} />
                </span>
                <span className="min-w-0">
                  <span className="block text-xs text-slate-500">{stat.label}</span>
                  <span className="block text-2xl font-bold tracking-tight">{stat.value}</span>
                  <span className="mt-1 block text-[10px] text-emerald-800">View details →</span>
                </span>
              </button>
            )
          })}
        </section>

        <div className="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-[1.65fr_1fr]">
          <SectionCard title={`Document Activity, ${range}`} icon={Activity}>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-slate-500">Sample activity counts for the selected period</p>
              <label className="flex items-center gap-2 text-xs font-semibold">
                Period
                <select
                  value={range}
                  onChange={(event) => setRange(event.target.value)}
                  className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs"
                >
                  <option>7 days</option>
                  <option>30 days</option>
                  <option>90 days</option>
                </select>
              </label>
            </div>

            <div className="flex h-44 items-end justify-around gap-3 border-b border-slate-200 px-2">
              {chartData.map(({ day, value }) => (
                <div key={day} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1">
                  <span className="text-xs font-semibold">{value}</span>
                  <div
                    className="w-full max-w-12 rounded-t-md bg-emerald-700 transition-all duration-300 hover:bg-emerald-500"
                    style={{ height: `${Math.max((value / maxChartValue) * 65, 5)}%` }}
                    title={`${value} sample activities`}
                  />
                  <span className="pb-2 text-center text-[10px] text-slate-500">{day}</span>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Security Alerts" icon={TriangleAlert}>
            <div className="space-y-4 text-xs">
              {initialAlerts.map((alert) => (
                <button
                  type="button"
                  key={alert.id}
                  onClick={() => setSelectedAlert(alert)}
                  className="flex w-full items-start gap-2 rounded-lg text-left hover:bg-slate-50"
                >
                  <StatusBadge color={alert.severity === 'High' ? 'rose' : 'amber'}>{alert.severity}</StatusBadge>
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold text-slate-800">{alert.title}</span>
                    <span className="mt-1 block text-slate-500">{alert.time}</span>
                  </span>
                  <Eye size={14} className="shrink-0 text-emerald-800" />
                </button>
              ))}

              <button
                type="button"
                onClick={() => navigate('/admin/security')}
                className="mt-2 rounded-full border border-emerald-100 px-3 py-2 font-semibold text-emerald-800 hover:bg-emerald-50"
              >
                <Search size={13} className="mr-1 inline" /> Investigate Events
              </button>
            </div>
          </SectionCard>
        </div>

        <SectionCard title="Recent Document Activities" icon={History} className="mb-4">
          <p className="mb-3 text-xs text-slate-500">Select a row to view its event details.</p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[650px] text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="px-2 py-3 font-medium">Time</th>
                  <th className="px-2 py-3 font-medium">User</th>
                  <th className="px-2 py-3 font-medium">Action</th>
                  <th className="px-2 py-3 font-medium">Document</th>
                  <th className="px-2 py-3 font-medium">Result</th>
                  <th className="px-2 py-3 font-medium">Details</th>
                </tr>
              </thead>
              <tbody>
                {activities.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedActivity(item)}
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        setSelectedActivity(item)
                      }
                    }}
                    className="cursor-pointer border-b border-slate-100 last:border-0 hover:bg-emerald-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-emerald-600"
                  >
                    <td className="whitespace-nowrap px-2 py-3">{item.time}</td>
                    <td className="px-2 py-3">{item.user}</td>
                    <td className="px-2 py-3">{item.action}</td>
                    <td className="px-2 py-3">
                      <span className="flex items-center gap-2 font-semibold">
                        <FileText size={16} className="text-emerald-700" /> {item.document}
                      </span>
                    </td>
                    <td className="px-2 py-3">
                      <StatusBadge color={item.result === 'Denied' ? 'rose' : 'teal'}>{item.result}</StatusBadge>
                    </td>
                    <td className="px-2 py-3">
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          setSelectedActivity(item)
                        }}
                        className="font-semibold text-emerald-800 hover:underline"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>

        <SectionCard title="Recent Permission Changes" icon={LockKeyhole}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="px-2 py-3 font-medium">Document</th>
                  <th className="px-2 py-3 font-medium">Change</th>
                  <th className="px-2 py-3 font-medium">Permission</th>
                  <th className="px-2 py-3 font-medium">Details</th>
                </tr>
              </thead>
              <tbody>
                {permissionChanges.map((item) => (
                  <tr key={item.id} className="border-b border-slate-100 last:border-0 hover:bg-emerald-50">
                    <td className="px-2 py-3">
                      <span className="flex items-center gap-2 font-medium">
                        <FileText size={16} className="text-emerald-700" /> {item.document}
                      </span>
                    </td>
                    <td className="px-2 py-3">
                      <StatusBadge color={item.color}>{item.status}</StatusBadge>
                    </td>
                    <td className="px-2 py-3">{item.permission}</td>
                    <td className="px-2 py-3">
                      <button
                        type="button"
                        onClick={() => setSelectedPermission(item)}
                        className="font-semibold text-emerald-800 hover:underline"
                      >
                        View details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            type="button"
            onClick={() => navigate('/admin/permissions')}
            className="mt-4 rounded-full border border-emerald-100 px-3 py-2 text-xs font-semibold text-emerald-800 hover:bg-emerald-50"
          >
            <ShieldCheck size={14} className="mr-1 inline" /> View Permission Audit
          </button>
        </SectionCard>

        <p className="mt-4 text-xs leading-relaxed text-slate-500">
          Frontend demo: dashboard data is sample data. Changes are held in component state and are not saved to a backend.
        </p>
      </div>

      <DetailDialog
        title="Activity Event Details"
        data={selectedActivity}
        onClose={() => setSelectedActivity(null)}
      />

      <DetailDialog
        title="Permission Change Details"
        data={selectedPermission}
        onClose={() => setSelectedPermission(null)}
      />

      <DetailDialog
        title="Security Alert Details"
        data={selectedAlert}
        onClose={() => setSelectedAlert(null)}
      />
    </main>
  )
}
