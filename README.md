# DocTrust

[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61dafb)](https://react.dev/)
[![Backend](https://img.shields.io/badge/backend-Django%20%2B%20DRF-0c4b33)](https://www.djangoproject.com/)
[![Database](https://img.shields.io/badge/database-PostgreSQL-336791)](https://www.postgresql.org/)
[![Deployment](https://img.shields.io/badge/deployment-Vercel%20%2B%20Render-black)](https://vercel.com/)

Secure document management, sharing, permission control, and audit visibility for Administrator and Employee workflows.

## Table of contents

1. [Project Summary](#1-project-summary)
2. [Demo Login Credentials](#2-demo-login-credentials)
3. [Project Workflow and Architecture](#3-project-workflow-and-architecture)
4. [Technology Stack and Dependencies](#4-technology-stack-and-dependencies)
5. [Features](#5-features)
6. [Project Directory Structure](#6-project-directory-structure)
7. [API Endpoints](#7-api-endpoints)
8. [Database Design](#8-database-design)
9. [Local Installation and Setup](#9-local-installation-and-setup)
10. [Demo Data and Data Persistence](#10-demo-data-and-data-persistence)
11. [Environment Variables](#11-environment-variables)
12. [Deployment Guide](#12-deployment-guide)
13. [Testing and Verification](#13-testing-and-verification)
14. [Troubleshooting](#14-troubleshooting)
15. [Future Improvements](#15-future-improvements)
16. [Conclusion and Project Information](#16-conclusion-and-project-information)

## 1. Project Summary

DocTrust is a role-aware document management application for securely uploading, organizing, sharing, reviewing, and auditing business documents. It separates the Employee document workspace from the Administrator governance workspace and enforces authorization in Django rather than relying on frontend role selection.

The project addresses common document-management risks: uncontrolled file access, cross-owner folder assignment, missing audit history, weak session boundaries, and data that exists only in frontend mock state. Document metadata and relationships are persisted in PostgreSQL. Physical files are kept behind authenticated Django handlers using private storage keys.

The application is used by:

- **Employees**, who own documents, organize folders, share documents, manage permissions, and review their activity.
- **Administrators**, who manage accounts, review document metadata and audit activity, inspect permission changes, and monitor security alerts. Administrators are deliberately denied access to Employee private document content through the Employee-only document permissions.

The current stack is React, Vite, Tailwind CSS, Django 5.1, Django REST Framework, PostgreSQL through Psycopg 3, and Gunicorn. The frontend is deployed to Vercel and the Django backend is deployed to Render.

**Live application:** [https://doc-trust-one.vercel.app/](https://doc-trust-one.vercel.app/)

## 2. Demo Login Credentials

These are intentionally public demonstration credentials supplied for the DocTrust demo environment. Do not reuse them for real accounts, private business data, or any deployment that is not explicitly a demo service.

| Role | Login ID / Username | Password |
|---|---|---|
| Administrator | **admin_demo** | **AdminDemo!2026** |
| Employee | **employee_demo** | **EmployeeDemo!2026** |

Use the usernames above to sign in. Select **Administrator** for admin_demo and **Employee** for employee_demo; the backend requires the submitted expected role to match the account database role.

The passwords above are safe demo values explicitly designated for this project. The supported account command never stores them in source code and does not reset an existing password unless reset-passwords is explicitly requested. For a new deployment, set passwords through temporary environment variables or an interactive prompt instead of committing them.

If login fails:

1. Confirm that the selected UI role matches the account role.
2. Refresh the page so the CSRF cookie and masked token are obtained again.
3. Confirm the frontend is calling /api/auth/csrf/ and /api/auth/login/ on the frontend origin.
4. Check that the backend is connected to the intended PostgreSQL database.
5. Use seed_dev_users only with an explicit secure password setup; never guess or copy a password hash.

## 3. Project Workflow and Architecture

### 3.1 High-level architecture

The Vercel frontend uses relative /api/... URLs. Vite proxies those URLs to the local Django server during development. In production, Vercel API rewriting forwards /api/:path* to Render before the SPA fallback. Django authenticates the request, applies role and ownership permissions, reads or writes PostgreSQL records, and accesses private document bytes only through authenticated views.

~~~mermaid
flowchart LR
    Browser[User browser]
    Vercel[React/Vite frontend on Vercel]
    Proxy[Vercel /api rewrite]
    Render[Gunicorn + Django REST API on Render]
    DB[(PostgreSQL / Neon pooled DATABASE_URL)]
    Files[PrivateDocumentStorage filesystem]
    Browser --> Vercel
    Vercel -->|same-origin /api/*| Proxy
    Proxy --> Render
    Render --> DB
    Render -->|authenticated view/download only| Files
    Render --> Vercel
~~~

The current repository implements private local filesystem storage through PrivateDocumentStorage. It does not contain an S3 storage adapter or AWS SDK dependency. A Render persistent disk or private object-storage adapter is required for durable real-user uploads.

### 3.2 Authentication flow

1. The user opens the React login page and selects Administrator or Employee.
2. The form sends the identifier, password, expected_role, and remember_me values to login() in src/services/auth.js.
3. The frontend first requests GET /api/auth/csrf/ with credentials included.
4. Django's CSRFView uses ensure_csrf_cookie and get_token(request), returning a masked csrfToken JSON value and issuing the csrftoken cookie.
5. The frontend sends the masked value as X-CSRFToken on POST /api/auth/login/, again with credentials included.
6. Django validates the identifier against username or email, checks password hashing, active status, suspension state, and the selected role. A mismatch is rejected before a session is created.
7. If MFA is enabled or required by policy, the API returns an MFA challenge. Otherwise it creates a database-backed per-tab session and returns a tab_session_key.
8. The frontend stores that tab key in sessionStorage and sends it as X-DocTrust-Session on authenticated API requests. The backend verifies the session hash, account status, and idle timeout.
9. The role route redirects administrators to /admin/dashboard and employees to /employee/dashboard.
10. Logout sends a CSRF-protected request, revokes the current tab session, clears the tab key, and leaves other tabs isolated.

The production frontend origin is https://doc-trust-one.vercel.app. Django production configuration trusts that exact HTTPS origin, enables credentialed CORS, and uses secure cookies. CSRF remains enabled; the login endpoint is not exempted.

### 3.3 Administrator workflow

- **Administrator Dashboard**: displays registered users, total/active/restricted document counts, recent audit activity, chart data, permission changes, and active security alerts.
- **User Management**: lists administrators and employees with search/status filters. Administrators can create accounts, update profile/role information, suspend accounts, and reactivate accounts subject to backend role checks.
- **Document Overview**: shows document metadata, owner, format, status, access level, and aggregate counts. The endpoint intentionally returns permitted metadata only; administrators are not granted private employee file content or download access.
- **Activity Logs**: reads administrator and employee audit streams, filters activity, shows event details, and supports CSV export through the audit API.
- **Permission Audit**: displays document-share grants, updates, and revocations recorded in audit events.
- **Security Monitoring**: lists persisted security alerts, filters by severity/status, and allows an administrator to resolve or reopen alerts. Resolution is audited.
- **System Settings**: reads and updates the singleton settings row, reports database/storage health, exposes capability status, and supports an administrator-initiated reset to safe defaults.

All Administrator APIs require an authenticated active account with the ADMIN role. Administrator status does not grant Employee document permissions.

### 3.4 Employee workflow

- **Employee Dashboard**: shows owned-document totals, shared-document totals, storage usage, recent activity, quick actions, and persisted notifications.
- **My Documents**: lists documents owned by the Employee with search, category, date, pagination, preview, download, metadata actions, and lifecycle controls.
- **Folders & Categories**: creates, renames, filters, opens, and deletes empty owner folders. A folder cannot be deleted while it contains documents.
- **Shared with Me**: lists documents shared to the current Employee and applies the permission granted by the owner.
- **Shared by Me**: lists outgoing shares made on owned documents and supports permission/revocation management.
- **Manage Permissions**: selects an owned document and creates, updates, or revokes recipient grants.
- **Activity History**: filters the Employee's own audit activity and provides an export action.
- **Profile and MFA**: updates the current profile, changes password, displays/enrolls/disables TOTP MFA, and supports MFA recovery codes.

All Employee document and folder endpoints use the current authenticated tab session and the Employee permission class. The frontend route is not an authorization boundary by itself.

### 3.5 Document lifecycle

1. An Employee uploads a PDF, DOCX, XLSX, or PPTX through multipart form data.
2. Django validates the extension, MIME/signature bytes, Office OpenXML structure where applicable, PDF dangerous-script markers, size limit, and per-user quota.
3. The file is written through PrivateDocumentStorage under an unguessable 64-character key. The database stores metadata, SHA-256, size, owner, folder, status, and storage key; the storage key is excluded from API serializers.
4. The document record and fail-closed upload audit event are created in a transaction. Failed database/audit writes clean up the physical file.
5. Owners can view metadata, preview/download authorized bytes, edit metadata, archive, restore, or soft-delete documents. Employees with an active EDIT share can edit limited metadata but cannot move another owner's document between folders.
6. Owners can share a document with another Employee at VIEW, DOWNLOAD, or EDIT level. Shares are unique per document/recipient and can expire.
7. Soft deletion marks the document as deleted and retains bytes for recovery/retention. Explicit purge removes physical bytes and records purged_at while preserving the database reference and audit history.

### 3.6 Permission and security flow

- ADMIN is for governance, user management, audit review, settings, and security monitoring.
- EMPLOYEE is the document owner/workspace role.
- Folder and document owner relationships are checked in serializers, model save/clean logic, and PostgreSQL composite ownership constraints.
- Document access is based on ownership or an active document share. Private bytes are never served as public media.
- Mutating requests require a CSRF token. Authenticated API requests also require the current tab-session header.
- Audit metadata is sanitized and security-relevant operations are logged. AuditEvent.save() and delete() enforce application-level append-only behavior; database-level audit triggers are a future hardening proposal.

## 4. Technology Stack and Dependencies

### Runtime

- Python 3.13-compatible environment, Django 5.1.15, and Django REST Framework 3.15.2.
- PostgreSQL through psycopg[binary] 3.2.13. The application uses the pooled DATABASE_URL for normal web traffic.
- django-cors-headers for exact-origin CORS configuration.
- python-dotenv for local environment loading.
- gunicorn for the Render WSGI process.
- PyOTP and qrcode for TOTP MFA enrollment and recovery flows.
- python-magic on non-Windows or python-magic-bin on Windows as optional native MIME support. Built-in signature validation remains available if native magic is unavailable.

### Frontend

- React 19.3.1, React DOM, React Router 7.18.4, and lucide-react.
- Vite 8.3.4, Tailwind CSS 4.3.3, @tailwindcss/vite, and the React Vite plugin.
- ESLint and React hook/refresh plugins for development checks.
- @neon/config and @neon/env are present in package.json; the Django application still uses its existing PostgreSQL URL rather than a browser database client.

Node dependencies belong in package.json; Python dependencies belong in backend/requirements.txt.

## 5. Features

### Implemented

- Username/email login with selected-role validation.
- CSRF-protected login, password reset request/confirmation, password change, and logout.
- Database-backed per-tab sessions with idle timeout and session-hash validation.
- TOTP MFA enrollment, login challenge, disable flow, replay protection, and single-use recovery codes.
- Administrator account creation, editing, suspension, reactivation, and status filtering.
- Employee folder and document management.
- PDF/DOCX/XLSX/PPTX validation, private storage, SHA-256 metadata, quotas, preview, download, archive, restore, soft delete, and purge.
- Document-level VIEW, DOWNLOAD, and EDIT shares with expiration support.
- Persisted Employee notifications and read/read-all actions.
- Append-only application audit events, CSV exports, audit dashboards, permission audit, and security alerts.
- Singleton administrator system settings with health/capability reporting.
- Idempotent demo-data seeding and read-only verification.
- Vercel same-origin API rewrite to Render and SPA fallback.

### Incomplete or not implemented

- A durable S3-compatible storage adapter is not present in the current repository. Render /tmp is ephemeral.
- External malware scanning is not integrated; validation is built in.
- The VIEWER role is reserved but not implemented.
- Database-level audit immutability triggers and restricted database roles are documented as future hardening; current immutability is enforced at the application layer.

## 6. Project Directory Structure

~~~text
DocTrust/
├── src/
│   ├── App.jsx
│   ├── pages/                 # Login, dashboards, portal, settings, admin pages
│   └── services/              # API, auth, tab sessions, documents, audit, settings
├── public/                    # Public frontend assets
├── backend/
│   ├── manage.py
│   ├── doctrust/              # Django settings, URLs, WSGI/ASGI, health checks
│   ├── accounts/              # User model, auth, MFA, permissions, seed commands
│   ├── documents/             # Folders, documents, shares, storage, validators
│   ├── auditlog/              # AuditEvent, SecurityAlert, audit APIs
│   ├── systemsettings/        # Singleton settings and idle-timeout middleware
│   ├── */migrations/          # Django schema migrations
│   ├── */tests.py             # App tests and storage tests
│   ├── requirements.txt
│   └── pyproject.toml
├── docs/API.md                # API reference maintained with the project
├── docs/SECURITY.md           # Security architecture notes
├── render.yaml                # Render backend Blueprint
├── vercel.json                # Vercel API rewrite and SPA fallback
├── vite.config.js             # Vite port and local /api proxy
├── package.json
├── package-lock.json
├── docker-compose.yml         # Optional local PostgreSQL container
├── .env.example
└── README.md
~~~

Generated dist/, staticfiles/, virtual environments, storage bytes, caches, and node_modules/ are not application source.

## 7. API Endpoints

The API is rooted at /api. Authenticated API requests use the X-DocTrust-Session tab key returned by login. State-changing requests also require X-CSRFToken.

### Health and authentication

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | /api/health/ | Backend/database health | Public |
| GET | /api/auth/csrf/ | Set CSRF cookie and return masked token | Public |
| POST | /api/auth/login/ | Authenticate username/email, password, and expected role | Public + CSRF |
| POST | /api/auth/logout/ | Revoke current tab session | Active authenticated user + CSRF |
| GET/PATCH | /api/auth/me/ or /api/auth/profile/ | Read/update current profile | Active authenticated user; CSRF for PATCH |
| GET | /api/auth/session/ | Current-user session equivalent | Active authenticated user |
| GET | /api/auth/admin-check/ | Verify Administrator access | Active Administrator |
| POST | /api/auth/password-reset/ | Request generic password-reset instructions | Public + CSRF |
| POST | /api/auth/password-reset/confirm/ | Confirm reset with uid/token/new password | Public + CSRF |
| POST | /api/auth/password-change/ | Change current password | Active authenticated user + CSRF |
| GET | /api/auth/2fa/status/ | Read MFA status | Active authenticated user |
| POST | /api/auth/2fa/enroll/, /verify-enroll/, /disable/ | MFA enrollment and disable lifecycle | Active authenticated user + CSRF |
| POST | /api/auth/2fa/verify-login/ | Complete an MFA login challenge | MFA challenge + CSRF |
| POST | /api/auth/2fa/setup-login/ | Complete required MFA setup during login | MFA challenge + CSRF |

### Administrator APIs

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET/POST | /api/admin/users/ | List/filter or create users | Administrator; POST requires CSRF |
| PATCH | /api/admin/users/<id>/ | Update user name, email, or role | Administrator + CSRF |
| POST | /api/admin/users/<id>/suspend/ | Suspend an account | Administrator + CSRF |
| POST | /api/admin/users/<id>/unsuspend/ | Reactivate an account | Administrator + CSRF |
| GET/PATCH | /api/admin/system-settings/ | Read or update singleton settings | Administrator; writes require CSRF |
| POST | /api/admin/system-settings/reset/ | Reset settings to defaults | Administrator + CSRF |

### Employee document APIs

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET/POST | /api/folders/ or /api/documents/folders/ | List/create owner folders | Active Employee; POST + CSRF |
| GET/PATCH/DELETE | /api/folders/<uuid>/ | Read, rename, or delete an empty folder | Folder owner; writes + CSRF |
| GET/POST | /api/documents/ | List owned documents or upload a file | Active Employee; POST + CSRF |
| GET/PATCH | /api/documents/<uuid>/ | Read or update document metadata | Owner or active EDIT share; PATCH + CSRF |
| GET | /api/documents/<uuid>/download/ | Download authorized bytes | Owner or active DOWNLOAD/EDIT share |
| GET | /api/documents/<uuid>/view/ | Inline authorized file view | Owner or active share |
| DELETE | /api/documents/<uuid>/ or /delete/ | Soft-delete a document | Owner or permitted actor + CSRF |
| POST | /api/documents/<uuid>/archive/ | Archive a document | Owner + CSRF |
| POST | /api/documents/<uuid>/restore/ | Restore an archived document | Owner + CSRF |
| POST | /api/documents/<uuid>/purge/ | Permanently remove physical bytes after soft delete | Owner + CSRF |
| GET/POST | /api/documents/<uuid>/shares/ | List/create document shares | Owner; POST + CSRF |
| PATCH/DELETE | /api/documents/<uuid>/shares/<share_id>/ | Update/revoke a share | Owner + CSRF |
| GET | /api/documents/shared/ | List documents shared to the Employee | Active Employee |
| GET | /api/documents/owned-shares/ | List outgoing owner shares | Active Employee |
| GET | /api/documents/share-recipients/ | List eligible Employee recipients | Active Employee |
| GET | /api/documents/storage/ | Current usage/quota | Active Employee |
| GET | /api/documents/activity/ | Employee document activity | Active Employee |
| GET | /api/documents/notifications/ | List notifications | Active Employee |
| POST | /api/documents/notifications/<id>/read/ | Mark one notification read | Active Employee + CSRF |
| POST | /api/documents/notifications/read-all/ | Mark all notifications read | Active Employee + CSRF |

### Audit and security APIs

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | /api/audit/admin/, /api/audit/employee/ | Filtered audit streams | Administrator |
| GET | /api/audit/admin/export/, /api/audit/employee/export/ | CSV audit exports | Administrator |
| GET | /api/audit/events/<id>/ | Audit event detail | Administrator |
| GET | /api/audit/action-types/, /api/audit/users/ | Audit filter data | Administrator |
| GET | /api/audit/security-alerts/ | List security alerts | Administrator |
| POST | /api/audit/security-alerts/<id>/resolve/ | Resolve or reopen an alert | Administrator + CSRF |
| GET | /api/audit/dashboard-stats/ | Dashboard statistics and recent activity | Administrator |
| GET | /api/audit/activity-summary/ | Audit summary | Administrator |
| GET | /api/audit/documents-overview/ | Permitted document metadata overview | Administrator |

## 8. Database Design

PostgreSQL stores users, authentication/session records, document metadata, folders, shares, notifications, audit events, alerts, and system settings. Physical bytes are not stored in PostgreSQL; Document.storage_key points to private storage and is never exposed by serializers.

~~~mermaid
erDiagram
    USER ||--o{ FOLDER : owns
    USER ||--o{ DOCUMENT : owns
    FOLDER ||--o{ DOCUMENT : contains
    DOCUMENT ||--o{ DOCUMENT_SHARE : grants
    USER ||--o{ DOCUMENT_SHARE : receives
    USER ||--o{ EMPLOYEE_NOTIFICATION : receives
    DOCUMENT ||--o{ EMPLOYEE_NOTIFICATION : concerns
    USER ||--o{ AUDIT_EVENT : acts
    USER ||--o{ SECURITY_ALERT : targets
    USER ||--o{ SECURITY_ALERT : resolves
    USER ||--|| USER_TWO_FACTOR : configures
    USER ||--o{ TWO_FACTOR_RECOVERY_CODE : owns
~~~

Principal entities:

- accounts.User: custom Django user with unique email, ADMIN/EMPLOYEE role, active/suspended status, suspension details, and standard Django password hashing.
- accounts.UserTwoFactor and TwoFactorRecoveryCode: TOTP setup, replay protection, lockout state, and hashed one-time recovery codes.
- documents.Folder: owner-scoped UUID folders with case-insensitive owner/name uniqueness.
- documents.Document: UUID metadata record with owner, optional folder, file type, status, size, SHA-256, lifecycle timestamps, and private storage key.
- documents.DocumentShare: unique document/recipient permission grant with optional expiry.
- documents.EmployeeNotification: idempotent per-Employee notification with stable event_key.
- auditlog.AuditEvent: append-only application-level audit record with actor, action, target label/id, IP, metadata, and timestamp.
- auditlog.SecurityAlert: persisted severity/status/scope alert with optional target and resolver users.
- systemsettings.SystemSettings: singleton row enforced with id=1, containing upload, quota, audit, alert, and security settings.

Important integrity rules include protected document ownership, folder/document owner matching, positive file size, allowed file types, SHA-256/storage-key formats, active/archive name uniqueness, unique shares, and PostgreSQL ownership constraints.

## 9. Local Installation and Setup

### Prerequisites

- Windows 10/11 with PowerShell and VS Code.
- Python 3.13 or another version supported by the pinned dependencies.
- Node.js/npm compatible with the installed Vite version.
- PostgreSQL 16, or Docker Desktop for the repository optional PostgreSQL container.

### Backend

From the repository root:

~~~powershell
py -3.13 -m venv backend\venv
backend\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
~~~

Edit .env locally. Use either an available local PostgreSQL database or a deliberately selected development database. Never put production secrets in Git.

For the Docker PostgreSQL service, configure the POSTGRES_* values in .env and start only the database:

~~~powershell
docker compose up -d db
~~~

Apply migrations only to the intended local/development database:

~~~powershell
python backend\manage.py check
python backend\manage.py migrate
python backend\manage.py runserver 127.0.0.1:8000
~~~

The backend is available at http://127.0.0.1:8000/ and health is exposed at http://127.0.0.1:8000/api/health/.

### Frontend

In a second terminal:

~~~powershell
npm install
npm run dev
~~~

The Vite frontend runs at http://localhost:5173/. Its /api proxy targets http://127.0.0.1:8000; the production frontend uses the Vercel rewrite. Leave VITE_API_BASE_URL unset for this architecture.

## 10. Demo Data and Data Persistence

### Supported commands

The project has one orchestration command and one read-only verifier. Do not create a second seed system.

~~~powershell
# Local/demo database; prompts for passwords only if the two primary accounts are missing.
python backend\manage.py seed_demo_data --prompt-for-passwords

# Read-only count, relationship, and file validation.
python backend\manage.py verify_demo_data
~~~

The orchestration command calls the supported account, administrator fixture, Employee fixture, and scale commands. It is idempotent: stable usernames, names, event markers, notification keys, shares, and alert types prevent duplicate demo records. Existing user passwords are preserved unless --reset-passwords is explicitly requested.

The expected dataset is **557 coordinated demo records**:

| Layer | Records |
|---|---:|
| Primary demo accounts | 2 |
| Administrator fixture layer | 50 |
| Employee fixture layer | 85 |
| Scale layer | 420 |
| **Total** | **557** |

The dataset contains 185 fictional demo documents with generated PDF/DOCX/XLSX/PPTX bytes. The verifier checks 557 records, 185 files, owner/folder relationships, share recipients, audit targets, notification targets, alert targets, and storage-path containment. It does not modify data.

### Production/demo Render mode

This repository is configured for an intentionally populated demo service. The [render.yaml](./render.yaml) startup command runs the seed only when all of the following are enabled:

~~~text
DOCTRUST_AUTO_SEED_DEMO_DATA=1
DOCTRUST_DEMO_MODE=1
DOCTRUST_DEMO_EPHEMERAL_FILES=1
~~~

The command passes --allow-production-demo --allow-ephemeral-demo-files. The flags are deliberate safeguards: normal production processes cannot seed accidentally, and ephemeral file mode can only regenerate fictional demo files. It never resets the database, truncates tables, deletes real files, or changes existing passwords without an explicit reset option.

Database records persist in PostgreSQL across deploys and restarts. Render free-plan /tmp files do not. With demo-only ephemeral mode, missing fictional demo files are regenerated from their database metadata on startup. Real user uploads require a Render persistent disk or a private object-storage implementation; do not treat real uploads as disposable demo files.

## 11. Environment Variables

Values below are names and safe placeholders only. Do not copy real .env or Render values into documentation or Git.

| Variable | Purpose | Required |
|---|---|---|
| DATABASE_URL | Pooled PostgreSQL URL used by Django web traffic | Yes in production |
| DATABASE_URL_UNPOOLED | Optional direct URL for carefully controlled migration/admin operations | Optional; current direct credential must be valid |
| DOCTRUST_USE_UNPOOLED_DATABASE | Explicitly selects the unpooled URL when enabled | Normally unset |
| NEON_BRANCH | Database branch indicator used by safety guards | Recommended |
| POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT | Local PostgreSQL fallback when DATABASE_URL is absent | Local fallback |
| DJANGO_SECRET_KEY | Django signing/crypto secret | Required in production; secret |
| DJANGO_DEBUG | Debug mode | False in production |
| DJANGO_ALLOWED_HOSTS | Backend host allowlist | Required in production |
| FRONTEND_BASE_URL | Frontend origin used in CORS/CSRF configuration | https://doc-trust-one.vercel.app in production |
| DJANGO_CORS_ALLOWED_ORIGINS | Additional exact CORS origins | Production Vercel origin |
| DJANGO_CSRF_TRUSTED_ORIGINS | Additional exact CSRF trusted origins | Production Vercel origin |
| DOCUMENT_STORAGE_ROOT | Private document storage root | Persistent disk for real uploads; /tmp/doctrust/storage only for demo regeneration |
| MEDIA_ROOT | Legacy/private media setting | Optional; not public document serving |
| FILE_UPLOAD_TEMP_DIR | Temporary upload directory | Optional; writable path required |
| MAX_UPLOAD_MB | Maximum upload size | Defaults to 50 |
| USER_STORAGE_QUOTA_MB | Per-user quota | Defaults to 500 |
| DELETED_RETENTION_DAYS | Retention policy setting | Defaults to 30 |
| DOCTRUST_DEMO_MODE | Explicit demo seed safety switch | Only for demo deployment |
| DOCTRUST_AUTO_SEED_DEMO_DATA | Enables guarded seed on startup | Only for demo deployment |
| DOCTRUST_DEMO_EPHEMERAL_FILES | Allows fictional file regeneration on ephemeral storage | Only for demo deployment |
| DOCTRUST_DEMO_ADMIN_PASSWORD | One-time password input if admin_demo is missing/reset | Temporary secret; never commit |
| DOCTRUST_DEMO_EMPLOYEE_PASSWORD | One-time password input if employee_demo is missing/reset | Temporary secret; never commit |
| DOCTRUST_MOCK_EMPLOYEE_PASSWORD | Optional password for seed-only fixture employees | Usually unset |
| DJANGO_EMAIL_BACKEND, DJANGO_EMAIL_HOST, DJANGO_EMAIL_PORT, DJANGO_EMAIL_USE_TLS, DJANGO_EMAIL_HOST_USER, DJANGO_EMAIL_HOST_PASSWORD, DJANGO_DEFAULT_FROM_EMAIL | Email delivery | SMTP values in production; secrets where applicable |
| VITE_API_BASE_URL | Direct frontend API override | **Leave unset**; browser requests must use same-origin /api |

## 12. Deployment Guide

### Vercel frontend

1. Connect the repository root to the Vercel project.
2. Use the repository root as the Vercel Root Directory.
3. Build command: npm run build.
4. Output directory: dist.
5. Leave VITE_API_BASE_URL unset.
6. Deploy [vercel.json](./vercel.json), which places the API rewrite before the SPA fallback:

~~~json
{
  "source": "/api/:path*",
  "destination": "https://doctrust-backend.onrender.com/api/:path*"
}
~~~

The deployed frontend is https://doc-trust-one.vercel.app/.

### Render backend

The Blueprint in [render.yaml](./render.yaml) uses:

~~~text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: the guarded demo-seed shell command followed by Gunicorn
Health Check: /api/health/
~~~

The ordinary Django server entry point is:

~~~bash
gunicorn doctrust.wsgi:application --bind 0.0.0.0:$PORT
~~~

Required production configuration includes DJANGO_DEBUG=False, a strong DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS=doctrust-backend.onrender.com, the pooled DATABASE_URL, and the exact Vercel CORS/CSRF origins. Do not use uvicorn app.main:app; this repository has no FastAPI application.

The deployed backend is https://doctrust-backend.onrender.com/ and its health response reports PostgreSQL connectivity. The Blueprint configures the explicit demo startup flags. If the Render service is not managed by the Blueprint, set the three flags and the guarded start command manually in the Render dashboard, then deploy the latest commit. The live service must be checked separately after deployment.

### Storage deployment choice

- **Demo-only free Render service:** /tmp/doctrust/storage plus the three explicit demo flags regenerates fictional demo files after restarts.
- **Real production uploads:** attach a Render persistent disk and set DOCUMENT_STORAGE_ROOT to its mount path, or implement a private S3-compatible storage adapter. Never expose storage_key or public media URLs.

## 13. Testing and Verification

### Backend checks

From backend/ with the intended development environment selected:

~~~powershell
python manage.py check
python -m pip check
python manage.py test accounts auditlog documents systemsettings
~~~

Run Django tests against an isolated local/test PostgreSQL database or branch. Do not let Django create/drop a test database on the production Neon database.

### Frontend checks

From the repository root:

~~~powershell
npm run test:auth-config
npm run lint
npm run build
~~~

test:auth-config validates relative browser API paths, rewrite ordering, credentials, and the CSRF header. Lint may report existing React hook dependency warnings; they should be reviewed separately from build errors.

### Demo verification

~~~powershell
python backend\manage.py verify_demo_data
~~~

This command is read-only. A successful populated demo reports 557 records and 185 files. It validates relationships and path containment without resetting or modifying the database.

## 14. Troubleshooting

### Login says invalid credentials

Use the username and role from [Demo Login Credentials](#2-demo-login-credentials). Confirm the selected role matches ADMIN or EMPLOYEE. The backend accepts username or email and rejects inactive, suspended, invalid-password, and role-mismatch requests safely.

### Login returns 401 or 403

- 401 normally means invalid credentials, inactive account, or role mismatch.
- 403 may be CSRF rejection, suspension, or a role/permission denial.
- Request /api/auth/csrf/ first and confirm a token-bearing response, cookie, and X-CSRFToken header.
- Confirm the browser uses the Vercel-origin /api/auth/login/, not a direct Render URL.

### CSRF/CORS errors

Set the exact HTTPS origin in FRONTEND_BASE_URL, DJANGO_CORS_ALLOWED_ORIGINS, and DJANGO_CSRF_TRUSTED_ORIGINS. Keep CORS_ALLOW_CREDENTIALS=True, secure production cookies, and the Vercel rewrite. Never add a blanket CSRF exemption.

### Missing data after deployment

Verify DATABASE_URL points to the intended pooled PostgreSQL database, then run the read-only verifier. Database records do not survive if the service is pointed at a different database. Do not use frontend arrays as a persistence workaround.

### Missing document files

Database records and physical bytes are separate. On free Render, enable the guarded demo startup flags so fictional demo files regenerate. For real uploads, configure a persistent disk or private object storage. A missing file returns an error rather than exposing another file.

### Vercel route refresh returns 404

Confirm the project Root Directory is the repository root and that vercel.json contains the /api/:path* rewrite before the /(.*) SPA fallback. Rebuild with npm run build.

### Render deployment fails

Confirm Root Directory backend, pip install -r requirements.txt, Gunicorn doctrust.wsgi:application, DATABASE_URL, allowed hosts, and writable storage. Render's PORT is supplied by the platform. Do not add a FastAPI/Uvicorn entry point.

## 15. Future Improvements

The following are proposals, not completed features:

- Replace ephemeral/local production file storage with a private S3-compatible adapter or a managed persistent disk.
- Add PostgreSQL triggers/restricted roles for database-level audit immutability in addition to application guards.
- Add a dedicated non-production PostgreSQL branch and CI test database workflow.
- Add explicit API schema generation/OpenAPI publication and stronger frontend integration tests.
- Add external malware scanning if the deployment threat model requires it.
- Implement a separate VIEWER role only after its authorization model is designed and tested.
- Improve background demo-file repair observability and rate limiting for very large demo datasets.

## 16. Conclusion and Project Information

DocTrust is a React/Vite and Django REST Framework document-management system with PostgreSQL persistence, role-based authorization, CSRF-protected per-tab sessions, private document storage, sharing permissions, audit history, and security monitoring.

- **Repository:** [github.com/SujithSugreevu/DocTrust](https://github.com/SujithSugreevu/DocTrust)
- **Live application:** [https://doc-trust-one.vercel.app/](https://doc-trust-one.vercel.app/)
- **Backend:** [doctrust-backend.onrender.com](https://doctrust-backend.onrender.com/)
- **Health endpoint:** [doctrust-backend.onrender.com/api/health/](https://doctrust-backend.onrender.com/api/health/)

The project keeps application behavior and authorization in the backend, persists metadata in PostgreSQL, and treats physical document storage as a separate deployment concern. Use the demo environment only with the explicitly designated demo accounts and never reuse their credentials for real data.
