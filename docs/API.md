# DocTrust API Documentation

## Overview

DocTrust is a secure document management system featuring strict role separation (ADMIN vs EMPLOYEE), encapsulated private storage, and a fail-closed immutable audit trail.

- **Base URL:** `http://localhost:8000/api` (or proxied via Vite dev server `/api`)
- **Authentication:** Session-based authentication via Django session cookies (`sessionid`)
- **CSRF Protection:** Required for all state-mutating requests (`POST`, `PATCH`, `DELETE`, `PUT`) via the `X-CSRFToken` header.
- **Roles:**
  - `EMPLOYEE`: Access to private document & folder workspace. Document owner.
  - `ADMIN`: Access to user management and audit log review. Explicitly forbidden (403) from accessing employee documents and metadata.

---

## 1. Authentication Endpoints

### `GET /api/auth/csrf/`
Fetches a CSRF token and sets the `csrftoken` cookie.

### `POST /api/auth/login/`
Authenticates user credentials.
- **Payload:**
  ```json
  {
    "username": "employee_demo",
    "password": "Password123!",
    "expected_role": "EMPLOYEE",
    "remember_me": false
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "detail": "Login successful.",
    "user": {
      "id": 1,
      "username": "employee_demo",
      "email": "employee@example.com",
      "role": "EMPLOYEE",
      "status": "ACTIVE"
    }
  }
  ```

### `POST /api/auth/logout/`
Terminates the session and invalidates the session cookie.

### `GET /api/auth/me/`
Retrieves the currently authenticated user's profile.

---

## 2. Folder Endpoints

All folder endpoints require active `EMPLOYEE` authentication. `ADMIN` accounts receive `403 Forbidden`.

### `GET /api/folders/` (also `/api/documents/folders/`)
List folders owned by the authenticated employee.
- **Response (200 OK):**
  ```json
  [
    {
      "id": "28ef9dfd-0e4b-44f4-8d97-5bbddc214342",
      "name": "Reports",
      "created_at": "2026-10-22T02:00:00Z",
      "document_count": 3
    }
  ]
  ```

### `POST /api/folders/` (also `/api/documents/folders/`)
Create a new folder.
- **Payload:**
  ```json
  {
    "name": "Financials"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "id": "...",
    "name": "Financials",
    "created_at": "...",
    "document_count": 0
  }
  ```

### `PATCH /api/folders/<uuid:id>/` (also `/api/documents/folders/<uuid:id>/`)
Rename a folder.
- **Payload:**
  ```json
  {
    "name": "Annual Financials"
  }
  ```
- **Response (200 OK):** Updated folder object.

### `DELETE /api/folders/<uuid:id>/` (also `/api/documents/folders/<uuid:id>/`)
Delete an empty folder.
- If the folder contains documents, returns `400 Bad Request` with an explanatory message.
- If the folder belongs to another owner, returns `404 Not Found`.
- **Response (204 No Content)**

---

## 3. Document Endpoints

All document endpoints require active `EMPLOYEE` authentication. `ADMIN` accounts receive `403 Forbidden`.

### `GET /api/documents/`
List documents owned by the caller.
- **Query Parameters:**
  - `status`: Filter by status (`active` [default], `archived`, `deleted`, `all`).
  - `search`: Case-insensitive substring search on `name` and `description`.
  - `folder`: Filter by folder UUID, or `none` for unfiled documents.
  - `file_type`: Filter by format (`PDF`, `DOCX`, `XLSX`, `PPTX`).
  - `ordering`: Sort field (`name`, `-name`, `created_at`, `-created_at`, `size`, `-size`).
  - `page`: Page number (1-indexed).
  - `page_size`: Results per page (max 100, default 20).
- **Response (200 OK):**
  ```json
  {
    "count": 1,
    "page": 1,
    "page_size": 20,
    "results": [
      {
        "id": "58a05ded-ccdb-461b-af25-572fa9987c3e",
        "name": "Q4_Report.pdf",
        "description": "Quarterly summary",
        "file_type": "PDF",
        "size": 1048576,
        "size_display": "1.0 MB",
        "status": "active",
        "folder": "28ef9dfd-0e4b-44f4-8d97-5bbddc214342",
        "folder_name": "Reports",
        "created_at": "2026-10-22T02:00:00Z",
        "updated_at": "2026-10-22T02:00:00Z",
        "archived_at": null,
        "deleted_at": null
      }
    ]
  }
  ```

### `POST /api/documents/`
Upload a new document (`multipart/form-data`).
- **Form Fields:**
  - `file` (required): Binary file (`.pdf`, `.docx`, `.xlsx`, `.pptx`). Max 50 MB.
  - `name` (optional): Display name (defaults to sanitized original filename).
  - `description` (optional): Plain text description (max 300 chars).
  - `folder` (optional): Folder UUID owned by the caller.
- **Security Validations:**
  - MIME type and magic byte verification.
  - Dangerous keyword detection in PDFs (`/JavaScript`, `/Launch`, etc.).
  - Storage quota verification (500 MB limit).
- **Response (201 Created):** Document detail object without storage key.

### `GET /api/documents/<uuid:id>/`
Retrieve document metadata and record a `DOCUMENT_VIEW` audit event.
- **Response (200 OK):** Full metadata including `sha256`, excluding `storage_key`.

### `PATCH /api/documents/<uuid:id>/`
Update document metadata (name, description, folder assignment).
- Validates that cross-owner folder assignment is strictly rejected.
- Records a `DOCUMENT_UPDATE` audit event.
- **Response (200 OK):** Updated document detail object.

### `GET /api/documents/<uuid:id>/download/`
Secure file streaming.
- Validates caller ownership and physical file existence.
- Disables MIME-sniffing (`X-Content-Type-Options: nosniff`).
- Sets `Content-Disposition: attachment; filename="..."`.
- Never reveals the storage key or physical filesystem path.
- Records a `DOCUMENT_DOWNLOAD` audit event.
- **Response (200 OK):** Binary file stream.

### `DELETE /api/documents/<uuid:id>/` (and `/api/documents/<uuid:id>/delete/`)
Soft-delete an active or archived document.
- Sets `status="deleted"`, records `deleted_at` timestamp and `deleted_by`.
- Retains physical bytes for potential recovery until explicit purge.
- Records a `DOCUMENT_DELETE` audit event.
- **Response (204 No Content)**

### `POST /api/documents/<uuid:id>/archive/`
Archive an active document.
- Sets `status="archived"` and records `archived_at`.
- Records a `DOCUMENT_ARCHIVE` audit event.
- **Response (200 OK):** Updated document detail object.

### `POST /api/documents/<uuid:id>/restore/`
Restore an archived document back to `active`.
- Clears `archived_at` and sets `status="active"`.
- Records a `DOCUMENT_RESTORE` audit event.
- **Response (200 OK):** Updated document detail object.

### `POST /api/documents/<uuid:id>/purge/`
Permanently destroy physical file bytes of a soft-deleted document.
- Removes physical storage file from disk.
- Sets `purged_at` timestamp on database record to maintain immutable audit reference.
- Records a `DOCUMENT_PURGE` audit event.
- **Response (204 No Content)**
