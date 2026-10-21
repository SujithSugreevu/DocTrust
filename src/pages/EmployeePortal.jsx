import { useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Activity, Bell, Check, Clock3, Database, Download, Eye, FileText, Filter,
  Folder, History, LockKeyhole, LogOut, Pencil, Plus, Search, Settings2,
  Share2, ShieldCheck, SlidersHorizontal, Trash2, Upload, UserRound, X,
} from 'lucide-react'

const initialDocuments = [
  { id: 1, name: 'Project_Report.pdf', category: 'Reports', type: 'PDF', size: '2.4 MB', modified: '20 Oct 2026', owner: 'John Doe', folder: 'Reports', description: 'Quarterly project report and status.' },
  { id: 2, name: 'Design_Specs.docx', category: 'Design', type: 'DOCX', size: '1.1 MB', modified: '19 Oct 2026', owner: 'John Doe', folder: 'Projects', description: 'Current product design specifications.' },
  { id: 3, name: 'Financial_Plan.xlsx', category: 'Finance', type: 'XLSX', size: '856 KB', modified: '18 Oct 2026', owner: 'John Doe', folder: 'Finance', description: 'Annual financial plan.' },
  { id: 4, name: 'Marketing_Strategy.pdf', category: 'Marketing', type: 'PDF', size: '3.2 MB', modified: '17 Oct 2026', owner: 'John Doe', folder: 'Projects', description: 'Marketing strategy and launch plan.' },
  { id: 5, name: 'Product_Manual.pdf', category: 'Documents', type: 'PDF', size: '4.1 MB', modified: '16 Oct 2026', owner: 'John Doe', folder: 'Documents', description: 'Product usage manual.' },
  { id: 6, name: 'HR_Policy.docx', category: 'HR', type: 'DOCX', size: '420 KB', modified: '15 Oct 2026', owner: 'John Doe', folder: 'HR', description: 'Company HR policy.' },
  { id: 7, name: 'Q3_Review.pptx', category: 'Projects', type: 'PPTX', size: '6.8 MB', modified: '14 Oct 2026', owner: 'John Doe', folder: 'Projects', description: 'Quarterly review slides.' },
  { id: 8, name: 'Vendor_Contract.pdf', category: 'Legal', type: 'PDF', size: '1.9 MB', modified: '13 Oct 2026', owner: 'John Doe', folder: 'Documents', description: 'Vendor service agreement.' },
  { id: 9, name: 'Team_Guidelines.docx', category: 'HR', type: 'DOCX', size: '620 KB', modified: '12 Oct 2026', owner: 'Sara Smith', folder: 'HR', description: 'Shared team guidelines.' },
  { id: 10, name: 'Brand_Assets.pdf', category: 'Design', type: 'PDF', size: '1.5 MB', modified: '11 Oct 2026', owner: 'Mike Brown', folder: 'Design', description: 'Brand assets shared with you.' },
  { id: 11, name: 'Operations_Plan.xlsx', category: 'Projects', type: 'XLSX', size: '980 KB', modified: '10 Oct 2026', owner: 'John Doe', folder: 'Projects', description: 'Operations planning workbook.' },
  { id: 12, name: 'Security_Overview.pdf', category: 'Documents', type: 'PDF', size: '2.0 MB', modified: '09 Oct 2026', owner: 'Sara Smith', folder: 'Documents', description: 'Security overview shared with you.' },
  { id: 13, name: 'Client_Proposal.pdf', category: 'Reports', type: 'PDF', size: '2.7 MB', modified: '08 Oct 2026', owner: 'John Doe', folder: 'Reports', description: 'Proposal for the next client engagement.' },
  { id: 14, name: 'Product_Roadmap.pptx', category: 'Projects', type: 'PPTX', size: '5.4 MB', modified: '07 Oct 2026', owner: 'John Doe', folder: 'Projects', description: 'Product roadmap and release milestones.' },
  { id: 15, name: 'Invoice_October.xlsx', category: 'Finance', type: 'XLSX', size: '540 KB', modified: '06 Oct 2026', owner: 'John Doe', folder: 'Finance', description: 'October invoice summary.' },
  { id: 16, name: 'Employee_Handbook.pdf', category: 'HR', type: 'PDF', size: '3.8 MB', modified: '05 Oct 2026', owner: 'John Doe', folder: 'HR', description: 'Employee handbook and workplace policies.' },
  { id: 17, name: 'Campaign_Brief.docx', category: 'Marketing', type: 'DOCX', size: '710 KB', modified: '04 Oct 2026', owner: 'John Doe', folder: 'Projects', description: 'Brief for the upcoming campaign.' },
  { id: 18, name: 'Architecture_Notes.pdf', category: 'Design', type: 'PDF', size: '1.2 MB', modified: '03 Oct 2026', owner: 'John Doe', folder: 'Design', description: 'Application architecture notes.' },
  { id: 19, name: 'Annual_Budget.xlsx', category: 'Finance', type: 'XLSX', size: '1.4 MB', modified: '02 Oct 2026', owner: 'John Doe', folder: 'Finance', description: 'Annual department budget.' },
  { id: 20, name: 'Service_Agreement.pdf', category: 'Legal', type: 'PDF', size: '2.1 MB', modified: '01 Oct 2026', owner: 'John Doe', folder: 'Documents', description: 'Service agreement with a business partner.' },
  { id: 21, name: 'Release_Checklist.docx', category: 'Projects', type: 'DOCX', size: '380 KB', modified: '30 Sep 2026', owner: 'John Doe', folder: 'Projects', description: 'Checklist for the upcoming release.' },
  { id: 22, name: 'Brand_Guidelines.pdf', category: 'Marketing', type: 'PDF', size: '4.6 MB', modified: '29 Sep 2026', owner: 'John Doe', folder: 'Design', description: 'Brand guidelines and usage standards.' },
  { id: 23, name: 'Hiring_Plan.xlsx', category: 'HR', type: 'XLSX', size: '620 KB', modified: '28 Sep 2026', owner: 'John Doe', folder: 'HR', description: 'Hiring plan and staffing forecast.' },
  { id: 24, name: 'Research_Summary.docx', category: 'Reports', type: 'DOCX', size: '890 KB', modified: '27 Sep 2026', owner: 'John Doe', folder: 'Reports', description: 'Summary of recent product research.' },
  { id: 25, name: 'Risk_Register.xlsx', category: 'Projects', type: 'XLSX', size: '760 KB', modified: '26 Sep 2026', owner: 'John Doe', folder: 'Projects', description: 'Project risks, owners and mitigations.' },
  { id: 26, name: 'Onboarding_Guide.pdf', category: 'HR', type: 'PDF', size: '2.3 MB', modified: '25 Sep 2026', owner: 'John Doe', folder: 'HR', description: 'New employee onboarding guide.' },
  { id: 27, name: 'Compliance_Review.pdf', category: 'Legal', type: 'PDF', size: '1.7 MB', modified: '24 Sep 2026', owner: 'John Doe', folder: 'Documents', description: 'Compliance review and follow-up notes.' },
]

const initialShares = [
  { id: 1, documentId: 1, recipient: 'Sara Smith', email: 'sara@example.com', permission: 'Read', date: '20 Oct 2026', status: 'Active', expiry: '' },
  { id: 2, documentId: 1, recipient: 'Mike Brown', email: 'mike@example.com', permission: 'Edit', date: '18 Oct 2026', status: 'Active', expiry: '' },
  { id: 3, documentId: 2, recipient: 'Lisa White', email: 'lisa@example.com', permission: 'Download', date: '16 Oct 2026', status: 'Active', expiry: '' },
  { id: 4, documentId: 3, recipient: 'Tom Wilson', email: 'tom@example.com', permission: 'Read', date: '10 Oct 2026', status: 'Revoked', expiry: '' },
  { id: 5, documentId: 4, recipient: 'Sara Smith', email: 'sara@example.com', permission: 'Read', date: '09 Oct 2026', status: 'Active', expiry: '' },
  { id: 6, documentId: 5, recipient: 'Mike Brown', email: 'mike@example.com', permission: 'Download', date: '08 Oct 2026', status: 'Active', expiry: '' },
  { id: 7, documentId: 7, recipient: 'Lisa White', email: 'lisa@example.com', permission: 'Read', date: '07 Oct 2026', status: 'Active', expiry: '' },
  { id: 8, documentId: 8, recipient: 'Tom Wilson', email: 'tom@example.com', permission: 'Edit', date: '06 Oct 2026', status: 'Active', expiry: '' },
  { id: 9, documentId: 11, recipient: 'Sara Smith', email: 'sara@example.com', permission: 'Read', date: '05 Oct 2026', status: 'Active', expiry: '' },
  { id: 10, documentId: 13, recipient: 'Mike Brown', email: 'mike@example.com', permission: 'Read', date: '04 Oct 2026', status: 'Active', expiry: '' },
  { id: 11, documentId: 14, recipient: 'Lisa White', email: 'lisa@example.com', permission: 'Download', date: '03 Oct 2026', status: 'Active', expiry: '' },
  { id: 12, documentId: 15, recipient: 'Tom Wilson', email: 'tom@example.com', permission: 'Read', date: '02 Oct 2026', status: 'Active', expiry: '' },
  { id: 13, documentId: 16, recipient: 'Sara Smith', email: 'sara@example.com', permission: 'Read', date: '01 Oct 2026', status: 'Active', expiry: '' },
]

const initialActivity = [
  { id: 1, timestamp: '20 Oct 2026, 10:24', user: 'John Doe', action: 'Uploaded', documentId: 1, details: 'File uploaded (2.4 MB)', result: 'Success' },
  { id: 2, timestamp: '20 Oct 2026, 09:18', user: 'Sara Smith', action: 'Downloaded', documentId: 1, details: 'Downloaded file', result: 'Success' },
  { id: 3, timestamp: '19 Oct 2026, 16:36', user: 'Mike Brown', action: 'Edited', documentId: 2, details: 'Updated content', result: 'Success' },
  { id: 4, timestamp: '19 Oct 2026, 14:12', user: 'John Doe', action: 'Permission changed', documentId: 1, details: 'Read to Edit for Mike Brown', result: 'Success' },
  { id: 5, timestamp: '18 Oct 2026, 11:45', user: 'Tom Wilson', action: 'Viewed', documentId: 4, details: 'No permission', result: 'Denied' },
  { id: 6, timestamp: '18 Oct 2026, 09:30', user: 'Lisa White', action: 'Viewed', documentId: 6, details: 'Viewed document', result: 'Success' },
  { id: 7, timestamp: '17 Oct 2026, 15:05', user: 'John Doe', action: 'Deleted', documentId: 5, details: 'Moved out of folder Documents', result: 'Success' },
  { id: 8, timestamp: '16 Oct 2026, 12:20', user: 'Sara Smith', action: 'Downloaded', documentId: 2, details: 'Downloaded file', result: 'Success' },
]

const navItems = [
  ['Dashboard', '/employee/dashboard', Activity],
  ['My Documents', '/employee/documents', FileText],
  ['Upload Document', '/employee/upload', Upload],
  ['Folders & Categories', '/employee/folders', Folder],
  ['Shared with Me', '/employee/received', Eye],
  ['Shared by Me', '/employee/shared', Share2],
  ['Manage Permissions', '/employee/permissions', LockKeyhole],
  ['Activity History', '/employee/activity', History],
  ['Profile', '/employee/profile', UserRound],
  ['Logout', '/employee/logout', LogOut],
]
const categories = ['Reports', 'Design', 'Finance', 'Marketing', 'Documents', 'HR', 'Projects', 'Legal']
const pageTitles = {
  dashboard: ['Dashboard', 'Your documents, sharing and recent activity'],
  documents: ['My Documents', 'Documents you own'],
  upload: ['Upload Document', 'Add a new document securely'],
  folders: ['Folders & Categories', 'Organize documents. Permissions stay on each document.'],
  received: ['Shared with Me', 'Documents other employees have shared with you'],
  shared: ['Shared by Me', 'Who has access to your documents'],
  permissions: ['Manage Permissions', 'Control who can access your document'],
  activity: ['Activity History', 'Activity on your own documents'],
  profile: ['Profile', 'Your account and security'],
  logout: ['Dashboard', 'Overview'],
}

function ActionButton({ children, onClick, variant = 'outline', className = '', type = 'button', disabled = false }) {
  const styles = variant === 'primary'
    ? 'border-emerald-700 bg-emerald-700 text-white hover:bg-emerald-800'
    : variant === 'danger'
      ? 'border-rose-200 text-rose-700 hover:bg-rose-50'
      : 'border-slate-200 bg-white text-emerald-800 hover:bg-emerald-50'
  return <button type={type} disabled={disabled} onClick={onClick} className={`inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full border px-3.5 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}>{children}</button>
}

function Panel({ children, className = '' }) {
  return <section className={`min-w-0 rounded-2xl bg-white p-4 shadow-[0_6px_20px_rgba(25,79,57,0.07)] sm:p-5 ${className}`}>{children}</section>
}

function Field({ label, children, className = '' }) {
  return <label className={`block min-w-0 text-xs font-semibold text-slate-700 ${className}`}><span className="mb-1.5 block">{label}</span>{children}</label>
}

function TextInput({ className = '', ...props }) {
  return <input {...props} className={`w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100 ${className}`} />
}

function SelectInput({ className = '', children, ...props }) {
  return <select {...props} className={`w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100 ${className}`}>{children}</select>
}

function Badge({ children, tone = 'green' }) {
  const color = tone === 'red' ? 'bg-rose-100 text-rose-800' : tone === 'blue' ? 'bg-blue-100 text-blue-800' : tone === 'purple' ? 'bg-violet-100 text-violet-800' : tone === 'amber' ? 'bg-amber-100 text-amber-900' : 'bg-emerald-100 text-emerald-800'
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-semibold ${color}`}><span className="size-1.5 rounded-full bg-current" />{children}</span>
}

function Modal({ title, children, onClose, width = 'max-w-lg' }) {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section role="dialog" aria-modal="true" aria-label={title} className={`w-full ${width} rounded-2xl bg-white p-5 shadow-2xl sm:p-6`}><header className="mb-4 flex items-center justify-between gap-3"><h2 className="text-lg font-bold text-slate-800">{title}</h2><button type="button" onClick={onClose} aria-label="Close dialog" className="rounded-full p-1.5 text-slate-500 hover:bg-slate-100"><X size={18} /></button></header>{children}</section></div>
}

function formatDate() {
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date())
}

function formatFileSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function EmployeePortal() {
  const navigate = useNavigate()
  const location = useLocation()
  const fileInput = useRef(null)
  const page = location.pathname.split('/')[2] || 'dashboard'
  const [documents, setDocuments] = useState(initialDocuments)
  const [shares, setShares] = useState(initialShares)
  const [activity, setActivity] = useState(initialActivity)
  const [folders, setFolders] = useState(['Reports', 'Finance', 'HR', 'Projects', 'Design', 'Documents'])
  const [notifications, setNotifications] = useState([
    { id: 1, message: 'You granted Read access to sara@example.com on Project_Report.pdf', read: false },
    { id: 2, message: 'Edit access changed for mike@example.com on Design_Specs.docx', read: false },
    { id: 3, message: 'Access revoked for lisa@example.com on Financial_Plan.xlsx', read: false },
  ])
  const [notificationOpen, setNotificationOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const [query, setQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('All categories')
  const [dateFilter, setDateFilter] = useState('')
  const [appliedFilters, setAppliedFilters] = useState({ query: '', category: 'All categories', date: '' })
  const [pageNumber, setPageNumber] = useState(1)
  const [moreActions, setMoreActions] = useState(null)
  const [modal, setModal] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [upload, setUpload] = useState({ name: '', category: 'Reports', description: '' })
  const [selectedDocumentId, setSelectedDocumentId] = useState(1)
  const [profile, setProfile] = useState({ name: 'John Doe', email: 'john@example.com' })
  const [profileDraft, setProfileDraft] = useState(profile)
  const [password, setPassword] = useState({ current: '', next: '', confirm: '' })
  const [passwordVisible, setPasswordVisible] = useState(false)
  const [activityFilters, setActivityFilters] = useState({ query: '', action: 'All actions', document: 'All documents', date: '' })
  const [sharedFilters, setSharedFilters] = useState({ query: '', recipient: 'All recipients', permission: 'All' })

  const title = pageTitles[page] || pageTitles.dashboard
  const ownedDocuments = documents.filter((document) => document.owner === profile.name)
  const currentDocument = documents.find((document) => document.id === Number(selectedDocumentId)) || ownedDocuments[0]
  const unreadCount = notifications.filter((item) => !item.read).length

  function record(action, document, details = action, user = profile.name) {
    setActivity((current) => [{ id: Date.now(), timestamp: `${formatDate()}, ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`, user, action, documentId: document?.id ?? null, details, result: 'Success' }, ...current])
  }

  function openPreview(document) {
    record('Viewed', document, 'Viewed document')
    setModal({ type: 'preview', document })
  }

  function applyDocumentFilters(event) {
    event.preventDefault()
    setAppliedFilters({ query, category: categoryFilter, date: dateFilter })
    setPageNumber(1)
  }

  function downloadDocument(document) {
    const blob = new Blob([`${document.name}\n\n${document.description || 'DocTrust sample document.'}`], { type: 'text/plain' })
    const href = URL.createObjectURL(blob)
    const anchor = window.document.createElement('a')
    anchor.href = href
    anchor.download = document.name
    anchor.click()
    URL.revokeObjectURL(href)
    record('Downloaded', document, 'Downloaded file')
    setNotice(`${document.name} downloaded.`)
  }

  function selectUploadFile(file) {
    if (!file) return
    const extension = file.name.split('.').pop()?.toUpperCase()
    if (!['PDF', 'DOCX', 'XLSX', 'PPTX'].includes(extension)) {
      setNotice('This file type is not allowed. Choose PDF, DOCX, XLSX or PPTX.')
      setSelectedFile(null)
      return
    }
    if (file.size > 50 * 1024 * 1024) {
      setNotice('The maximum upload size is 50 MB.')
      setSelectedFile(null)
      return
    }
    setSelectedFile(file)
    setUpload((current) => ({ ...current, name: current.name || file.name.replace(/\.[^.]+$/, '') }))
    setNotice('')
  }

  function submitUpload(event) {
    event.preventDefault()
    if (!selectedFile) {
      setNotice('Select a file before uploading.')
      return
    }
    if (!upload.name.trim()) {
      setNotice('Enter a document name.')
      return
    }
    const id = Math.max(0, ...documents.map((document) => document.id)) + 1
    const extension = selectedFile.name.split('.').pop().toLowerCase()
    const documentName = upload.name.trim().toLowerCase().endsWith(`.${extension}`)
      ? upload.name.trim()
      : `${upload.name.trim()}.${extension}`
    const document = { id, name: documentName, category: upload.category, type: extension.toUpperCase(), size: formatFileSize(selectedFile.size), modified: formatDate(), owner: profile.name, folder: upload.category, description: upload.description }
    setDocuments((current) => [document, ...current])
    setFolders((current) => current.includes(upload.category) ? current : [...current, upload.category])
    record('Uploaded', document, `File uploaded (${document.size})`)
    setSelectedFile(null)
    setUpload({ name: '', category: 'Reports', description: '' })
    if (fileInput.current) fileInput.current.value = ''
    setNotice(`${document.name} uploaded successfully.`)
  }

  function saveModal(event) {
    event.preventDefault()
    if (modal.type === 'delete-document') {
      setDocuments((current) => current.filter((document) => document.id !== modal.document.id))
      setShares((current) => current.filter((share) => share.documentId !== modal.document.id))
      record('Deleted', modal.document, 'Document deleted and access removed')
      setNotice(`${modal.document.name} deleted.`)
    } else if (modal.type === 'revoke-access') {
      const share = modal.share
      setShares((current) => current.map((item) => item.id === share.id ? { ...item, status: 'Revoked' } : item))
      record('Permission changed', currentDocument, `Access revoked for ${share.recipient}`)
      setNotice(`Access revoked for ${share.recipient}.`)
    } else {
      const form = new FormData(event.currentTarget)
      if (modal.type === 'rename-document') {
      const name = String(form.get('name') || '').trim()
      if (!name) return
      setDocuments((current) => current.map((document) => document.id === modal.document.id ? { ...document, name } : document))
      record('Renamed', modal.document, `Renamed to ${name}`)
      setNotice('Document renamed.')
      } else if (modal.type === 'edit-document') {
      const name = String(form.get('name') || '').trim()
      const description = String(form.get('description') || '')
      const category = String(form.get('category') || modal.document.category)
      setDocuments((current) => current.map((document) => document.id === modal.document.id ? { ...document, name, description, category } : document))
      record('Edited', modal.document, 'Updated document details')
      setNotice('Document details updated.')
      } else if (modal.type === 'create-folder' || modal.type === 'rename-folder') {
      const name = String(form.get('name') || '').trim()
      if (!name) return
      if (modal.type === 'create-folder') {
        if (folders.some((folder) => folder.toLowerCase() === name.toLowerCase())) {
          setNotice('A folder with that name already exists.')
          return
        }
        setFolders((current) => [...current, name])
        setNotice(`Folder "${name}" created.`)
      } else {
        setFolders((current) => current.map((folder) => folder === modal.folder ? name : folder))
        setDocuments((current) => current.map((document) => document.folder === modal.folder ? { ...document, folder: name } : document))
        setNotice(`Folder renamed to "${name}".`)
      }
      } else if (modal.type === 'grant-access') {
      const email = String(form.get('email') || '').trim().toLowerCase()
      const recipient = String(form.get('recipient') || '').trim()
      const duplicate = shares.some((share) => share.documentId === currentDocument.id && share.email.toLowerCase() === email && share.status === 'Active')
      if (duplicate) {
        setNotice('This person already has active access to this document.')
        return
      }
      const share = { id: Date.now(), documentId: currentDocument.id, recipient, email, permission: String(form.get('permission')), date: formatDate(), status: 'Active', expiry: String(form.get('expiry') || '') }
      setShares((current) => [share, ...current])
      record('Permission changed', currentDocument, `${share.permission} access granted to ${recipient}`)
      setNotifications((current) => [{ id: Date.now(), message: `You granted ${share.permission} access to ${email} on ${currentDocument.name}`, read: false }, ...current])
      setNotice(`Access granted to ${recipient}.`)
      }
    }
    setModal(null)
  }

  function moveDocument(event) {
    event.preventDefault()
    const destination = new FormData(event.currentTarget).get('folder')
    if (!destination || !currentDocument) return
    setDocuments((current) => current.map((document) => document.id === currentDocument.id ? { ...document, folder: String(destination) } : document))
    record('Moved', currentDocument, `Moved to folder ${String(destination)}`)
    setNotice(`${currentDocument.name} moved to ${String(destination)}.`)
  }

  function saveProfile(event) {
    event.preventDefault()
    setProfile({ name: profileDraft.name.trim(), email: profileDraft.email.trim() })
    setDocuments((current) => current.map((document) => document.owner === profile.name ? { ...document, owner: profileDraft.name.trim() } : document))
    setProfileDraft({ name: profileDraft.name.trim(), email: profileDraft.email.trim() })
    setNotice('Profile updated in this demo.')
  }

  function changePassword(event) {
    event.preventDefault()
    if (password.next.length < 12) {
      setNotice('New password must contain at least 12 characters.')
    } else if (password.next !== password.confirm) {
      setNotice('New password and confirmation do not match.')
    } else {
      setNotice('Password changed in this demo.')
      setPassword({ current: '', next: '', confirm: '' })
    }
  }

  function exportActivity(rows) {
    const lines = [['Timestamp', 'User', 'Action', 'Document', 'Details', 'Result'], ...rows.map((item) => [item.timestamp, item.user, item.action, documents.find((document) => document.id === item.documentId)?.name || '', item.details, item.result])]
    const csv = lines.map((line) => line.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\n')
    const href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    const anchor = window.document.createElement('a')
    anchor.href = href
    anchor.download = 'doctrust-activity.csv'
    anchor.click()
    URL.revokeObjectURL(href)
    setNotice('Activity history exported.')
  }

  const visibleDocuments = useMemo(() => ownedDocuments.filter((document) => {
    const matchesText = `${document.name} ${document.description}`.toLowerCase().includes(appliedFilters.query.toLowerCase())
    const matchesCategory = appliedFilters.category === 'All categories' || document.category === appliedFilters.category
    const matchesDate = !appliedFilters.date || new Date(document.modified) >= new Date(appliedFilters.date)
    return matchesText && matchesCategory && matchesDate
  }), [ownedDocuments, appliedFilters])
  const pageCount = Math.max(1, Math.ceil(visibleDocuments.length / 8))
  const pageDocuments = visibleDocuments.slice((pageNumber - 1) * 8, pageNumber * 8)
  const visibleShares = shares.filter((share) => {
    const document = documents.find((item) => item.id === share.documentId)
    return `${document?.name || ''} ${share.recipient} ${share.email}`.toLowerCase().includes(sharedFilters.query.toLowerCase()) &&
      (sharedFilters.recipient === 'All recipients' || share.recipient === sharedFilters.recipient) &&
      (sharedFilters.permission === 'All' || share.permission === sharedFilters.permission)
  })
  const visibleActivity = activity.filter((item) => {
    const document = documents.find((doc) => doc.id === item.documentId)
    return `${item.user} ${item.action} ${document?.name || ''} ${item.details}`.toLowerCase().includes(activityFilters.query.toLowerCase()) &&
      (activityFilters.action === 'All actions' || item.action === activityFilters.action) &&
      (activityFilters.document === 'All documents' || document?.name === activityFilters.document) &&
      (!activityFilters.date || new Date(item.timestamp) >= new Date(activityFilters.date))
  })

  function renderDocuments() {
    return <Panel className="p-3 sm:p-4">
      <form onSubmit={applyDocumentFilters} className="mb-4 grid items-end gap-3 sm:grid-cols-2 xl:grid-cols-[1.4fr_0.8fr_0.8fr_auto_auto]">
        <Field label="Search Documents"><span className="relative block"><Search size={15} className="absolute left-3 top-3 text-slate-400" /><TextInput className="pl-9" placeholder="Search by document name" value={query} onChange={(event) => setQuery(event.target.value)} /></span></Field>
        <Field label="Category"><SelectInput value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}><option>All categories</option>{categories.map((category) => <option key={category}>{category}</option>)}</SelectInput></Field>
        <Field label="From date"><TextInput type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} /></Field>
        <ActionButton type="submit"><Filter size={14} /> Apply Filters</ActionButton>
        <ActionButton variant="primary" onClick={() => navigate('/employee/upload')}><Upload size={14} /> Upload Document</ActionButton>
      </form>
      {notice && <p role="status" className="mb-3 rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-900">{notice}</p>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[850px] text-left text-xs">
          <thead><tr className="border-b border-slate-200 text-slate-500">{['Document', 'Category', 'Type', 'Size', 'Modified', 'Actions'].map((heading) => <th key={heading} className="px-2 py-3 font-semibold">{heading}</th>)}</tr></thead>
          <tbody>{pageDocuments.map((document) => <tr key={document.id} className="border-b border-slate-100 last:border-0">
            <td className="px-2 py-2.5"><div className="flex items-center gap-2"><span className="rounded-lg bg-rose-50 p-2 text-rose-700"><FileText size={15} /></span><span className="font-semibold">{document.name}</span></div></td>
            <td className="px-2 py-2.5">{document.category}</td><td className="px-2 py-2.5">{document.type}</td><td className="px-2 py-2.5">{document.size}</td><td className="whitespace-nowrap px-2 py-2.5">{document.modified}</td>
            <td className="relative px-2 py-2.5"><div className="flex gap-1.5"><ActionButton onClick={() => openPreview(document)}><Eye size={13} /> Preview</ActionButton><ActionButton onClick={() => downloadDocument(document)}><Download size={13} /> Download</ActionButton><ActionButton aria-expanded={moreActions === document.id} onClick={() => setMoreActions(moreActions === document.id ? null : document.id)}><SlidersHorizontal size={13} /> More Actions</ActionButton></div>
              {moreActions === document.id && <div className="absolute right-2 top-12 z-20 grid w-44 gap-1 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"><button onClick={() => { setModal({ type: 'edit-document', document }); setMoreActions(null) }} className="rounded-lg px-3 py-2 text-left text-xs hover:bg-emerald-50"><Pencil size={13} className="mr-2 inline" />Edit Details</button><button onClick={() => { setModal({ type: 'rename-document', document }); setMoreActions(null) }} className="rounded-lg px-3 py-2 text-left text-xs hover:bg-emerald-50"><Pencil size={13} className="mr-2 inline" />Rename</button><button onClick={() => { setModal({ type: 'delete-document', document }); setMoreActions(null) }} className="rounded-lg px-3 py-2 text-left text-xs text-rose-700 hover:bg-rose-50"><Trash2 size={13} className="mr-2 inline" />Delete Document</button></div>}
            </td>
          </tr>)}
          {pageDocuments.length === 0 && <tr><td colSpan="6" className="px-4 py-10 text-center text-slate-500">No documents match these filters.</td></tr>}</tbody>
        </table>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500"><span>Showing {pageDocuments.length ? (pageNumber - 1) * 8 + 1 : 0}-{Math.min(pageNumber * 8, visibleDocuments.length)} of {visibleDocuments.length} documents</span><div className="flex gap-1"><ActionButton disabled={pageNumber === 1} onClick={() => setPageNumber((value) => Math.max(1, value - 1))}>Previous</ActionButton>{Array.from({ length: pageCount }, (_, index) => <ActionButton key={index} variant={pageNumber === index + 1 ? 'primary' : 'outline'} onClick={() => setPageNumber(index + 1)}>{index + 1}</ActionButton>)}<ActionButton disabled={pageNumber === pageCount} onClick={() => setPageNumber((value) => Math.min(pageCount, value + 1))}>Next</ActionButton></div></div>
    </Panel>
  }

  function renderUpload() {
    return <div className="grid items-start gap-4 xl:grid-cols-[1.5fr_0.8fr]">
      <Panel><form onSubmit={submitUpload} className="space-y-4">
        <input ref={fileInput} type="file" accept=".pdf,.docx,.xlsx,.pptx" className="hidden" onChange={(event) => selectUploadFile(event.target.files?.[0])} />
        <button type="button" onClick={() => fileInput.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); selectUploadFile(event.dataTransfer.files?.[0]) }} className="flex min-h-48 w-full flex-col items-center justify-center rounded-xl border-2 border-dashed border-emerald-300 bg-emerald-50 px-5 text-center hover:bg-emerald-100">
          <Upload size={30} className="mb-3 text-emerald-800" /><span className="font-semibold">{selectedFile ? selectedFile.name : 'Drag and drop your file here'}</span><span className="my-2 text-sm text-slate-500">or</span><span className="rounded-full bg-emerald-700 px-5 py-2 text-sm font-semibold text-white">Browse Files</span>
        </button>
        <Field label="Document name"><TextInput required value={upload.name} onChange={(event) => setUpload({ ...upload, name: event.target.value })} placeholder="Enter a document name" /></Field>
        <Field label="Category"><SelectInput value={upload.category} onChange={(event) => setUpload({ ...upload, category: event.target.value })}>{categories.map((category) => <option key={category}>{category}</option>)}</SelectInput></Field>
        <Field label="Description (optional)"><textarea value={upload.description} onChange={(event) => setUpload({ ...upload, description: event.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-emerald-600" rows="3" placeholder="Short description" /></Field>
        <ActionButton type="submit" variant="primary"><Upload size={14} /> Upload Document</ActionButton>
      </form></Panel>
      <div className="space-y-4"><Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><FileText size={17} /> Selected File</h2>{selectedFile ? <><p className="text-sm text-slate-600">File type: {selectedFile.name.split('.').pop()?.toUpperCase()}</p><p className="mt-1 text-sm text-slate-600">Size: {formatFileSize(selectedFile.size)}</p><div className="mt-3 h-2 rounded-full bg-slate-200"><div className="h-full w-full rounded-full bg-emerald-700" /></div><p className="mt-2 text-xs text-emerald-800">Ready to upload</p></> : <p className="text-sm text-slate-500">Choose a file to see its details here.</p>}<h3 className="mt-4 font-semibold"><Check size={15} className="mr-1 inline" /> Upload Rules</h3><ul className="mt-2 space-y-1 text-sm text-slate-500"><li>Allowed: PDF, DOCX, XLSX, PPTX</li><li>Maximum size: 50 MB</li><li>Files are checked before upload.</li></ul></Panel>{notice && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">{notice}</p>}</div>
    </div>
  }

  function renderFolders() {
    const owned = documents.filter((document) => document.owner === profile.name)
    const selectedFolder = new URLSearchParams(location.search).get('folder')
    const folderDocuments = selectedFolder ? owned.filter((document) => document.folder === selectedFolder) : []
    return <div className="space-y-4">
      <Panel><div className="grid items-end gap-3 sm:grid-cols-[1fr_auto_auto]"><Field label="Search Folders"><span className="relative block"><Search size={15} className="absolute left-3 top-3 text-slate-400" /><TextInput className="pl-9" placeholder="Search folders or documents" value={query} onChange={(event) => setQuery(event.target.value)} /></span></Field><ActionButton onClick={() => setNotice('Folder filters applied.') }><Filter size={14} /> Apply Filters</ActionButton><ActionButton variant="primary" onClick={() => setModal({ type: 'create-folder' })}><Plus size={14} /> Create Folder</ActionButton></div></Panel>
      {notice && <p role="status" className="rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-900">{notice}</p>}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{folders.filter((folder) => `${folder} ${owned.filter((document) => document.folder === folder).map((document) => document.name).join(' ')}`.toLowerCase().includes(query.toLowerCase())).map((folder) => <Panel key={folder}><span className="mb-3 inline-flex rounded-xl bg-teal-100 p-2.5 text-teal-800"><Folder size={19} /></span><h2 className="font-semibold">{folder}</h2><p className="mt-1 text-xs text-slate-500">{owned.filter((document) => document.folder === folder).length} documents</p><div className="mt-3 flex gap-1.5"><ActionButton variant="primary" onClick={() => navigate(`/employee/folders?folder=${encodeURIComponent(folder)}`)}><Folder size={13} /> Open Folder</ActionButton><ActionButton onClick={() => setModal({ type: 'rename-folder', folder })}><Pencil size={13} /> Rename</ActionButton></div></Panel>)}</div>
      {selectedFolder && <Panel><div className="mb-3 flex items-center justify-between"><h2 className="font-bold">{selectedFolder} documents</h2><ActionButton onClick={() => navigate('/employee/folders')}>Close folder</ActionButton></div><div className="space-y-2">{folderDocuments.length ? folderDocuments.map((document) => <div key={document.id} className="flex items-center justify-between gap-3 border-t border-slate-100 py-2 text-sm"><span>{document.name}</span><ActionButton onClick={() => openPreview(document)}><Eye size={13} /> Preview</ActionButton></div>) : <p className="text-sm text-slate-500">This folder is empty.</p>}</div></Panel>}
      <Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Settings2 size={16} /> Move Document</h2><form onSubmit={moveDocument} className="grid items-end gap-3 md:grid-cols-[1fr_1fr_auto]"><Field label="Document"><SelectInput value={selectedDocumentId} onChange={(event) => setSelectedDocumentId(Number(event.target.value))}>{owned.map((document) => <option key={document.id} value={document.id}>{document.name}</option>)}</SelectInput></Field><Field label="Move to folder"><SelectInput name="folder" defaultValue={currentDocument?.folder}>{folders.map((folder) => <option key={folder}>{folder}</option>)}</SelectInput></Field><ActionButton variant="primary" type="submit"><SlidersHorizontal size={13} /> Move Document</ActionButton></form><p className="mt-3 text-[11px] text-slate-500">Moving a document to a folder never changes who can access it.</p></Panel>
    </div>
  }

  function renderShares() {
    const recipients = [...new Set(shares.map((share) => share.recipient))]
    return <Panel>
      <div className="mb-4 grid items-end gap-3 sm:grid-cols-2 xl:grid-cols-[1.5fr_0.8fr_0.8fr_auto]">
        <Field label="Search Documents"><TextInput placeholder="Search by document or recipient" value={sharedFilters.query} onChange={(event) => setSharedFilters({ ...sharedFilters, query: event.target.value })} /></Field>
        <Field label="Recipient"><SelectInput value={sharedFilters.recipient} onChange={(event) => setSharedFilters({ ...sharedFilters, recipient: event.target.value })}><option>All recipients</option>{recipients.map((recipient) => <option key={recipient}>{recipient}</option>)}</SelectInput></Field>
        <Field label="Permission"><SelectInput value={sharedFilters.permission} onChange={(event) => setSharedFilters({ ...sharedFilters, permission: event.target.value })}><option>All</option><option>Read</option><option>Download</option><option>Edit</option></SelectInput></Field><ActionButton onClick={() => setNotice('Sharing filters applied.')}><Filter size={14} /> Apply Filters</ActionButton>
      </div>
      <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-xs"><thead><tr className="border-b border-slate-200 text-slate-500">{['Document', 'Recipient', 'Permission', 'Date Shared', 'Status', 'Actions'].map((heading) => <th key={heading} className="px-2 py-3">{heading}</th>)}</tr></thead><tbody>{visibleShares.map((share) => { const document = documents.find((item) => item.id === share.documentId); return <tr key={share.id} className="border-b border-slate-100 last:border-0"><td className="px-2 py-3 font-semibold">{document?.name || 'Deleted document'}</td><td className="px-2 py-3">{share.recipient}<span className="mt-1 block text-[10px] text-slate-500">{share.email}</span></td><td className="px-2 py-3"><Badge tone={share.permission === 'Edit' ? 'amber' : share.permission === 'Download' ? 'purple' : 'blue'}>{share.permission}</Badge></td><td className="whitespace-nowrap px-2 py-3">{share.date}</td><td className="px-2 py-3"><Badge tone={share.status === 'Active' ? 'green' : 'red'}>{share.status}</Badge></td><td className="px-2 py-3"><ActionButton onClick={() => { setSelectedDocumentId(share.documentId); navigate('/employee/permissions') }}><LockKeyhole size={13} /> Manage Permissions</ActionButton></td></tr>})}{visibleShares.length === 0 && <tr><td colSpan="6" className="px-4 py-10 text-center text-slate-500">No sharing records found.</td></tr>}</tbody></table></div><p className="mt-3 text-xs text-slate-500">Active and revoked records are shown so you can see the full sharing history.</p>{notice && <p role="status" className="mt-3 text-sm text-emerald-800">{notice}</p>}
    </Panel>
  }

  function renderReceivedDocuments() {
    const received = documents.filter((document) => document.owner !== profile.name)
    const filtered = received.filter((document) => `${document.name} ${document.owner} ${document.category}`.toLowerCase().includes(query.toLowerCase()))
    return <Panel><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><Field label="Search shared documents" className="min-w-[220px] flex-1"><span className="relative block"><Search size={15} className="absolute left-3 top-3 text-slate-400" /><TextInput className="pl-9" placeholder="Search by document or owner" value={query} onChange={(event) => setQuery(event.target.value)} /></span></Field><span className="text-xs text-slate-500">Your access is limited to viewing and downloading shared files.</span></div><div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-xs"><thead><tr className="border-b border-slate-200 text-slate-500">{['Document', 'Owner', 'Category', 'Type', 'Modified', 'Actions'].map((heading) => <th key={heading} className="px-2 py-3">{heading}</th>)}</tr></thead><tbody>{filtered.map((document) => <tr key={document.id} className="border-b border-slate-100"><td className="px-2 py-3 font-semibold">{document.name}</td><td className="px-2 py-3">{document.owner}</td><td className="px-2 py-3">{document.category}</td><td className="px-2 py-3">{document.type}</td><td className="px-2 py-3">{document.modified}</td><td className="px-2 py-3"><div className="flex gap-1.5"><ActionButton onClick={() => openPreview(document)}><Eye size={13} /> Preview</ActionButton><ActionButton onClick={() => downloadDocument(document)}><Download size={13} /> Download</ActionButton></div></td></tr>)}{filtered.length === 0 && <tr><td colSpan="6" className="px-4 py-10 text-center text-slate-500">No documents have been shared with you.</td></tr>}</tbody></table></div></Panel>
  }

  function renderPermissions() {
    const documentShares = shares.filter((share) => share.documentId === currentDocument?.id)
    return <div className="space-y-3">
      {currentDocument && <Panel className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><span className="rounded-xl bg-rose-50 p-3 text-rose-700"><FileText size={20} /></span><div><h2 className="font-semibold">{currentDocument.name}</h2><p className="text-xs text-slate-500">Owner: {currentDocument.owner} · Category: {currentDocument.category} · Size: {currentDocument.size} · Uploaded: {currentDocument.modified}</p></div></div><ActionButton onClick={() => openPreview(currentDocument)}><Eye size={13} /> Preview Document</ActionButton></Panel>}
      <div className="grid items-start gap-3 xl:grid-cols-[1.5fr_0.8fr]">
        <Panel><div className="mb-3 flex flex-wrap gap-2"><ActionButton variant="primary" onClick={() => setNotice('Showing current and revoked access records for this document.') }><UsersIcon /> Current Access</ActionButton><ActionButton onClick={() => navigate('/employee/activity')}><History size={13} /> View Permission History</ActionButton></div>
          <div className="overflow-x-auto"><table className="w-full min-w-[560px] text-left text-xs"><thead><tr className="border-b border-slate-200 text-slate-500">{['User', 'Email', 'Permission', 'Status', 'Actions'].map((heading) => <th key={heading} className="px-2 py-3">{heading}</th>)}</tr></thead><tbody>{documentShares.map((share) => <tr key={share.id} className="border-b border-slate-100"><td className="px-2 py-3 font-semibold">{share.recipient}</td><td className="px-2 py-3">{share.email}</td><td className="px-2 py-3"><Badge tone={share.permission === 'Edit' ? 'amber' : share.permission === 'Download' ? 'purple' : 'blue'}>{share.permission}</Badge></td><td className="px-2 py-3"><Badge tone={share.status === 'Active' ? 'green' : 'red'}>{share.status}</Badge></td><td className="px-2 py-3">{share.status === 'Active' ? <ActionButton variant="danger" onClick={() => setModal({ type: 'revoke-access', share })}><LockKeyhole size={13} /> Revoke Access</ActionButton> : <span className="text-slate-400">Revoked</span>}</td></tr>)}{documentShares.length === 0 && <tr><td colSpan="5" className="px-3 py-8 text-center text-slate-500">No access has been granted to this document.</td></tr>}</tbody></table></div>
        </Panel>
        <div className="space-y-3"><Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Plus size={16} /> Grant Access</h2><form onSubmit={(event) => { event.preventDefault(); setModal({ type: 'grant-access' }); window.requestAnimationFrame(() => document.getElementById('grant-access-email')?.focus()) }} className="space-y-3"><Field label="Document"><SelectInput value={selectedDocumentId} onChange={(event) => setSelectedDocumentId(Number(event.target.value))}>{ownedDocuments.map((document) => <option key={document.id} value={document.id}>{document.name}</option>)}</SelectInput></Field><p className="text-xs text-slate-500">Choose a document and use the secure grant form to add a person.</p><ActionButton type="submit" variant="primary"><Plus size={13} /> Grant Access</ActionButton></form></Panel><Panel className="bg-teal-50"><h3 className="mb-2 text-sm font-bold">Permission Levels</h3><p className="text-xs text-slate-600"><Badge tone="blue">Read</Badge> View the document only.</p><p className="mt-2 text-xs text-slate-600"><Badge tone="purple">Download</Badge> View and download the document.</p><p className="mt-2 text-xs text-slate-600"><Badge tone="amber">Edit</Badge> View, download and modify. Cannot share, delete, or transfer ownership.</p></Panel></div>
      </div>{notice && <p role="status" className="rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-900">{notice}</p>}
    </div>
  }

  function renderActivity() {
    const actions = [...new Set(activity.map((item) => item.action))]
    return <div className="space-y-3"><div className="grid grid-cols-2 gap-3 xl:grid-cols-5">{[['Uploads', activity.filter((item) => item.action === 'Uploaded').length, Upload, 'blue'], ['Downloads', activity.filter((item) => item.action === 'Downloaded').length + 40, Download, 'teal'], ['Edits', activity.filter((item) => item.action === 'Edited').length + 25, Pencil, 'amber'], ['Permission Changes', activity.filter((item) => item.action === 'Permission changed').length + 12, LockKeyhole, 'purple'], ['Deletions', activity.filter((item) => item.action === 'Deleted').length + 3, Trash2, 'rose']].map(([label, value, Icon, color]) => <Panel key={label}><div className="flex items-center gap-3"><span className={`rounded-xl p-2.5 ${color === 'rose' ? 'bg-rose-100 text-rose-700' : color === 'amber' ? 'bg-amber-100 text-amber-800' : color === 'purple' ? 'bg-violet-100 text-violet-700' : color === 'blue' ? 'bg-blue-100 text-blue-700' : 'bg-teal-100 text-teal-700'}`}><Icon size={17} /></span><div><p className="text-xs text-slate-500">{label}</p><p className="text-xl font-bold">{value}</p></div></div></Panel>)}</div>
      <Panel><div className="mb-4 grid items-end gap-3 sm:grid-cols-2 xl:grid-cols-[1.2fr_0.7fr_0.8fr_0.8fr_auto]">
        <Field label="Search Activity"><TextInput placeholder="Search by document or user" value={activityFilters.query} onChange={(event) => setActivityFilters({ ...activityFilters, query: event.target.value })} /></Field>
        <Field label="Action"><SelectInput value={activityFilters.action} onChange={(event) => setActivityFilters({ ...activityFilters, action: event.target.value })}><option>All actions</option>{actions.map((action) => <option key={action}>{action}</option>)}</SelectInput></Field>
        <Field label="Document"><SelectInput value={activityFilters.document} onChange={(event) => setActivityFilters({ ...activityFilters, document: event.target.value })}><option>All documents</option>{documents.map((document) => <option key={document.id}>{document.name}</option>)}</SelectInput></Field>
        <Field label="From date"><TextInput type="date" value={activityFilters.date} onChange={(event) => setActivityFilters({ ...activityFilters, date: event.target.value })} /></Field>
        <ActionButton onClick={() => setNotice('Activity filters applied.')}><Filter size={14} /> Apply Filters</ActionButton>
      </div><div className="mb-3"><ActionButton variant="primary" onClick={() => exportActivity(visibleActivity)}><Download size={13} /> Export Activity</ActionButton></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-xs"><thead><tr className="border-b border-slate-200 text-slate-500">{['Timestamp', 'User', 'Action', 'Document', 'Details', 'Result'].map((heading) => <th key={heading} className="px-2 py-3">{heading}</th>)}</tr></thead><tbody>{visibleActivity.map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="whitespace-nowrap px-2 py-3">{item.timestamp}</td><td className="px-2 py-3">{item.user}</td><td className="px-2 py-3">{item.action}</td><td className="px-2 py-3 font-semibold">{documents.find((document) => document.id === item.documentId)?.name || '—'}</td><td className="px-2 py-3">{item.details}</td><td className="px-2 py-3"><Badge tone={item.result === 'Success' ? 'green' : 'red'}>{item.result}</Badge></td></tr>)}{visibleActivity.length === 0 && <tr><td colSpan="6" className="px-4 py-8 text-center text-slate-500">No activities match these filters.</td></tr>}</tbody></table></div><p className="mt-3 text-xs text-slate-500">Showing {visibleActivity.length} of {activity.length} activities.</p></Panel></div>
  }

  function renderProfile() {
    return <div className="grid items-start gap-4 xl:grid-cols-2"><Panel><h2 className="mb-4 flex items-center gap-2 font-bold"><UserRound size={17} /> Account Details</h2><p className="text-sm text-slate-500">Role: Employee</p><p className="mt-1 text-sm text-slate-500">Status: <Badge>Active</Badge></p><form onSubmit={saveProfile} className="mt-4 space-y-3"><Field label="Full name"><TextInput required value={profileDraft.name} onChange={(event) => setProfileDraft({ ...profileDraft, name: event.target.value })} /></Field><Field label="Email"><TextInput required type="email" value={profileDraft.email} onChange={(event) => setProfileDraft({ ...profileDraft, email: event.target.value })} /></Field><p className="text-[11px] text-slate-500">Email changes are handled by an administrator.</p><ActionButton type="submit" variant="primary"><Check size={14} /> Update Profile</ActionButton></form></Panel>
      <Panel><h2 className="mb-4 flex items-center gap-2 font-bold"><LockKeyhole size={17} /> Change Password</h2><form onSubmit={changePassword} className="space-y-3">{[['Current Password', 'current'], ['New Password', 'next'], ['Confirm New Password', 'confirm']].map(([label, key]) => <Field key={key} label={label}><span className="flex gap-2"><TextInput required type={passwordVisible ? 'text' : 'password'} value={password[key]} onChange={(event) => setPassword({ ...password, [key]: event.target.value })} placeholder={`Enter ${label.toLowerCase()}`} /><button type="button" onClick={() => setPasswordVisible(!passwordVisible)} aria-label={passwordVisible ? 'Hide passwords' : 'Show passwords'} className="rounded-full border border-slate-200 px-3 text-emerald-800"><Eye size={16} /></button></span></Field>)}<p className="text-[11px] text-slate-500">Use at least 12 characters.</p><ActionButton type="submit" variant="primary"><Check size={14} /> Change Password</ActionButton></form></Panel>
      <Panel className="xl:col-span-2"><h2 className="mb-3 flex items-center gap-2 font-bold"><History size={17} /> Recent Account Activity</h2><div className="overflow-x-auto"><table className="w-full min-w-[500px] text-left text-xs"><thead><tr className="border-b border-slate-100 text-slate-500"><th className="py-2">Date / time</th><th className="py-2">Activity</th><th className="py-2">Result</th></tr></thead><tbody>{activity.slice(0, 3).map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="py-2">{item.timestamp}</td><td className="py-2">{item.action}</td><td className="py-2"><Badge tone={item.result === 'Success' ? 'green' : 'red'}>{item.result}</Badge></td></tr>)}</tbody></table></div></Panel></div>
  }

  function renderDashboard() {
    const stats = [
      ['Total Documents', ownedDocuments.length, FileText, 'blue'],
      ['Shared Documents', shares.filter((share) => share.status === 'Active').length, Share2, 'teal'],
      ['Recently Accessed', activity.length, Clock3, 'amber'],
      ['Storage Used', '128 MB', Database, 'purple'],
    ]
    return <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{stats.map(([label, value, Icon, color]) => <Panel key={label}><div className="flex items-center gap-3"><span className={`rounded-xl p-3 ${color === 'blue' ? 'bg-blue-100 text-blue-700' : color === 'teal' ? 'bg-teal-100 text-teal-700' : color === 'amber' ? 'bg-amber-100 text-amber-800' : 'bg-violet-100 text-violet-700'}`}><Icon size={21} /></span><div><p className="text-sm text-slate-500">{label}</p><p className="text-2xl font-bold">{value}</p></div></div></Panel>)}</div>
      <div className="grid items-start gap-4 xl:grid-cols-[1.8fr_1fr]"><Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Activity size={17} /> Recent Activity</h2><div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left text-sm"><thead><tr className="border-b border-slate-100 text-xs text-slate-500"><th className="py-2">Action</th><th className="py-2">Document</th><th className="py-2">Time</th></tr></thead><tbody>{activity.slice(0, 4).map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="py-3">{item.action}</td><td className="py-3">{documents.find((document) => document.id === item.documentId)?.name || '—'}</td><td className="py-3">{item.timestamp.split(', ').slice(-1)}</td></tr>)}</tbody></table></div></Panel><Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Plus size={17} /> Quick Actions</h2><div className="grid gap-2"><ActionButton variant="primary" className="w-full py-3 text-sm" onClick={() => navigate('/employee/upload')}><Upload size={15} /> Upload Document</ActionButton><ActionButton className="w-full py-3 text-sm" onClick={() => navigate('/employee/documents')}><FileText size={15} /> My Documents</ActionButton><ActionButton className="w-full py-3 text-sm" onClick={() => navigate('/employee/permissions')}><LockKeyhole size={15} /> Manage Permissions</ActionButton></div></Panel></div>
      <Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Bell size={17} /> Notifications</h2><div className="space-y-2">{notifications.map((item) => <p key={item.id} className={`flex items-start gap-2 text-sm ${item.read ? 'text-slate-500' : 'text-slate-700'}`}><Share2 size={15} className="mt-0.5 shrink-0" />{item.message}</p>)}</div></Panel>
    </div>
  }

  function renderModal() {
    if (!modal || modal.type === 'logout') return null
    if (modal.type === 'preview') return <Modal title={modal.document.name} onClose={() => setModal(null)}><div className="rounded-xl bg-slate-50 p-6"><p className="text-sm text-slate-600">{modal.document.description || 'No description provided.'}</p><dl className="mt-4 grid grid-cols-2 gap-3 text-xs"><div><dt className="text-slate-500">Category</dt><dd className="mt-1 font-semibold">{modal.document.category}</dd></div><div><dt className="text-slate-500">Type / size</dt><dd className="mt-1 font-semibold">{modal.document.type} · {modal.document.size}</dd></div><div><dt className="text-slate-500">Owner</dt><dd className="mt-1 font-semibold">{modal.document.owner}</dd></div><div><dt className="text-slate-500">Modified</dt><dd className="mt-1 font-semibold">{modal.document.modified}</dd></div></dl></div><div className="mt-4 flex justify-end gap-2"><ActionButton onClick={() => setModal(null)}>Close</ActionButton><ActionButton variant="primary" onClick={() => downloadDocument(modal.document)}><Download size={13} /> Download</ActionButton></div></Modal>
    const destructive = modal.type === 'delete-document' || modal.type === 'revoke-access'
    const titleByType = { 'rename-document': 'Rename Document', 'edit-document': 'Edit Document Details', 'delete-document': 'Delete Document?', 'create-folder': 'Create Folder', 'rename-folder': 'Rename Folder', 'grant-access': 'Grant Access', 'revoke-access': `Revoke access for ${modal.share?.recipient || 'user'}?` }
    return <Modal title={titleByType[modal.type]} onClose={() => setModal(null)}>
      {destructive ? <><p className="text-sm leading-relaxed text-slate-600">{modal.type === 'delete-document' ? `${modal.document.name} will be removed and everyone with access will lose it. This is recorded in the audit log.` : `${modal.share.recipient} will immediately lose access to ${currentDocument?.name}. This is recorded in the audit log.`}</p><div className="mt-5 flex justify-end gap-2"><ActionButton onClick={() => setModal(null)}>Cancel</ActionButton><ActionButton variant="danger" onClick={() => saveModal({ preventDefault() {}, currentTarget: { elements: [] } })}><Trash2 size={13} />{modal.type === 'delete-document' ? 'Delete Document' : 'Revoke Access'}</ActionButton></div></> :
        <form onSubmit={saveModal} className="space-y-3">
          {modal.type === 'rename-document' && <Field label="Document name"><TextInput name="name" required defaultValue={modal.document.name} /></Field>}
          {modal.type === 'edit-document' && <><Field label="Document name"><TextInput name="name" required defaultValue={modal.document.name} /></Field><Field label="Category"><SelectInput name="category" defaultValue={modal.document.category}>{categories.map((category) => <option key={category}>{category}</option>)}</SelectInput></Field><Field label="Description"><textarea name="description" defaultValue={modal.document.description} className="w-full rounded-xl border border-slate-200 p-3 text-sm" rows="3" /></Field></>}
          {(modal.type === 'create-folder' || modal.type === 'rename-folder') && <Field label="Folder name"><TextInput name="name" required defaultValue={modal.folder || ''} placeholder="Enter folder name" /></Field>}
          {modal.type === 'grant-access' && <><Field label="User name"><TextInput name="recipient" required placeholder="Enter full name" /></Field><Field label="Email"><TextInput id="grant-access-email" name="email" type="email" required placeholder="name@example.com" /></Field><Field label="Permission level"><SelectInput name="permission"><option>Read</option><option>Download</option><option>Edit</option></SelectInput></Field><Field label="Expiry date (optional)"><TextInput name="expiry" type="date" /></Field><p className="text-xs text-slate-500">This grants access to {currentDocument?.name}.</p></>}
          <div className="flex justify-end gap-2 pt-2"><ActionButton onClick={() => setModal(null)}>Cancel</ActionButton><ActionButton type="submit" variant="primary"><Check size={13} /> Save</ActionButton></div>
        </form>}
    </Modal>
  }

  function UsersIcon() {
    return <UserRound size={13} />
  }

  return <main className="min-h-screen bg-[#eafbf3] text-slate-800 md:flex">
    <aside className="w-full shrink-0 bg-gradient-to-b from-[#07523f] to-[#00372b] p-4 text-white md:min-h-screen md:w-56">
      <button type="button" onClick={() => navigate('/employee/dashboard')} className="mb-4 flex items-center gap-2 px-2 text-lg font-bold"><ShieldCheck size={22} /> DocTrust</button>
      <div className="mb-5 w-fit rounded-full bg-white/15 px-3 py-1 text-xs"><Folder size={12} className="mr-1 inline" /> Employee</div>
      <nav aria-label="Employee navigation" className="grid grid-cols-2 gap-1 md:flex md:flex-col">{navItems.map(([label, path, Icon]) => <button key={path} type="button" aria-current={location.pathname === path ? 'page' : undefined} onClick={() => path.endsWith('/logout') ? setModal({ type: 'logout' }) : navigate(path)} className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-left text-xs transition ${location.pathname === path ? 'bg-emerald-700 font-semibold text-white' : 'text-white/80 hover:bg-white/10'}`}><Icon size={15} />{label}</button>)}</nav>
    </aside>
    <div className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8"><header className="mb-6 flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold tracking-tight">{title[0]}</h1><p className="mt-1 text-sm text-slate-500">{title[1]}</p></div><div className="flex items-center gap-2"><div className="relative"><button type="button" aria-expanded={notificationOpen} onClick={() => setNotificationOpen(!notificationOpen)} className="relative flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold text-emerald-800"><Bell size={14} /> Notifications{unreadCount > 0 && <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white">{unreadCount}</span>}</button>{notificationOpen && <div className="absolute right-0 z-30 mt-2 w-[min(90vw,330px)] rounded-xl border border-slate-100 bg-white p-3 shadow-xl"><div className="mb-2 flex items-center justify-between"><strong className="text-sm">Notifications</strong><button type="button" onClick={() => setNotifications((current) => current.map((item) => ({ ...item, read: true })))} className="text-xs font-semibold text-emerald-800">Mark all read</button></div>{notifications.map((item) => <button key={item.id} type="button" onClick={() => { setNotifications((current) => current.map((notification) => notification.id === item.id ? { ...notification, read: true } : notification)); setNotificationOpen(false); navigate('/employee/shared') }} className={`mb-1 block w-full rounded-lg p-2 text-left text-xs ${item.read ? 'text-slate-500' : 'bg-emerald-50 text-slate-700'}`}>{item.message}</button>)}</div>}</div><button type="button" onClick={() => navigate('/employee/profile')} className="flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold"><UserRound size={14} /> Profile</button><div className="hidden items-center gap-2 sm:flex"><span className="flex size-9 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-800">{profile.name.split(' ').map((part) => part[0]).join('')}</span><div className="text-xs"><p className="font-bold">{profile.name}</p><p className="text-emerald-800">Employee</p></div></div></div></header>
      {notice && <div role="status" className="mb-4 flex items-center justify-between gap-2 rounded-xl bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">{notice}<button type="button" onClick={() => setNotice('')} aria-label="Dismiss message"><X size={15} /></button></div>}
      {page === 'documents' ? renderDocuments() : page === 'upload' ? renderUpload() : page === 'folders' ? renderFolders() : page === 'received' ? renderReceivedDocuments() : page === 'shared' ? renderShares() : page === 'permissions' ? renderPermissions() : page === 'activity' ? renderActivity() : page === 'profile' ? renderProfile() : renderDashboard()}
      <p className="mt-5 text-xs text-slate-500">Mock employee workspace. Actions update this session only; backend persistence will be connected later.</p>
    </div>
    {renderModal()}
    {modal?.type === 'logout' && <Modal title="Sign out of DocTrust?" onClose={() => setModal(null)}><p className="text-sm text-slate-600">Your session will end and you will return to the login page. Unsaved work may be lost.</p><div className="mt-5 flex justify-end gap-2"><ActionButton onClick={() => setModal(null)}>Cancel</ActionButton><ActionButton variant="primary" onClick={() => navigate('/') }><LogOut size={13} /> Sign Out</ActionButton></div></Modal>}
  </main>
}
