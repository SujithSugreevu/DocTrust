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

# Seed initial test accounts (admin_demo & employee_demo)
python backend/manage.py seed_dev_accounts

# Start Django development server
python backend/manage.py runserver 127.0.0.1:8000
```

### 4. Frontend Setup
```bash
npm install
npm run dev
```
The React frontend is available at `http://localhost:5173`.

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
