import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Activity, Bell, Check, Clock3, Database, Download, Eye, FileText, Filter,
  Folder, History, LockKeyhole, LogOut, Pencil, Plus, Search, Settings2,
  Share2, ShieldCheck, SlidersHorizontal, Trash2, Upload, UserRound, X,
} from 'lucide-react'
import { logout, getCurrentUser, updateProfile, changePassword as changePasswordService } from '../services/auth.js'
import './EmployeePortal.css'
import {
  listFolders,
  createFolder,
  renameFolder,
  deleteFolder,
  listDocuments,
  getStorageUsage,
  uploadDocument,
  updateDocument,
  downloadDocument as downloadDocService,
  viewDocument as viewDocService,
  deleteDocument as deleteDocService,
  archiveDocument as archiveDocService,
  restoreDocument as restoreDocService,
  listSharedDocuments,
  listShareRecipients,
  listDocumentShares,
  listOwnedDocumentShares,
  createDocumentShare,
  revokeDocumentShare,
  listEmployeeActivity,
  listEmployeeNotifications,
  markEmployeeNotificationRead,
  markAllEmployeeNotificationsRead,
} from '../services/documents.js'

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

function ActionButton({ children, onClick, variant = 'outline', className = '', type = 'button', disabled = false, ...props }) {
  const styles = variant === 'primary'
    ? 'border-emerald-700 bg-emerald-700 text-white hover:bg-emerald-800'
    : variant === 'danger'
      ? 'border-rose-200 text-rose-700 hover:bg-rose-50'
      : 'border-slate-200 bg-white text-emerald-800 hover:bg-emerald-50'
  return <button type={type} disabled={disabled} onClick={onClick} {...props} className={`inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full border px-3.5 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}>{children}</button>
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

function MoreActionsDropdown({ anchorEl, onClose, children }) {
  const menuRef = useRef(null)
  const [position, setPosition] = useState({
    top: 0,
    left: 0,
    maxHeight: 320,
    ready: false,
  })

  useLayoutEffect(() => {
    function updatePosition() {
      if (!anchorEl || !anchorEl.isConnected || !menuRef.current) {
        onClose()
        return
      }
      const rect = anchorEl.getBoundingClientRect()

      if (
        rect.bottom < 0 ||
        rect.top > window.innerHeight ||
        rect.right < 0 ||
        rect.left > window.innerWidth
      ) {
        onClose()
        return
      }

      const menuEl = menuRef.current
      const menuWidth = menuEl.offsetWidth || 176
      const menuHeight = menuEl.offsetHeight || 190
      const margin = 8
      const offset = 4

      const spaceBelow = window.innerHeight - rect.bottom
      const spaceAbove = rect.top

      const fitsBelow = spaceBelow >= menuHeight + offset + margin
      const fitsAbove = spaceAbove >= menuHeight + offset + margin

      let top
      let maxHeight

      if (fitsBelow) {
        top = rect.bottom + offset
        maxHeight = Math.max(100, spaceBelow - offset - margin)
      } else if (fitsAbove) {
        top = rect.top - menuHeight - offset
        maxHeight = Math.max(100, spaceAbove - offset - margin)
      } else if (spaceAbove > spaceBelow) {
        maxHeight = Math.max(100, spaceAbove - offset - margin)
        const visibleHeight = Math.min(menuHeight, maxHeight)
        top = Math.max(margin, rect.top - visibleHeight - offset)
      } else {
        top = rect.bottom + offset
        maxHeight = Math.max(100, spaceBelow - offset - margin)
      }

      let left = rect.right - menuWidth
      const maxLeft = window.innerWidth - menuWidth - margin
      if (left > maxLeft) left = maxLeft
      if (left < margin) left = margin

      setPosition({
        top: Math.round(top),
        left: Math.round(left),
        maxHeight: Math.round(maxHeight),
        ready: true,
      })
    }

    updatePosition()

    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)

    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [anchorEl, onClose])

  useEffect(() => {
    function handlePointerDown(event) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target) &&
        anchorEl &&
        !anchorEl.contains(event.target)
      ) {
        onClose()
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
        anchorEl?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [anchorEl, onClose])

  return createPortal(
    <div
      ref={menuRef}
      role="menu"
      aria-orientation="vertical"
      className="employee-theme fixed z-50 grid w-44 gap-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`,
        maxHeight: `${position.maxHeight}px`,
        visibility: position.ready ? 'visible' : 'hidden',
      }}
    >
      {children}
    </div>,
    document.body
  )
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
  const dataLoadRequest = useRef(null)
  const page = location.pathname.split('/')[2] || 'dashboard'
  const [documents, setDocuments] = useState([])
  const [sharedDocuments, setSharedDocuments] = useState([])
  const [backendFolders, setBackendFolders] = useState([])
  const [shares, setShares] = useState([])
  const [sharesLoadError, setSharesLoadError] = useState('')
  const [accessLoading, setAccessLoading] = useState(false)
  const [shareRecipients, setShareRecipients] = useState([])
  const [activity, setActivity] = useState([])
  const [folders, setFolders] = useState([])
  const [notifications, setNotifications] = useState([])
  const [notificationOpen, setNotificationOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const [query, setQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('All categories')
  const [dateFilter, setDateFilter] = useState('')
  const [appliedFilters, setAppliedFilters] = useState({ query: '', category: 'All categories', date: '' })
  const [pageNumber, setPageNumber] = useState(1)
  const [moreActions, setMoreActions] = useState(null)
  const [moreActionsAnchor, setMoreActionsAnchor] = useState(null)
  const [modal, setModal] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [upload, setUpload] = useState({ name: '', category: 'Reports', description: '' })
  const [selectedDocumentId, setSelectedDocumentIdRaw] = useState(() => sessionStorage.getItem('doctrust_selected_doc_id') || '')
  const permissionsRefreshed = useRef(false)
  function setSelectedDocumentId(valueOrFn) {
    setSelectedDocumentIdRaw((prev) => {
      const next = typeof valueOrFn === 'function' ? valueOrFn(prev) : valueOrFn
      if (next) sessionStorage.setItem('doctrust_selected_doc_id', next)
      return next
    })
  }
  const [moveDestination, setMoveDestination] = useState('')
  const [storageUsage, setStorageUsage] = useState(null)
  const [profile, setProfile] = useState({ name: '', email: '' })
  const [accountStatus, setAccountStatus] = useState('')
  const [profileDraft, setProfileDraft] = useState(profile)
  const [password, setPassword] = useState({ current: '', next: '', confirm: '' })
  const [passwordVisible, setPasswordVisible] = useState(false)
  const [activityFilters, setActivityFilters] = useState({ query: '', action: 'All actions', document: 'All documents', date: '' })
  const [sharedFilters, setSharedFilters] = useState({ query: '', recipient: 'All recipients', permission: 'All' })

  async function loadData() {
    if (dataLoadRequest.current) return dataLoadRequest.current

    const load = async () => {
      try {
      const user = await getCurrentUser()
      if (user) {
        const displayName = user.display_name || [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || ''
        setProfile({ name: displayName, email: user.email || '' })
        setProfileDraft({ name: displayName, email: user.email || '' })
        setAccountStatus(user.status || '')
      }

      const fetchedFolders = await listFolders()
      if (Array.isArray(fetchedFolders)) {
        setBackendFolders(fetchedFolders)
        setFolders(fetchedFolders.map((f) => f.name))
      }

      const docsResp = await listDocuments({ status: 'all', page_size: 100 })
      const userName = user?.display_name || [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || ''
      const mapped = (docsResp?.results || []).filter((d) => d.status !== 'deleted').map((d) => ({
          id: d.id,
          name: d.name,
          category: d.folder_name || 'Documents',
          folder: d.folder_name || 'Documents',
          folderId: d.folder,
          type: d.file_type,
          size: d.size_display || formatFileSize(d.size),
          modified: d.created_at
            ? new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(d.created_at))
            : formatDate(),
          owner: userName,
          description: d.description || '',
          status: d.status,
          rawDoc: d,
        }))
      setDocuments(mapped)
      setSelectedDocumentId((current) => {
        // If the current ID exists (e.g. restored from sessionStorage), keep it —
        // it may belong to a shared document that hasn't loaded yet.
        if (current && mapped.some((document) => document.id === current)) return current
        if (current) return current // might be a shared doc; don't override yet
        return mapped[0]?.id || ''
      })
      const optionalResults = await Promise.allSettled([
        listShareRecipients(),
        listSharedDocuments(),
        listEmployeeActivity(),
        listEmployeeNotifications(),
        listOwnedDocumentShares(),
      ])
      const [recipientResult, sharedResult, activityResult, notificationResult, ownedSharesResult] = optionalResults
      const responseOr = (result, fallback) => result.status === 'fulfilled' ? result.value : fallback
      const optionalFailures = [
        ['share recipients', recipientResult],
        ['shared documents', sharedResult],
        ['activity history', activityResult],
        ['notifications', notificationResult],
        ['document sharing details', ownedSharesResult],
      ].filter(([, result]) => result.status === 'rejected').map(([label]) => label)
      const recipientResponse = responseOr(recipientResult, [])
      const sharedResponse = responseOr(sharedResult, { results: [] })
      const activityResponse = responseOr(activityResult, { results: [] })
      const notificationResponse = responseOr(notificationResult, { results: [] })
      const ownedSharesResponse = responseOr(ownedSharesResult, [])
      setSharesLoadError(ownedSharesResult.status === 'rejected' ? (ownedSharesResult.reason?.message || 'Unable to load sharing records.') : '')
      const recipients = Array.isArray(recipientResponse) ? recipientResponse : []
      const recipientById = new Map(recipients.map((recipient) => [recipient.id, recipient]))
      setShareRecipients(recipients)
      setShares((Array.isArray(ownedSharesResponse) ? ownedSharesResponse : []).map((share) => {
        const recipient = recipientById.get(share.recipient)
        const expired = share.expires_at && new Date(share.expires_at) <= new Date()
        return {
          id: share.id,
          documentId: share.document,
          recipient: share.recipient_name || share.recipient_username,
          email: share.recipient_email || recipient?.email || '',
          recipientId: share.recipient,
          permission: share.permission === 'EDIT' ? 'Edit' : share.permission === 'DOWNLOAD' ? 'Download' : 'Read',
          date: new Date(share.created_at).toLocaleDateString(),
          status: expired ? 'Expired' : 'Active',
          expiry: share.expires_at ? new Date(share.expires_at).toISOString().slice(0, 10) : '',
        }
      }))
      const shared = (sharedResponse?.results || []).map((document) => ({
        id: document.id,
        name: document.name,
        category: document.folder_name || 'Documents',
        folder: document.folder_name || 'Documents',
        folderId: document.folder,
        type: document.file_type,
        size: document.size_display || formatFileSize(document.size),
        modified: document.created_at
          ? new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(document.created_at))
          : '—',
        owner: document.owner_name,
        owner_email: document.owner_email || '',
        permission: document.permission,
        description: document.description || '',
        rawDoc: document,
      }))
      setSharedDocuments(shared)
      // Now that both owned and shared docs are loaded, validate selectedDocumentId.
      // If the persisted ID doesn't match any available document, fall back.
      setSelectedDocumentId((current) => {
        if (!current) return mapped[0]?.id || ''
        const existsInOwned = mapped.some((d) => String(d.id) === String(current))
        const existsInShared = shared.some((d) => String(d.id) === String(current))
        if (existsInOwned || existsInShared) return current
        return mapped[0]?.id || ''
      })
      const fetchedActivity = (activityResponse?.results || []).map((event) => ({
        id: event.id,
        timestamp: event.timestamp,
        user: userName,
        action: event.action_label,
        actionCode: event.action,
        documentId: event.target_id,
        documentName: event.document_name || '',
        details: event.document_name || event.target_type || '',
        result: event.outcome,
      }))
      setActivity(fetchedActivity)
      setNotifications((notificationResponse?.results || []).map((notification) => ({
        id: notification.id,
        message: notification.message,
        read: notification.is_read,
      })))
      let storageError = ''
      try {
        setStorageUsage(await getStorageUsage())
      } catch (err) {
        storageError = err.message || 'Unable to refresh storage usage.'
        console.warn('Storage usage could not be refreshed:', err)
        setNotice(storageError)
      }
      if (optionalFailures.length) {
        setNotice(`Some dashboard sections could not be loaded: ${optionalFailures.join(', ')}.`)
      }
      return { ok: true, storageError, optionalFailures }
      } catch (err) {
        setDocuments([])
        setBackendFolders([])
        setFolders([])
        const error = err.message || 'Unable to load your documents.'
        setNotice(error)
        return { ok: false, error }
      }
    }

    const request = load()
    dataLoadRequest.current = request
    try {
      return await request
    } finally {
      if (dataLoadRequest.current === request) dataLoadRequest.current = null
    }
  }

  async function getOrCreateFolder(name) {
    let folder = backendFolders.find((item) => item.name.toLowerCase() === name.toLowerCase())
    if (!folder) {
      folder = await createFolder(name)
      setBackendFolders((current) => [...current, folder])
      setFolders((current) => current.some((item) => item.toLowerCase() === folder.name.toLowerCase())
        ? current
        : [...current, folder.name])
    }
    return folder
  }

  useEffect(() => {
    loadData().then(() => {
      // After data loads, validate the selectedDocumentId.
      // If it doesn't match any owned or shared doc, fall back to the first owned doc.
      setSelectedDocumentId((current) => {
        if (!current) return current
        // We'll let the computed permissionDocument handle fallback on render
        return current
      })
    })
  }, [])

  const title = pageTitles[page] || pageTitles.dashboard
  const ownedDocuments = documents.filter((document) => !document.owner || document.owner === profile.name || document.rawDoc)
  const recentlyAccessedDocumentCount = new Set(
    activity
      .filter((event) => ['DOCUMENT_VIEW', 'DOCUMENT_DOWNLOAD'].includes(event.actionCode) && event.documentId)
      .map((event) => event.documentId),
  ).size
  const availableCategories = [...new Set([...categories, ...folders])]
  const currentDocument = documents.find((document) => String(document.id) === String(selectedDocumentId)) || ownedDocuments[0]
  const permissionDocument = [...ownedDocuments, ...sharedDocuments].find((document) => String(document.id) === String(selectedDocumentId)) || currentDocument || sharedDocuments[0]
  const unreadCount = notifications.filter((item) => !item.read).length

  useEffect(() => {
    setMoveDestination(currentDocument?.folder || '')
  }, [selectedDocumentId, currentDocument?.folder])

  // Clear any previous access error whenever switching documents or navigation pages
  useEffect(() => {
    setSharesLoadError('')
  }, [page, selectedDocumentId])

  // Auto-refresh current access when landing on the permissions page
  useEffect(() => {
    if (page === 'permissions' && !permissionsRefreshed.current && (documents.length > 0 || sharedDocuments.length > 0)) {
      permissionsRefreshed.current = true
      const permDoc = [...documents, ...sharedDocuments].find((d) => String(d.id) === String(selectedDocumentId)) || documents[0] || sharedDocuments[0]
      if (permDoc) {
        const isOwned = documents.some((d) => String(d.id) === String(permDoc.id))
        setAccessLoading(true)
        setSharesLoadError('')
        if (isOwned) {
          listDocumentShares(permDoc.rawDoc?.id || permDoc.id).then((freshShares) => {
            const recipientsById = new Map(shareRecipients.map((r) => [r.id, r]))
            setShares((current) => [
              ...current.filter((s) => String(s.documentId) !== String(permDoc.id)),
              ...freshShares.map((share) => ({
                id: share.id,
                documentId: share.document,
                recipient: share.recipient_name || share.recipient_username,
                email: share.recipient_email || recipientsById.get(share.recipient)?.email || '',
                recipientId: share.recipient,
                permission: share.permission === 'EDIT' ? 'Edit' : share.permission === 'DOWNLOAD' ? 'Download' : 'Read',
                date: new Date(share.created_at).toLocaleDateString(),
                status: share.expires_at && new Date(share.expires_at) <= new Date() ? 'Expired' : 'Active',
                expiry: share.expires_at ? new Date(share.expires_at).toISOString().slice(0, 10) : '',
              })),
            ])
          }).catch((err) => {
            setSharesLoadError(err.message || 'Unable to load current access.')
          }).finally(() => setAccessLoading(false))
        } else {
          listSharedDocuments().then((refreshed) => {
            const currentShare = (refreshed?.results || []).find((share) => String(share.id) === String(permDoc.id))
            if (currentShare) {
              setSharedDocuments((current) => current.map((document) => String(document.id) === String(currentShare.id) ? {
                ...document,
                permission: currentShare.permission,
                owner: currentShare.owner_name,
                owner_email: currentShare.owner_email || '',
                rawDoc: currentShare,
              } : document))
            }
          }).catch((err) => {
            setSharesLoadError(err.message || 'Unable to load current access.')
          }).finally(() => setAccessLoading(false))
        }
      }
    }
    if (page !== 'permissions') permissionsRefreshed.current = false
  }, [page, documents.length, sharedDocuments.length, selectedDocumentId])

  async function record() {
    try {
      const [activityResp, notifResp] = await Promise.all([
        listEmployeeActivity(),
        listEmployeeNotifications().catch(() => null),
      ])
      const events = (activityResp?.results || []).map((event) => ({
        id: event.id,
        timestamp: event.timestamp,
        user: profile.name,
        action: event.action_label,
        actionCode: event.action,
        documentId: event.target_id,
        documentName: event.document_name || '',
        details: event.document_name || event.target_type || '',
        result: event.outcome,
      }))
      setActivity(events)
      if (notifResp?.results) {
        setNotifications(notifResp.results.map((notification) => ({
          id: notification.id,
          message: notification.message,
          read: notification.is_read,
        })))
      }
    } catch (error) {
      setNotice(error.message || 'Unable to refresh activity history.')
    }
  }

  async function openPreview(document) {
    try {
      if (!document.rawDoc) throw new Error('This document is no longer available. Refresh and try again.')
      try {
        await viewDocService(document.rawDoc)
      } catch (viewErr) {
        console.warn('Inline preview popup could not be opened:', viewErr)
      }
      record()
    } catch (error) {
      setNotice(error.message || 'Unable to preview this document.')
      return
    }
    setModal({ type: 'preview', document })
  }

  async function markNotificationRead(id) {
    try {
      await markEmployeeNotificationRead(id)
      setNotifications((current) => current.map((item) => item.id === id ? { ...item, read: true } : item))
    } catch (error) {
      setNotice(error.message || 'Unable to update notification.')
    }
  }

  async function markAllNotificationsRead() {
    try {
      await markAllEmployeeNotificationsRead()
      setNotifications((current) => current.map((item) => ({ ...item, read: true })))
    } catch (error) {
      setNotice(error.message || 'Unable to update notifications.')
    }
  }

  function applyDocumentFilters(event) {
    event.preventDefault()
    setAppliedFilters({ query, category: categoryFilter, date: dateFilter })
    setPageNumber(1)
  }

  async function downloadDocument(document) {
    try {
      if (!document.rawDoc) throw new Error('This document is no longer available. Refresh and try again.')
      await downloadDocService(document.rawDoc)
      record()
      setNotice(`${document.name} download initiated.`)
    } catch (err) {
      setNotice(err.message || 'Download failed.')
    }
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

  async function submitUpload(event) {
    event.preventDefault()
    if (!selectedFile) {
      setNotice('Select a file before uploading.')
      return
    }
    if (!upload.name.trim()) {
      setNotice('Enter a document name.')
      return
    }

    try {
      setNotice('Uploading document...')
      const targetFolder = await getOrCreateFolder(upload.category)

      const created = await uploadDocument(selectedFile, {
        name: upload.name.trim(),
        description: upload.description.trim(),
        folder: targetFolder.id,
      })

      const refresh = await loadData()
      setSelectedFile(null)
      setUpload({ name: '', category: 'Reports', description: '' })
      if (fileInput.current) fileInput.current.value = ''
      record('Uploaded', { id: created.id, name: created.name }, `File uploaded (${created.size_display || formatFileSize(selectedFile.size)})`)
      let message = refresh.ok
        ? `${created.name} uploaded successfully.`
        : `${created.name} uploaded, but the document list could not be refreshed: ${refresh.error}`
      if (refresh.storageError) message += ` Storage usage could not be refreshed: ${refresh.storageError}`
      setNotice(message)
    } catch (err) {
      setNotice(err.message || 'Upload failed.')
    }
  }

  async function saveModal(event) {
    event.preventDefault()
    if (modal.type === 'delete-document') {
      try {
        const documentId = modal.document.rawDoc?.id
        if (!documentId) throw new Error('This document is no longer available. Refresh and try again.')
        await deleteDocService(documentId)
        setDocuments((current) => current.filter((document) => document.id !== documentId))
        setShares((current) => current.filter((share) => share.documentId !== documentId))
        setSelectedDocumentId((current) => current === documentId ? '' : current)
        const refresh = await loadData()
        record('Deleted', modal.document, 'Document deleted and access removed')
        let message = refresh.ok
          ? `${modal.document.name} deleted.`
          : `${modal.document.name} deleted, but the document list could not be refreshed: ${refresh.error}`
        if (refresh.storageError) message += ` Storage usage could not be refreshed: ${refresh.storageError}`
        setNotice(message)
      } catch (err) {
        setNotice(err.message || 'Failed to delete document.')
      }
    } else if (modal.type === 'delete-folder') {
      try {
        const folderObj = backendFolders.find((f) => f.name === modal.folder)
        if (folderObj) {
          await deleteFolder(folderObj.id)
          await loadData()
          setNotice(`Folder "${modal.folder}" deleted.`)
        } else {
          setFolders((current) => current.filter((f) => f !== modal.folder))
          setNotice(`Folder "${modal.folder}" removed.`)
        }
      } catch (err) {
        setNotice(err.message || 'Cannot delete folder.')
      }
    } else if (modal.type === 'revoke-access') {
      const share = modal.share
      try {
        await revokeDocumentShare(share.documentId, share.id)
        await loadData()
        setNotice(`Access revoked for ${share.recipient}.`)
      } catch (err) {
        setNotice(err.message || 'Unable to revoke document access.')
      }
    } else {
      const form = new FormData(event.currentTarget)
      if (modal.type === 'rename-document') {
        const name = String(form.get('name') || '').trim()
        if (!name) return
        try {
          if (modal.document.rawDoc?.id) {
            await updateDocument(modal.document.rawDoc.id, { name })
            await loadData()
          } else {
            setDocuments((current) => current.map((document) => document.id === modal.document.id ? { ...document, name } : document))
          }
          record('Renamed', modal.document, `Renamed to ${name}`)
          setNotice('Document renamed.')
        } catch (err) {
          setNotice(err.message || 'Failed to rename document.')
        }
      } else if (modal.type === 'edit-document') {
        const name = String(form.get('name') || '').trim()
        const description = String(form.get('description') || '')
        const category = String(form.get('category') || modal.document.category)
        const targetFolder = category ? await getOrCreateFolder(category) : null
        try {
          if (modal.document.rawDoc?.id) {
            await updateDocument(modal.document.rawDoc.id, {
              name,
              description,
              folder: targetFolder ? targetFolder.id : null,
            })
            await loadData()
          } else {
            setDocuments((current) => current.map((document) => document.id === modal.document.id ? { ...document, name, description, category } : document))
          }
          record('Edited', modal.document, 'Updated document details')
          setNotice('Document details updated.')
        } catch (err) {
          setNotice(err.message || 'Failed to update document.')
        }
      } else if (modal.type === 'create-folder' || modal.type === 'rename-folder') {
        const name = String(form.get('name') || '').trim()
        if (!name) return
        if (modal.type === 'create-folder') {
          if (folders.some((folder) => folder.toLowerCase() === name.toLowerCase())) {
            setNotice('A folder with that name already exists.')
            return
          }
          try {
            await createFolder(name)
            await loadData()
            setNotice(`Folder "${name}" created.`)
          } catch (err) {
            setNotice(err.message || 'Failed to create folder.')
          }
        } else {
          try {
            const folderObj = backendFolders.find((f) => f.name === modal.folder)
            if (folderObj) {
              await renameFolder(folderObj.id, name)
              await loadData()
            } else {
              setFolders((current) => current.map((folder) => folder === modal.folder ? name : folder))
              setDocuments((current) => current.map((document) => document.folder === modal.folder ? { ...document, folder: name } : document))
            }
            setNotice(`Folder renamed to "${name}".`)
          } catch (err) {
            setNotice(err.message || 'Failed to rename folder.')
          }
        }
      } else if (modal.type === 'grant-access') {
          const selectedRecipientId = Number(form.get('recipient'))
          const selectedRecipient = shareRecipients.find((item) => item.id === selectedRecipientId)
          const targetDoc = (permissionDocument && ownedDocuments.some((d) => String(d.id) === String(permissionDocument.id))) ? permissionDocument : currentDocument
          if (!targetDoc?.rawDoc?.id || !selectedRecipient) {
            setNotice('Choose an active employee from the available share recipients.')
            return
          }
          const expiry = String(form.get('expiry') || '')
          const permission = String(form.get('permission') || 'Read')
          const expiresAt = expiry ? new Date(`${expiry}T23:59:59`).toISOString() : null
          if (expiresAt && new Date(expiresAt) <= new Date()) {
            setNotice('Expiry date must be in the future.')
            return
          }
          const existingShare = shares.find((share) => String(share.documentId) === String(targetDoc.id) && share.recipientId === selectedRecipient.id && share.status === 'Active')
          try {
            await createDocumentShare(targetDoc.rawDoc.id, {
              recipient: selectedRecipient.id,
              permission: permission === 'Edit' ? 'EDIT' : permission === 'Download' ? 'DOWNLOAD' : 'VIEW',
              expires_at: expiresAt,
            })
            await loadData()
            setNotice(existingShare ? `Access updated for ${selectedRecipient.display_name}.` : `Access granted to ${selectedRecipient.display_name}.`)
          } catch (err) {
            setNotice(err.message || 'Unable to grant document access.')
            return
          }
      }
    }
    setModal(null)
  }

  async function moveDocument(event) {
    event.preventDefault()
    const destination = moveDestination
    if (!destination || !currentDocument) return
    try {
      const documentId = currentDocument.rawDoc?.id
      if (!documentId) throw new Error('This document is no longer available. Refresh and try again.')
      const targetFolder = await getOrCreateFolder(String(destination))
      await updateDocument(documentId, { folder: targetFolder.id })
      const refresh = await loadData()
      record('Moved', currentDocument, `Moved to folder ${String(destination)}`)
      let message = refresh.ok
        ? `${currentDocument.name} moved to ${String(destination)}.`
        : `${currentDocument.name} moved, but the document list could not be refreshed: ${refresh.error}`
      if (refresh.storageError) message += ` Storage usage could not be refreshed: ${refresh.storageError}`
      setNotice(message)
    } catch (err) {
      setNotice(err.message || 'Failed to move document.')
    }
  }

  async function saveProfile(event) {
    event.preventDefault()
    const name = profileDraft.name.trim()
    const email = profileDraft.email.trim()
    if (!name || !email) {
      setNotice('Enter a full name and valid email address.')
      return
    }

    try {
      const updatedProfile = await updateProfile({ name, email })
      const updatedName = updatedProfile.display_name || [updatedProfile.first_name, updatedProfile.last_name].filter(Boolean).join(' ') || updatedProfile.username
      const savedProfile = { name: updatedName, email: updatedProfile.email }
      setProfile(savedProfile)
      setProfileDraft(savedProfile)
      setDocuments((current) => current.map((document) => document.owner === profile.name ? { ...document, owner: updatedName } : document))
      setNotice('Profile updated successfully.')
    } catch (err) {
      setNotice(err.message || 'Failed to update profile.')
    }
  }

  async function changePassword(event) {
    event.preventDefault()
    if (password.next.length < 12) {
      setNotice('New password must contain at least 12 characters.')
    } else if (password.next !== password.confirm) {
      setNotice('New password and confirmation do not match.')
    } else {
      try {
        await changePasswordService({
          currentPassword: password.current,
          newPassword: password.next,
          confirmPassword: password.confirm,
        })
        setNotice('Password changed successfully.')
        setPassword({ current: '', next: '', confirm: '' })
      } catch (error) {
        setNotice(error.message || 'Unable to change password.')
      }
    }
  }

  function exportActivity(rows) {
    const lines = [['Timestamp', 'User', 'Action', 'Document', 'Details', 'Result'], ...rows.map((item) => [item.timestamp, item.user, item.action, documents.find((document) => document.id === item.documentId)?.name || item.documentName || '', item.details, item.result])]
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
    const document = documents.find((item) => String(item.id) === String(share.documentId))
    return `${document?.name || ''} ${share.recipient} ${share.email}`.toLowerCase().includes(sharedFilters.query.toLowerCase()) &&
      (sharedFilters.recipient === 'All recipients' || share.recipient === sharedFilters.recipient) &&
      (sharedFilters.permission === 'All' || share.permission === sharedFilters.permission)
  })
  const visibleActivity = activity.filter((item) => {
    const document = documents.find((doc) => doc.id === item.documentId)
    const docName = document?.name || item.documentName || ''
    return `${item.user} ${item.action} ${docName} ${item.details}`.toLowerCase().includes(activityFilters.query.toLowerCase()) &&
      (activityFilters.action === 'All actions' || item.action === activityFilters.action) &&
      (activityFilters.document === 'All documents' || docName === activityFilters.document) &&
      (!activityFilters.date || new Date(item.timestamp) >= new Date(activityFilters.date))
  })

  function renderDocuments() {
    return <Panel className="p-3 sm:p-4">
      <form onSubmit={applyDocumentFilters} className="mb-4 grid items-end gap-3 sm:grid-cols-2 xl:grid-cols-[1.4fr_0.8fr_0.8fr_auto_auto]">
        <Field label="Search Documents"><span className="relative block"><Search size={15} className="absolute left-3 top-3 text-slate-400" /><TextInput className="pl-9" placeholder="Search by document name" value={query} onChange={(event) => setQuery(event.target.value)} /></span></Field>
        <Field label="Category"><SelectInput value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}><option>All categories</option>{availableCategories.map((category) => <option key={category}>{category}</option>)}</SelectInput></Field>
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
            <td className="relative px-2 py-2.5">
              <div className="flex gap-1.5">
                <ActionButton onClick={() => openPreview(document)}><Eye size={13} /> Preview</ActionButton>
                <ActionButton onClick={() => downloadDocument(document)}><Download size={13} /> Download</ActionButton>
                <ActionButton
                  aria-expanded={moreActions === document.id}
                  aria-haspopup="true"
                  onClick={(event) => {
                    if (moreActions === document.id) {
                      setMoreActions(null)
                      setMoreActionsAnchor(null)
                    } else {
                      setMoreActions(document.id)
                      setMoreActionsAnchor(event.currentTarget)
                    }
                  }}
                >
                  <SlidersHorizontal size={13} /> More Actions
                </ActionButton>
              </div>
              {moreActions === document.id && moreActionsAnchor && (
                <MoreActionsDropdown
                  anchorEl={moreActionsAnchor}
                  onClose={() => {
                    setMoreActions(null)
                    setMoreActionsAnchor(null)
                  }}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setModal({ type: 'edit-document', document })
                      setMoreActions(null)
                      setMoreActionsAnchor(null)
                    }}
                    className="rounded-lg px-3 py-2 text-left text-xs hover:bg-emerald-50"
                  >
                    <Pencil size={13} className="mr-2 inline" />Edit Details
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setModal({ type: 'rename-document', document })
                      setMoreActions(null)
                      setMoreActionsAnchor(null)
                    }}
                    className="rounded-lg px-3 py-2 text-left text-xs hover:bg-emerald-50"
                  >
                    <Pencil size={13} className="mr-2 inline" />Rename
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedDocumentId(document.id)
                      navigate('/employee/permissions')
                      setMoreActions(null)
                      setMoreActionsAnchor(null)
                    }}
                    className="rounded-lg px-3 py-2 text-left text-xs hover:bg-emerald-50"
                  >
                    <LockKeyhole size={13} className="mr-2 inline" />Manage Permissions
                  </button>
                  {document.status === 'archived' ? (
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          if (document.rawDoc?.id) await restoreDocService(document.rawDoc.id)
                          await loadData()
                          record('Restored', document, 'Restored document to active')
                          setNotice(`${document.name} restored.`)
                        } catch (e) {
                          setNotice(e.message)
                        }
                        setMoreActions(null)
                        setMoreActionsAnchor(null)
                      }}
                      className="rounded-lg px-3 py-2 text-left text-xs hover:bg-emerald-50"
                    >
                      <History size={13} className="mr-2 inline" />Restore
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          if (document.rawDoc?.id) await archiveDocService(document.rawDoc.id)
                          await loadData()
                          record('Archived', document, 'Archived document')
                          setNotice(`${document.name} archived.`)
                        } catch (e) {
                          setNotice(e.message)
                        }
                        setMoreActions(null)
                        setMoreActionsAnchor(null)
                      }}
                      className="rounded-lg px-3 py-2 text-left text-xs hover:bg-emerald-50"
                    >
                      <Database size={13} className="mr-2 inline" />Archive
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      setModal({ type: 'delete-document', document })
                      setMoreActions(null)
                      setMoreActionsAnchor(null)
                    }}
                    className="rounded-lg px-3 py-2 text-left text-xs text-rose-700 hover:bg-rose-50"
                  >
                    <Trash2 size={13} className="mr-2 inline" />Delete Document
                  </button>
                </MoreActionsDropdown>
              )}
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
        <Field label="Category"><SelectInput value={upload.category} onChange={(event) => setUpload({ ...upload, category: event.target.value })}>{availableCategories.map((category) => <option key={category}>{category}</option>)}</SelectInput></Field>
        <Field label="Description (optional)"><textarea value={upload.description} onChange={(event) => setUpload({ ...upload, description: event.target.value })} className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-emerald-600" rows="3" placeholder="Short description" /></Field>
        <ActionButton type="submit" variant="primary"><Upload size={14} /> Upload Document</ActionButton>
      </form></Panel>
      <div className="space-y-4"><Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><FileText size={17} /> Selected File</h2>{selectedFile ? <><p className="text-sm text-slate-600">File type: {selectedFile.name.split('.').pop()?.toUpperCase()}</p><p className="mt-1 text-sm text-slate-600">Size: {formatFileSize(selectedFile.size)}</p><div className="mt-3 h-2 rounded-full bg-slate-200"><div className="h-full w-full rounded-full bg-emerald-700" /></div><p className="mt-2 text-xs text-emerald-800">Ready to upload</p></> : <p className="text-sm text-slate-500">Choose a file to see its details here.</p>}<h3 className="mt-4 font-semibold"><Check size={15} className="mr-1 inline" /> Upload Rules</h3><ul className="mt-2 space-y-1 text-sm text-slate-500"><li>Allowed: PDF, DOCX, XLSX, PPTX</li><li>Maximum size: 50 MB</li><li>Files are checked before upload.</li></ul></Panel>{notice && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">{notice}</p>}</div>
    </div>
  }

  function renderFolders() {
    const owned = ownedDocuments
    const selectedFolder = new URLSearchParams(location.search).get('folder')
    const folderDocuments = selectedFolder ? owned.filter((document) => document.folder === selectedFolder) : []
    return <div className="space-y-4">
      <Panel><div className="grid items-end gap-3 sm:grid-cols-[1fr_auto_auto]"><Field label="Search Folders"><span className="relative block"><Search size={15} className="absolute left-3 top-3 text-slate-400" /><TextInput className="pl-9" placeholder="Search folders or documents" value={query} onChange={(event) => setQuery(event.target.value)} /></span></Field><ActionButton onClick={() => setNotice('Folder filters applied.') }><Filter size={14} /> Apply Filters</ActionButton><ActionButton variant="primary" onClick={() => setModal({ type: 'create-folder' })}><Plus size={14} /> Create Folder</ActionButton></div></Panel>
      {notice && <p role="status" className="rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-900">{notice}</p>}
      {selectedFolder && (
        <Panel id="selected-folder-view" className="border border-emerald-200/80 bg-white shadow-sm">
          <div className="mb-3 flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2.5">
              <span className="inline-flex rounded-xl bg-teal-100 p-2 text-teal-800"><Folder size={18} /></span>
              <div>
                <h2 className="text-base font-bold text-slate-800">{selectedFolder}</h2>
                <p className="text-xs text-slate-500">{folderDocuments.length} document{folderDocuments.length === 1 ? '' : 's'} in this folder</p>
              </div>
            </div>
            <ActionButton onClick={() => navigate('/employee/folders')}><X size={13} /> Close folder</ActionButton>
          </div>
          <div className="space-y-2">
            {folderDocuments.length ? (
              folderDocuments.map((document) => (
                <div key={document.id} className="flex items-center justify-between gap-3 border-t border-slate-100 py-2 text-sm first:border-0 first:pt-0">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText size={15} className="shrink-0 text-slate-400" />
                    <span className="truncate font-medium text-slate-700">{document.name}</span>
                  </div>
                  <ActionButton onClick={() => openPreview(document)}><Eye size={13} /> Preview</ActionButton>
                </div>
              ))
            ) : (
              <p className="py-2 text-sm text-slate-500">This folder is empty.</p>
            )}
          </div>
        </Panel>
      )}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{folders.filter((folder) => `${folder} ${owned.filter((document) => document.folder === folder).map((document) => document.name).join(' ')}`.toLowerCase().includes(query.toLowerCase())).map((folder) => <Panel key={folder} className={folder === selectedFolder ? 'ring-2 ring-emerald-600/70 border-emerald-300' : ''}><span className="mb-3 inline-flex rounded-xl bg-teal-100 p-2.5 text-teal-800"><Folder size={19} /></span><h2 className="font-semibold">{folder}</h2><p className="mt-1 text-xs text-slate-500">{owned.filter((document) => document.folder === folder).length} documents</p><div className="mt-3 flex flex-wrap gap-1.5"><ActionButton variant="primary" onClick={() => navigate(`/employee/folders?folder=${encodeURIComponent(folder)}`)}><Folder size={13} /> {folder === selectedFolder ? 'Viewing' : 'Open Folder'}</ActionButton><ActionButton onClick={() => setModal({ type: 'rename-folder', folder })}><Pencil size={13} /> Rename</ActionButton><ActionButton variant="danger" onClick={() => setModal({ type: 'delete-folder', folder })}><Trash2 size={13} /> Delete</ActionButton></div></Panel>)}</div>
      <Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Settings2 size={16} /> Move Document</h2><form onSubmit={moveDocument} className="grid items-end gap-3 md:grid-cols-[1fr_1fr_auto]"><Field label="Document"><SelectInput value={selectedDocumentId} onChange={(event) => setSelectedDocumentId(event.target.value)}>{owned.map((document) => <option key={document.id} value={document.id}>{document.name}</option>)}</SelectInput></Field><Field label="Move to folder"><SelectInput name="folder" value={moveDestination} onChange={(event) => setMoveDestination(event.target.value)}>{availableCategories.map((folder) => <option key={folder}>{folder}</option>)}</SelectInput></Field><ActionButton variant="primary" type="submit" disabled={!currentDocument}><SlidersHorizontal size={13} /> Move Document</ActionButton></form><p className="mt-3 text-[11px] text-slate-500">Moving a document to a folder never changes who can access it.</p></Panel>
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
      {sharesLoadError && <p role="alert" className="mb-3 text-sm text-rose-700">{sharesLoadError}</p>}
      <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-xs">
        <thead><tr className="border-b border-slate-200 text-slate-500">{['Document', 'Recipient', 'Permission', 'Date Shared', 'Status', 'Actions'].map((heading) => <th key={heading} className="px-2 py-3">{heading}</th>)}</tr></thead>
        <tbody>{visibleShares.map((share) => {
          const document = documents.find((item) => String(item.id) === String(share.documentId))
          return <tr key={share.id} className="border-b border-slate-100 last:border-0">
            <td className="px-2 py-3 font-semibold">{document?.name || 'Deleted document'}</td>
            <td className="px-2 py-3">{share.recipient}<span className="mt-1 block text-[10px] text-slate-500">{share.email}</span></td>
            <td className="px-2 py-3"><Badge tone={share.permission === 'Edit' ? 'amber' : share.permission === 'Download' ? 'purple' : 'blue'}>{share.permission}</Badge></td>
            <td className="whitespace-nowrap px-2 py-3">{share.date}<span className="mt-1 block text-[10px] text-slate-500">{share.expiry ? `Expires: ${share.expiry}` : 'No expiration'}</span></td>
            <td className="px-2 py-3"><Badge tone={share.status === 'Active' ? 'green' : 'red'}>{share.status}</Badge></td>
            <td className="px-2 py-3"><ActionButton onClick={() => { setSelectedDocumentId(share.documentId); navigate('/employee/permissions') }}><LockKeyhole size={13} /> Manage Permissions</ActionButton></td>
          </tr>
        })}
        {visibleShares.length === 0 && !sharesLoadError && <tr><td colSpan="6" className="px-4 py-10 text-center text-slate-500">No sharing records found.</td></tr>}
        </tbody>
      </table></div>
      <p className="mt-3 text-xs text-slate-500">Active and expired access grants are shown.</p>
      {notice && <p role="status" className="mt-3 text-sm text-emerald-800">{notice}</p>}
    </Panel>
  }

  function renderReceivedDocuments() {
    const received = sharedDocuments
    const filtered = received.filter((document) => `${document.name} ${document.owner} ${document.category}`.toLowerCase().includes(query.toLowerCase()))
    return <Panel><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><Field label="Search shared documents" className="min-w-[220px] flex-1"><span className="relative block"><Search size={15} className="absolute left-3 top-3 text-slate-400" /><TextInput className="pl-9" placeholder="Search by document or owner" value={query} onChange={(event) => setQuery(event.target.value)} /></span></Field><span className="text-xs text-slate-500">Your actions depend on the access granted by the owner.</span></div><div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-xs"><thead><tr className="border-b border-slate-200 text-slate-500">{['Document', 'Owner', 'Category', 'Type', 'Modified', 'Actions'].map((heading) => <th key={heading} className="px-2 py-3">{heading}</th>)}</tr></thead><tbody>{filtered.map((document) => <tr key={document.id} className="border-b border-slate-100"><td className="px-2 py-3 font-semibold">{document.name}</td><td className="px-2 py-3">{document.owner}</td><td className="px-2 py-3">{document.category}</td><td className="px-2 py-3">{document.type}</td><td className="px-2 py-3">{document.modified}</td><td className="px-2 py-3"><div className="flex gap-1.5"><ActionButton onClick={() => openPreview(document)}><Eye size={13} /> Preview</ActionButton>{['DOWNLOAD', 'EDIT'].includes(document.permission) && <ActionButton onClick={() => downloadDocument(document)}><Download size={13} /> Download</ActionButton>}<ActionButton onClick={() => { setSelectedDocumentId(document.id); navigate('/employee/permissions') }}><LockKeyhole size={13} /> View Access</ActionButton></div></td></tr>)}{filtered.length === 0 && <tr><td colSpan="6" className="px-4 py-10 text-center text-slate-500">No documents have been shared with you.</td></tr>}</tbody></table></div></Panel>
  }

  function renderPermissions() {
    const ownsPermissionDocument = Boolean(permissionDocument && ownedDocuments.some((d) => String(d.id) === String(permissionDocument.id)))
    const receivedShare = sharedDocuments.find((document) => String(document.id) === String(permissionDocument?.id))
    const availableDocsForPermissions = [...ownedDocuments, ...sharedDocuments]
    const documentShares = [
      ...(permissionDocument ? [{
        id: `owner-${permissionDocument.id}`,
        recipient: ownsPermissionDocument ? (profile.name || 'You') : (permissionDocument.owner || 'Owner'),
        email: ownsPermissionDocument ? profile.email : (permissionDocument.owner_email || permissionDocument.rawDoc?.owner_email || '—'),
        permission: 'Owner',
        status: 'Active',
        owner: true,
        isSelf: ownsPermissionDocument,
      }] : []),
      ...(!ownsPermissionDocument && receivedShare ? [{
        id: `received-${receivedShare.rawDoc?.share_id || receivedShare.id}`,
        recipient: profile.name || 'You',
        email: profile.email,
        permission: receivedShare.permission === 'EDIT' ? 'Edit' : receivedShare.permission === 'DOWNLOAD' ? 'Download' : 'Read',
        status: (receivedShare.rawDoc?.expires_at && new Date(receivedShare.rawDoc.expires_at) <= new Date()) ? 'Expired' : 'Active',
        grantor: receivedShare.owner,
        isSelf: true,
      }] : []),
      ...(ownsPermissionDocument ? shares.filter((share) => String(share.documentId) === String(permissionDocument?.id)) : []),
    ]

    async function refreshCurrentAccess() {
      if (!permissionDocument) return
      setAccessLoading(true)
      setSharesLoadError('')
      try {
        if (ownsPermissionDocument) {
          const freshShares = await listDocumentShares(permissionDocument.id)
          const recipientsById = new Map(shareRecipients.map((recipient) => [recipient.id, recipient]))
          setShares((current) => [
            ...current.filter((share) => String(share.documentId) !== String(permissionDocument.id)),
            ...freshShares.map((share) => ({
              id: share.id,
              documentId: share.document,
              recipient: share.recipient_name || share.recipient_username,
              email: share.recipient_email || recipientsById.get(share.recipient)?.email || '',
              recipientId: share.recipient,
              permission: share.permission === 'EDIT' ? 'Edit' : share.permission === 'DOWNLOAD' ? 'Download' : 'Read',
              date: new Date(share.created_at).toLocaleDateString(),
              status: share.expires_at && new Date(share.expires_at) <= new Date() ? 'Expired' : 'Active',
              expiry: share.expires_at ? new Date(share.expires_at).toISOString().slice(0, 10) : '',
            })),
          ])
          setNotice(`Current access refreshed for ${permissionDocument.name}.`)
        } else {
          const refreshed = await listSharedDocuments()
          const currentShare = (refreshed?.results || []).find((share) => String(share.id) === String(permissionDocument.id))
          if (!currentShare) throw new Error('This document is no longer shared with your account.')
          setSharedDocuments((current) => current.map((document) => String(document.id) === String(currentShare.id) ? {
            ...document,
            permission: currentShare.permission,
            owner: currentShare.owner_name,
            owner_email: currentShare.owner_email || '',
            rawDoc: currentShare,
          } : document))
          try {
            const freshShares = await listDocumentShares(permissionDocument.id)
            const recipientsById = new Map(shareRecipients.map((recipient) => [recipient.id, recipient]))
            setShares((current) => [
              ...current.filter((share) => String(share.documentId) !== String(permissionDocument.id)),
              ...freshShares.map((share) => ({
                id: share.id,
                documentId: share.document,
                recipient: share.recipient_name || share.recipient_username,
                email: share.recipient_email || recipientsById.get(share.recipient)?.email || '',
                recipientId: share.recipient,
                permission: share.permission === 'EDIT' ? 'Edit' : share.permission === 'DOWNLOAD' ? 'Download' : 'Read',
                date: new Date(share.created_at).toLocaleDateString(),
                status: share.expires_at && new Date(share.expires_at) <= new Date() ? 'Expired' : 'Active',
                expiry: share.expires_at ? new Date(share.expires_at).toISOString().slice(0, 10) : '',
              })),
            ])
          } catch {
            // Safe fallback: recipient share info is already provided by listSharedDocuments
          }
          setNotice(`Current access refreshed for ${permissionDocument.name}.`)
        }
      } catch (error) {
        setSharesLoadError(error.message || 'Unable to load current access.')
      } finally {
        setAccessLoading(false)
      }
    }

    return <div className="space-y-3">
      {permissionDocument && <Panel className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="rounded-xl bg-rose-50 p-3 text-rose-700"><FileText size={20} /></span>
          <div>
            <h2 className="font-semibold">{permissionDocument.name}</h2>
            <p className="text-xs text-slate-500">Owner: {permissionDocument.owner} · Category: {permissionDocument.category} · Size: {permissionDocument.size} · Uploaded: {permissionDocument.modified}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {availableDocsForPermissions.length > 1 && (
            <Field label="Document" className="w-56">
              <SelectInput value={permissionDocument.id} onChange={(event) => setSelectedDocumentId(event.target.value)}>
                {ownedDocuments.length > 0 && (
                  <optgroup label="My Documents">
                    {ownedDocuments.map((doc) => <option key={doc.id} value={doc.id}>{doc.name}</option>)}
                  </optgroup>
                )}
                {sharedDocuments.length > 0 && (
                  <optgroup label="Shared with Me">
                    {sharedDocuments.map((doc) => <option key={doc.id} value={doc.id}>{doc.name}</option>)}
                  </optgroup>
                )}
              </SelectInput>
            </Field>
          )}
          {permissionDocument.rawDoc?.id && <ActionButton onClick={() => openPreview(permissionDocument)}><Eye size={13} /> Preview Document</ActionButton>}
        </div>
      </Panel>}
      <div className="grid items-start gap-3 xl:grid-cols-[1.5fr_0.8fr]">
        <Panel>
          <div className="mb-3 flex flex-wrap gap-2">
            <ActionButton variant="primary" onClick={refreshCurrentAccess} disabled={accessLoading}>
              <UsersIcon /> {accessLoading ? 'Loading Access' : 'Current Access'}
            </ActionButton>
            <ActionButton onClick={() => navigate('/employee/activity')}>
              <History size={13} /> View Permission History
            </ActionButton>
          </div>
          {sharesLoadError && <p role="alert" className="mb-3 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-700">{sharesLoadError}</p>}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-xs">
              <thead><tr className="border-b border-slate-200 text-slate-500">{['User', 'Email', 'Permission', 'Status', 'Actions'].map((heading) => <th key={heading} className="px-2 py-3">{heading}</th>)}</tr></thead>
              <tbody>
                {accessLoading ? (
                  <tr><td colSpan="5" className="px-3 py-8 text-center text-slate-500">Loading current access...</td></tr>
                ) : (
                  documentShares.map((share) => (
                    <tr key={share.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-2 py-3 font-semibold">{share.recipient}{share.isSelf && <span className="ml-1 text-[10px] font-normal text-slate-500">(You)</span>}</td>
                      <td className="px-2 py-3">{share.email}</td>
                      <td className="px-2 py-3"><Badge tone={share.permission === 'Owner' ? 'green' : share.permission === 'Edit' ? 'amber' : share.permission === 'Download' ? 'purple' : 'blue'}>{share.permission}</Badge></td>
                      <td className="px-2 py-3"><Badge tone={share.status === 'Active' ? 'green' : 'red'}>{share.status}</Badge></td>
                      <td className="px-2 py-3">{!share.owner && ownsPermissionDocument && <ActionButton variant="danger" onClick={() => setModal({ type: 'revoke-access', share })}><LockKeyhole size={13} /> Revoke Access</ActionButton>}</td>
                    </tr>
                  ))
                )}
                {!accessLoading && documentShares.length === 0 && (
                  <tr><td colSpan="5" className="px-3 py-8 text-center text-slate-500">{permissionDocument ? 'No access has been granted to this document.' : 'No document selected or available.'}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
        <div className="space-y-3">
          {ownsPermissionDocument && (
            <Panel>
              <h2 className="mb-3 flex items-center gap-2 font-bold"><Plus size={16} /> Grant Access</h2>
              <form onSubmit={(event) => { event.preventDefault(); setModal({ type: 'grant-access' }); window.requestAnimationFrame(() => document.getElementById('grant-access-email')?.focus()) }} className="space-y-3">
                <Field label="Document"><SelectInput value={permissionDocument?.id || selectedDocumentId} onChange={(event) => setSelectedDocumentId(event.target.value)}>{ownedDocuments.map((document) => <option key={document.id} value={document.id}>{document.name}</option>)}</SelectInput></Field>
                <p className="text-xs text-slate-500">Choose a document and use the secure grant form to add a person.</p>
                <ActionButton type="submit" variant="primary"><Plus size={13} /> Grant Access</ActionButton>
              </form>
            </Panel>
          )}
          {ownsPermissionDocument && (
            <Panel className="bg-teal-50">
              <h3 className="mb-2 text-sm font-bold">Permission Levels</h3>
              <p className="text-xs text-slate-600"><Badge tone="blue">Read</Badge> View the document without downloading.</p>
              <p className="mt-2 text-xs text-slate-600"><Badge tone="purple">Download</Badge> View and download the document.</p>
              <p className="mt-2 text-xs text-slate-600"><Badge tone="amber">Edit</Badge> View, download and modify. Cannot share, delete, or transfer ownership.</p>
            </Panel>
          )}
        </div>
      </div>
      {notice && <p role="status" className="rounded-lg bg-emerald-50 p-2.5 text-xs text-emerald-900">{notice}</p>}
    </div>
  }

  function renderActivity() {
    const actions = [...new Set(activity.map((item) => item.action))]
    return <div className="space-y-3"><div className="grid grid-cols-2 gap-3 xl:grid-cols-5">{[['Uploads', activity.filter((item) => item.actionCode === 'DOCUMENT_UPLOAD').length, Upload, 'blue'], ['Downloads', activity.filter((item) => item.actionCode === 'DOCUMENT_DOWNLOAD').length, Download, 'teal'], ['Edits', activity.filter((item) => item.actionCode === 'DOCUMENT_UPDATE').length, Pencil, 'amber'], ['Permission Changes', activity.filter((item) => item.actionCode?.startsWith('DOCUMENT_SHARE')).length, LockKeyhole, 'purple'], ['Deletions', activity.filter((item) => item.actionCode === 'DOCUMENT_DELETE').length, Trash2, 'rose']].map(([label, value, Icon, color]) => <Panel key={label}><div className="flex items-center gap-3"><span className={`rounded-xl p-2.5 ${color === 'rose' ? 'bg-rose-100 text-rose-700' : color === 'amber' ? 'bg-amber-100 text-amber-800' : color === 'purple' ? 'bg-violet-100 text-violet-700' : color === 'blue' ? 'bg-blue-100 text-blue-700' : 'bg-teal-100 text-teal-700'}`}><Icon size={17} /></span><div><p className="text-xs text-slate-500">{label}</p><p className="text-xl font-bold">{value}</p></div></div></Panel>)}</div>
      <Panel><div className="mb-4 grid items-end gap-3 sm:grid-cols-2 xl:grid-cols-[1.2fr_0.7fr_0.8fr_0.8fr_auto]">
        <Field label="Search Activity"><TextInput placeholder="Search by document or user" value={activityFilters.query} onChange={(event) => setActivityFilters({ ...activityFilters, query: event.target.value })} /></Field>
        <Field label="Action"><SelectInput value={activityFilters.action} onChange={(event) => setActivityFilters({ ...activityFilters, action: event.target.value })}><option>All actions</option>{actions.map((action) => <option key={action}>{action}</option>)}</SelectInput></Field>
        <Field label="Document"><SelectInput value={activityFilters.document} onChange={(event) => setActivityFilters({ ...activityFilters, document: event.target.value })}><option>All documents</option>{documents.map((document) => <option key={document.id}>{document.name}</option>)}</SelectInput></Field>
        <Field label="From date"><TextInput type="date" value={activityFilters.date} onChange={(event) => setActivityFilters({ ...activityFilters, date: event.target.value })} /></Field>
        <ActionButton onClick={() => setNotice('Activity filters applied.')}><Filter size={14} /> Apply Filters</ActionButton>
      </div><div className="mb-3"><ActionButton variant="primary" onClick={() => exportActivity(visibleActivity)}><Download size={13} /> Export Activity</ActionButton></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-xs"><thead><tr className="border-b border-slate-200 text-slate-500">{['Timestamp', 'User', 'Action', 'Document', 'Details', 'Result'].map((heading) => <th key={heading} className="px-2 py-3">{heading}</th>)}</tr></thead><tbody>{visibleActivity.map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="whitespace-nowrap px-2 py-3">{new Date(item.timestamp).toLocaleString()}</td><td className="px-2 py-3">{item.user}</td><td className="px-2 py-3">{item.action}</td><td className="px-2 py-3 font-semibold">{documents.find((document) => document.id === item.documentId)?.name || item.documentName || '—'}</td><td className="px-2 py-3">{item.details}</td><td className="px-2 py-3"><Badge tone={item.result === 'Success' ? 'green' : 'red'}>{item.result}</Badge></td></tr>)}{visibleActivity.length === 0 && <tr><td colSpan="6" className="px-4 py-8 text-center text-slate-500">No activities match these filters.</td></tr>}</tbody></table></div><p className="mt-3 text-xs text-slate-500">Showing {visibleActivity.length} of {activity.length} activities.</p></Panel></div>
  }

  function renderProfile() {
    return <div className="grid items-start gap-4 xl:grid-cols-2">    <Panel><h2 className="mb-4 flex items-center gap-2 font-bold"><UserRound size={17} /> Account Details</h2><p className="text-sm text-slate-500">Role: Employee</p><p className="mt-1 text-sm text-slate-500">Status: <Badge>{accountStatus || '—'}</Badge></p><form onSubmit={saveProfile} className="mt-4 space-y-3"><Field label="Full name"><TextInput required value={profileDraft.name} onChange={(event) => setProfileDraft({ ...profileDraft, name: event.target.value })} /></Field><Field label="Email"><TextInput required type="email" value={profileDraft.email} onChange={(event) => setProfileDraft({ ...profileDraft, email: event.target.value })} /></Field><p className="text-[11px] text-slate-500">Email changes are saved to your account.</p><ActionButton type="submit" variant="primary"><Check size={14} /> Update Profile</ActionButton></form></Panel>
      <Panel><h2 className="mb-4 flex items-center gap-2 font-bold"><LockKeyhole size={17} /> Change Password</h2><form onSubmit={changePassword} className="space-y-3">{[['Current Password', 'current'], ['New Password', 'next'], ['Confirm New Password', 'confirm']].map(([label, key]) => <Field key={key} label={label}><span className="flex gap-2"><TextInput required type={passwordVisible ? 'text' : 'password'} value={password[key]} onChange={(event) => setPassword({ ...password, [key]: event.target.value })} placeholder={`Enter ${label.toLowerCase()}`} /><button type="button" onClick={() => setPasswordVisible(!passwordVisible)} aria-label={passwordVisible ? 'Hide passwords' : 'Show passwords'} className="rounded-full border border-slate-200 px-3 text-emerald-800"><Eye size={16} /></button></span></Field>)}<p className="text-[11px] text-slate-500">Use at least 12 characters.</p><ActionButton type="submit" variant="primary"><Check size={14} /> Change Password</ActionButton></form></Panel>
      <Panel className="xl:col-span-2"><h2 className="mb-3 flex items-center gap-2 font-bold"><History size={17} /> Recent Account Activity</h2><div className="overflow-x-auto"><table className="w-full min-w-[500px] text-left text-xs"><thead><tr className="border-b border-slate-100 text-slate-500"><th className="py-2">Date / time</th><th className="py-2">Activity</th><th className="py-2">Result</th></tr></thead><tbody>{activity.slice(0, 3).map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="py-2">{new Date(item.timestamp).toLocaleString()}</td><td className="py-2">{item.action}</td><td className="py-2"><Badge tone={item.result === 'Success' ? 'green' : 'red'}>{item.result}</Badge></td></tr>)}</tbody></table></div></Panel></div>
  }

  function renderDashboard() {
    const stats = [
      ['Total Documents', ownedDocuments.length, FileText],
      ['Shared Documents', shares.filter((share) => share.status === 'Active').length, Share2],
      ['Recently Accessed', recentlyAccessedDocumentCount, Clock3],
      ['Storage Used', storageUsage ? (storageUsage.used_bytes ? formatFileSize(storageUsage.used_bytes) : '0 KB') : '—', Database],
    ]
    return <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{stats.map(([label, value, Icon]) => <Panel key={label}><div className="flex items-center gap-3"><span className="employee-stat-icon rounded-xl p-3"><Icon size={21} /></span><div><p className="text-sm text-slate-500">{label}</p><p className="text-2xl font-bold">{value}</p></div></div></Panel>)}</div>
      <div className="grid items-start gap-4 xl:grid-cols-[1.8fr_1fr]"><Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Activity size={17} /> Recent Activity</h2><div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left text-sm"><thead><tr className="border-b border-slate-100 text-xs text-slate-500"><th className="py-2">Action</th><th className="py-2">Document</th><th className="py-2">Time</th></tr></thead><tbody>{activity.slice(0, 4).map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="py-3">{item.action}</td><td className="py-3">{documents.find((document) => document.id === item.documentId)?.name || item.documentName || '—'}</td><td className="py-3">{new Date(item.timestamp).toLocaleTimeString()}</td></tr>)}</tbody></table></div></Panel><Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Plus size={17} /> Quick Actions</h2><div className="grid gap-2"><ActionButton variant="primary" className="w-full py-3 text-sm" onClick={() => navigate('/employee/upload')}><Upload size={15} /> Upload Document</ActionButton><ActionButton className="w-full py-3 text-sm" onClick={() => navigate('/employee/documents')}><FileText size={15} /> My Documents</ActionButton><ActionButton className="w-full py-3 text-sm" onClick={() => navigate('/employee/permissions')}><LockKeyhole size={15} /> Manage Permissions</ActionButton></div></Panel></div>
      <Panel><h2 className="mb-3 flex items-center gap-2 font-bold"><Bell size={17} /> Notifications</h2><div className="space-y-2">{notifications.length > 0 ? notifications.map((item) => <p key={item.id} className={`flex items-start gap-2 text-sm ${item.read ? 'text-slate-500' : 'text-slate-700'}`}><Share2 size={15} className="mt-0.5 shrink-0" />{item.message}</p>) : <p className="text-sm text-slate-500">No notifications at this time.</p>}</div></Panel>
    </div>
  }

  function renderModal() {
    if (!modal || modal.type === 'logout') return null
    if (modal.type === 'preview') {
      const canDownload = modal.document.owner === profile.name ||
        ['DOWNLOAD', 'EDIT'].includes(modal.document.rawDoc?.permission)
      return <Modal title={modal.document.name} onClose={() => setModal(null)}><div className="rounded-xl bg-slate-50 p-6"><p className="text-sm text-slate-600">{modal.document.description || 'No description provided.'}</p><dl className="mt-4 grid grid-cols-2 gap-3 text-xs"><div><dt className="text-slate-500">Category</dt><dd className="mt-1 font-semibold">{modal.document.category}</dd></div><div><dt className="text-slate-500">Type / size</dt><dd className="mt-1 font-semibold">{modal.document.type} · {modal.document.size}</dd></div><div><dt className="text-slate-500">Owner</dt><dd className="mt-1 font-semibold">{modal.document.owner}</dd></div><div><dt className="text-slate-500">Modified</dt><dd className="mt-1 font-semibold">{modal.document.modified}</dd></div></dl></div><div className="mt-4 flex justify-end gap-2"><ActionButton onClick={() => setModal(null)}>Close</ActionButton>{canDownload && <ActionButton variant="primary" onClick={() => downloadDocument(modal.document)}><Download size={13} /> Download</ActionButton>}</div></Modal>
    }
    const destructive = modal.type === 'delete-document' || modal.type === 'revoke-access' || modal.type === 'delete-folder'
    const titleByType = { 'rename-document': 'Rename Document', 'edit-document': 'Edit Document Details', 'delete-document': 'Delete Document?', 'delete-folder': `Delete folder "${modal.folder}"?`, 'create-folder': 'Create Folder', 'rename-folder': 'Rename Folder', 'grant-access': 'Grant Access', 'revoke-access': `Revoke access for ${modal.share?.recipient || 'user'}?` }
    return <Modal title={titleByType[modal.type]} onClose={() => setModal(null)}>
      {destructive ? <><p className="text-sm leading-relaxed text-slate-600">{modal.type === 'delete-document' ? `${modal.document.name} will be removed and everyone with access will lose it. This is recorded in the audit log.` : modal.type === 'delete-folder' ? `Folder "${modal.folder}" will be deleted. The folder must contain no documents.` : `${modal.share.recipient} will immediately lose access to ${(permissionDocument && ownedDocuments.some((d) => String(d.id) === String(permissionDocument.id))) ? permissionDocument.name : (currentDocument?.name || 'this document')}. This is recorded in the audit log.`}</p><div className="mt-5 flex justify-end gap-2"><ActionButton onClick={() => setModal(null)}>Cancel</ActionButton><ActionButton variant="danger" onClick={() => saveModal({ preventDefault() {}, currentTarget: { elements: [] } })}><Trash2 size={13} />{modal.type === 'delete-document' ? 'Delete Document' : modal.type === 'delete-folder' ? 'Delete Folder' : 'Revoke Access'}</ActionButton></div></> :
        <form onSubmit={saveModal} className="space-y-3">
          {modal.type === 'rename-document' && <Field label="Document name"><TextInput name="name" required defaultValue={modal.document.name} /></Field>}
          {modal.type === 'edit-document' && <><Field label="Document name"><TextInput name="name" required defaultValue={modal.document.name} /></Field><Field label="Category"><SelectInput name="category" defaultValue={modal.document.category}>{availableCategories.map((category) => <option key={category}>{category}</option>)}</SelectInput></Field><Field label="Description"><textarea name="description" defaultValue={modal.document.description} className="w-full rounded-xl border border-slate-200 p-3 text-sm" rows="3" /></Field></>}
          {(modal.type === 'create-folder' || modal.type === 'rename-folder') && <Field label="Folder name"><TextInput name="name" required defaultValue={modal.folder || ''} placeholder="Enter folder name" /></Field>}
          {modal.type === 'grant-access' && <><Field label="Employee"><SelectInput id="grant-access-email" name="recipient" required defaultValue=""><option value="" disabled>Select an active employee</option>{shareRecipients.map((recipient) => <option key={recipient.id} value={recipient.id}>{recipient.display_name} · {recipient.email}</option>)}</SelectInput></Field><Field label="Permission level"><SelectInput name="permission"><option>Read</option><option>Download</option><option>Edit</option></SelectInput></Field><Field label="Expiry date (optional)"><TextInput name="expiry" type="date" min={new Date().toISOString().slice(0, 10)} /></Field><p className="text-xs text-slate-500">This grants access to {(permissionDocument && ownedDocuments.some((d) => String(d.id) === String(permissionDocument.id))) ? permissionDocument.name : (currentDocument?.name || 'this document')}.</p></>}
          <div className="flex justify-end gap-2 pt-2"><ActionButton onClick={() => setModal(null)}>Cancel</ActionButton><ActionButton type="submit" variant="primary"><Check size={13} /> Save</ActionButton></div>
        </form>}
    </Modal>
  }

  function UsersIcon() {
    return <UserRound size={13} />
  }

  return <main className="employee-theme min-h-screen bg-[#ECFEFF] text-slate-800 md:flex">
    <aside className="w-full shrink-0 bg-gradient-to-b from-[#164E63] to-[#083344] p-4 text-white md:min-h-screen md:w-56">
      <button type="button" onClick={() => navigate('/employee/dashboard')} className="mb-4 flex items-center gap-2 px-2 text-lg font-bold"><ShieldCheck size={22} /> DocTrust</button>
      <div className="mb-5 w-fit rounded-full bg-white/15 px-3 py-1 text-xs"><Folder size={12} className="mr-1 inline" /> Employee</div>
      <nav aria-label="Employee navigation" className="grid grid-cols-2 gap-1 md:flex md:flex-col">{navItems.map(([label, path, Icon]) => <button key={path} type="button" aria-current={location.pathname === path ? 'page' : undefined} onClick={() => path.endsWith('/logout') ? setModal({ type: 'logout' }) : navigate(path)} className={`flex items-center gap-2 rounded-lg px-3 py-2.5 text-left text-xs transition ${location.pathname === path ? 'bg-emerald-700 font-semibold text-white' : 'text-white/80 hover:bg-white/10'}`}><Icon size={15} />{label}</button>)}</nav>
    </aside>
    <div className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8"><header className="mb-6 flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold tracking-tight">{title[0]}</h1><p className="mt-1 text-sm text-slate-500">{title[1]}</p></div><div className="flex items-center gap-2"><div className="relative"><button type="button" aria-expanded={notificationOpen} onClick={() => setNotificationOpen(!notificationOpen)} className="relative flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold text-emerald-800"><Bell size={14} /> Notifications{unreadCount > 0 && <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white">{unreadCount}</span>}</button>{notificationOpen && <div className="absolute right-0 z-30 mt-2 w-[min(90vw,330px)] rounded-xl border border-slate-100 bg-white p-3 shadow-xl"><div className="mb-2 flex items-center justify-between"><strong className="text-sm">Notifications</strong><button type="button" onClick={markAllNotificationsRead} className="text-xs font-semibold text-emerald-800">Mark all read</button></div>{notifications.map((item) => <button key={item.id} type="button" onClick={() => { markNotificationRead(item.id); setNotificationOpen(false); navigate('/employee/activity') }} className={`mb-1 block w-full rounded-lg p-2 text-left text-xs ${item.read ? 'text-slate-500' : 'bg-emerald-50 text-slate-700'}`}>{item.message}</button>)}</div>}</div><button type="button" onClick={() => navigate('/employee/profile')} className="flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-2 text-xs font-semibold"><UserRound size={14} /> Profile</button><div className="hidden items-center gap-2 sm:flex"><span className="flex size-9 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-800">{profile.name.split(' ').map((part) => part[0]).join('')}</span><div className="text-xs"><p className="font-bold">{profile.name}</p><p className="text-emerald-800">Employee</p></div></div></div></header>
      {notice && <div role="status" className="mb-4 flex items-center justify-between gap-2 rounded-xl bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">{notice}<button type="button" onClick={() => setNotice('')} aria-label="Dismiss message"><X size={15} /></button></div>}
      {page === 'documents' ? renderDocuments() : page === 'upload' ? renderUpload() : page === 'folders' ? renderFolders() : page === 'received' ? renderReceivedDocuments() : page === 'shared' ? renderShares() : page === 'permissions' ? renderPermissions() : page === 'activity' ? renderActivity() : page === 'profile' ? renderProfile() : renderDashboard()}
      <p className="mt-5 text-xs text-slate-500">DocTrust Employee Workspace. Connected to secure backend storage and audit logging.</p>
    </div>
    {renderModal()}
    {modal?.type === 'logout' && <Modal title="Sign out of DocTrust?" onClose={() => setModal(null)}><p className="text-sm text-slate-600">Your session will end and you will return to the login page. Unsaved work may be lost.</p><div className="mt-5 flex justify-end gap-2"><ActionButton onClick={() => setModal(null)}>Cancel</ActionButton><ActionButton variant="primary" onClick={async () => { await logout(); navigate('/'); }}><LogOut size={13} /> Sign Out</ActionButton></div></Modal>}
  </main>
}
