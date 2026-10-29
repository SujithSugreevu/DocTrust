# DocTrust — Secure Document Management Platform

DocTrust is an enterprise-grade document management and compliance platform engineered with strict role-based access control, cryptographic isolation, private storage containment, and a fail-closed immutable audit trail.

---

## Key Capabilities

- **Strict Role Separation**:
  - `EMPLOYEE`: Private workspace for creating folders, secure upload, document search, metadata management, archive/restore, soft-delete, and download.
  - `ADMIN`: User account management and audit log inspection. Prohibited by design from accessing private document content or metadata.
- **Encapsulated Private Storage**:
  - Files are stored in non-public directories using unguessable 256-bit cryptographic keys.
  - Path traversal is blocked using resolved filesystem containment checks.
  - Storage keys are never exposed in any API response.
- **Folder & Document Integrity**:
  - PostgreSQL-enforced composite foreign key `(folder_id, owner_id)` guarantees documents can never be cross-assigned to folders owned by another user.
- **Upload Security Pipeline**:
  - File extension whitelisting (`.pdf`, `.docx`, `.xlsx`, `.pptx`).
  - Magic byte and MIME type validation.
  - Malicious script scanning (PDF `/JavaScript`, `/Launch`, etc.).
  - Storage quota enforcement (50 MB per file, 500 MB per user).
- **Fail-Closed Audit Trail**:
  - All uploads, downloads, views, updates, deletions, and purges record immutable audit events with actor, IP, timestamp, and target IDs.

---

## Tech Stack

- **Backend**: Python 3.13, Django 5.x, Django REST Framework, PostgreSQL
- **Frontend**: React 19, Vite, Tailwind CSS, Lucide Icons
- **Infrastructure**: Docker & Docker Compose for PostgreSQL

---

## Getting Started

### 1. Prerequisites
- Python 3.12+ (tested with Python 3.13)
- Node.js 20+ and npm
- Docker (running PostgreSQL container `doctrust_postgres`)

### 2. Environment Configuration
Copy `.env.example` to `.env` and fill in necessary configuration:
```bash
cp .env.example .env
```

### 3. Backend Setup
```bash
# Activate virtual environment
.\backend\venv\Scripts\activate

# Install dependencies (if needed)
pip install -r backend/requirements.txt

# Run migrations
python backend/manage.py migrate

# Create or repair the two demo accounts. Passwords are requested without echoing.
python backend/manage.py seed_dev_users --prompt-for-passwords

# Start Django development server
python backend/manage.py runserver 127.0.0.1:8000
```

### 4. Frontend Setup
```bash
npm install
npm run dev
```
The React frontend is available at `http://localhost:5173`.

### Demo account repair and database selection

`seed_dev_users` is the supported command. It creates missing accounts, repairs
their `ADMIN`/`EMPLOYEE` role and active status, and preserves existing
passwords unless `--reset-passwords` is explicitly supplied. Passwords are
never stored in source code or printed by the command.

To seed the complete persisted demonstration dataset (users, folders,
documents, shares, audit events, notifications, and alerts), run:

```bash
python backend/manage.py seed_demo_data --prompt-for-passwords
python backend/manage.py verify_demo_data
```

The command creates approximately 550 coordinated demo records across the
existing models. It is idempotent and preserves existing records. It is
intentionally not run automatically during web-service startup, so a restart
cannot create or overwrite application data.

To explicitly rotate both demo passwords locally, run:

```bash
python backend/manage.py seed_dev_users --reset-passwords --prompt-for-passwords
```

For a deliberate one-time Render repair, set `DOCTRUST_DEMO_MODE=1`,
`DOCTRUST_DEMO_ADMIN_PASSWORD`, and `DOCTRUST_DEMO_EMPLOYEE_PASSWORD` as
temporary Render environment variables. Before seeding documents, attach a
Render persistent disk to the backend service and set
`DOCUMENT_STORAGE_ROOT=/var/data/doctrust/storage` (or the disk's actual mount
path). Then run from the Render shell:

```bash
cd backend
python manage.py seed_demo_data --allow-production-demo --reset-passwords
python manage.py verify_demo_data
```

Remove the temporary password variables and `DOCTRUST_DEMO_MODE` immediately
after the command succeeds. The command refuses to touch a `DEBUG=False`
database without both explicit production flags and refuses to write demo
document bytes to an unconfigured or `/tmp` storage root.

When `DATABASE_URL` is present, Django uses it in preference to
`POSTGRES_*`; local management commands and the Vite proxy therefore operate
against that PostgreSQL database. To use the Docker PostgreSQL database
instead, unset `DATABASE_URL`/`DATABASE_URL_UNPOOLED` for the local process
and start Docker first. The deployed Vercel frontend routes `/api/*` to the
Render backend through `vercel.json`. If the frontend is deployed as a
separate Render static site, configure the build environment variable
`VITE_API_BASE_URL=https://doctrust-backend.onrender.com/api` instead.

The web process uses pooled `DATABASE_URL`. For migrations or explicit
administrative seed/verification work, set `DOCTRUST_USE_UNPOOLED_DATABASE=1`
only after confirming that `DATABASE_URL_UNPOOLED` is current and valid; the
current local unpooled credential was rejected during inspection, so it must be
rotated before using that option.

---

## Running Tests

Run the complete test suite (accounts, auditlog, and documents):
```bash
.\backend\venv\Scripts\python.exe backend\manage.py test accounts auditlog documents
```
All 109 tests pass covering:
- Authentication, CSRF, and role denial
- Direct database composite foreign key isolation
- File validation, storage encapsulation, and quota enforcement
- Soft delete, restore, and permanent purge lifecycle
- Audit logging fail-closed behaviors

---

## Documentation

- [API Reference](docs/API.md) — Comprehensive REST API documentation
- [Security Architecture](docs/SECURITY.md) — Defense-in-depth security model and threat mitigations
