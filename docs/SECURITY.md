# DocTrust Security Architecture & Controls

## 1. Threat Model & Principles

DocTrust enforces enterprise security principles:
1. **Zero Public Media**: Document files are never exposed through public URL routes or static file servers (e.g. Nginx alias or Django `MEDIA_URL`). All downloads require authenticated view handlers.
2. **Principle of Least Privilege & Role Isolation**:
   - `EMPLOYEE` is the document owner and workspace operator.
   - `ADMIN` manages user credentials and inspects system logs, but is **cryptographically and authoritatively barred** from viewing or accessing private employee documents or folder contents.
   - Any ADMIN request to `/api/documents/` or `/api/folders/` yields `403 Forbidden`.
3. **Defense in Depth**: Document-folder ownership integrity is enforced at:
   - Request serializer validation (`DocumentMetadataUpdateSerializer` and `DocumentUploadSerializer`).
   - Django ORM model validation (`Document.clean()`).
   - Database-level integrity: composite foreign key `(folder_id, owner_id) REFERENCES documents_folder(id, owner_id)`.

---

## 2. Cross-Owner Isolation & Folder Integrity

### Problem
In multi-tenant or multi-employee environments, a subtle vulnerability occurs when a user assigns their document to a folder owned by another employee (`user2`), inadvertently leaking folder hierarchy or bypassing ACL boundaries.

### Solution
1. **Composite Foreign Key**:
   In `documents/models.py`, `Folder` defines a unique constraint:
   ```python
   models.UniqueConstraint(fields=["id", "owner"], name="unique_folder_id_owner")
   ```
   And `Document` defines a composite foreign key constraint at PostgreSQL level:
   ```sql
   ALTER TABLE documents_document
   ADD CONSTRAINT documents_document_folder_owner_fk
   FOREIGN KEY (folder_id, owner_id)
   REFERENCES documents_folder (id, owner_id)
   ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE;
   ```
2. **Verification**: Even if an attacker bypasses Django application-level code using raw SQL or `QuerySet.update()`, PostgreSQL rejects cross-owner assignment with `IntegrityError`.

---

## 3. Encapsulated Private Storage Pipeline

1. **Storage Keys**:
   - Files are stored with high-entropy cryptographic keys (64-character hex strings generated via `os.urandom(32).hex()`).
   - The storage key is **never** derived from or influenced by the user's uploaded filename.
   - The storage key is **never** included in API responses (explicitly excluded from serializers and audited to ensure no leakage).
2. **Path Traversal Prevention**:
   - Every read and write validates path containment using resolved filesystem paths:
     ```python
     full_path = (self._root / storage_key).resolve()
     if not full_path.is_relative_to(self._root):
         raise SuspiciousFileOperation("Storage key traversal detected")
     ```
3. **Orphan File Prevention**:
   - When a user uploads a file, bytes are written to storage first.
   - The database record and audit log are created inside a database transaction `with transaction.atomic():`.
   - If the database write or audit logging fails, the stored file is deleted in a `try/except` block to prevent orphaned files.

---

## 4. Upload Content Validation

DocTrust validates uploaded documents against malicious payloads:
1. **Extension Whitelist**: Only `.pdf`, `.docx`, `.xlsx`, `.pptx` are accepted.
2. **MIME & Magic Bytes**: Magic headers are verified (e.g., `%PDF` for PDF, ZIP signature `PK\x03\x04` with OOXML Content Types for Office documents).
3. **PDF Dangerous Script Scanning**: PDFs are scanned for active scripting elements:
   - `/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFiles`, `/RichMedia`.
4. **Quota & Size Limits**:
   - Max file size: 50 MB per document.
   - User quota: 500 MB per employee across active documents.

---

## 5. Audit Logging Architecture

1. **Fail-Closed Guarantee**: Security-critical actions (`DOCUMENT_UPLOAD`, `DOCUMENT_DELETE`, `DOCUMENT_PURGE`, `DOCUMENT_UPDATE`, `FOLDER_CREATE`, `FOLDER_RENAME`, `FOLDER_DELETE`) are fail-closed: if the audit event cannot be persisted to PostgreSQL, the primary transaction is aborted and rolled back.
2. **Non-Repudiation**:
   - Actor, action, target entity type, target entity ID, IP address, user agent, and timestamp are captured on every event.
   - Read actions (`DOCUMENT_VIEW`, `DOCUMENT_DOWNLOAD`) record audit events without blocking file download if the audit log experiences transient read-only load.
