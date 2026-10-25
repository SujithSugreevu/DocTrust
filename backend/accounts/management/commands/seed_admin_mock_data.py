"""
DocTrust Management Command: seed_admin_mock_data

Seeds 50 realistic demonstration records into PostgreSQL for the Administrator and Employee portals:
- 12 Employee Accounts (HR, Finance, Engineering, Design, Operations, Legal)
- 15 Real Documents (PDF, DOCX, XLSX, PPTX) with valid file bytes written to PrivateDocumentStorage
- 5 Folders (HR, Finance, Projects, Design, Legal)
- 8 Document Permission / Sharing grants
- 6 Activity / Audit demonstration events
- 4 Notifications / Security Alerts

Total: 50 primary demonstration records.

CONSTRAINTS & SAFETY:
- Restricted to development/test environments (requires settings.DEBUG=True).
- Fully idempotent: existing accounts, documents, folders, shares, and alerts are detected and preserved.
- No existing accounts, passwords, or data are overwritten or deleted.
"""

import hashlib
import io
import re
import secrets
import zipfile
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from documents.models import Document, Folder, DocumentShare
from documents.storage import PrivateDocumentStorage
from auditlog.models import AuditEvent, SecurityAlert

User = get_user_model()


def generate_valid_pdf_bytes(title: str, author: str) -> bytes:
    """Generate a syntactically valid PDF 1.4 document."""
    escaped_title = re.sub(r"[()]", "", title)
    escaped_author = re.sub(r"[()]", "", author)
    text_content = f"DocTrust Protected Document: {escaped_title} | Owner: {escaped_author}"
    stream_bytes = f"BT /F1 14 Tf 50 720 Td ({text_content}) Tj ET\n".encode("utf-8")
    stream_len = len(stream_bytes)

    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(stream_len).encode("ascii") + b" >>\nstream\n"
        + stream_bytes +
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000244 00000 n \n"
        b"0000000350 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n430\n%%EOF\n"
    )
    return pdf


def generate_valid_docx_bytes(title: str, author: str) -> bytes:
    """Generate a valid Office OpenXML Word Document (.docx)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>'
        )
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body><w:p><w:r><w:t>DocTrust Managed Document: {title} (Author: {author})</w:t></w:r></w:p></w:body>'
            '</w:document>'
        )
    return buf.getvalue()


def generate_valid_xlsx_bytes(title: str, author: str) -> bytes:
    """Generate a valid Office OpenXML Spreadsheet (.xlsx)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '</Types>'
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )
        safe_sheet_name = (title[:25] or "Sheet1").replace("[", "").replace("]", "").replace("*", "")
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets><sheet name="{safe_sheet_name}" sheetId="1" r:id="rId1"/></sheets>'
            '</workbook>'
        )
    return buf.getvalue()


def generate_valid_pptx_bytes(title: str, author: str) -> bytes:
    """Generate a valid Office OpenXML Presentation (.pptx)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
            '</Types>'
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
            '</Relationships>'
        )
        z.writestr(
            "ppt/presentation.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:sldIdLst/>'
            '</p:presentation>'
        )
    return buf.getvalue()


class Command(BaseCommand):
    help = "Seeds 50 realistic demonstration records (12 employees, 15 documents with real storage, 5 folders, 8 shares, 6 audit logs, 4 alerts)."

    def handle(self, *args, **options):
        # 1. Environment Safety Guard
        if not settings.DEBUG:
            raise CommandError(
                "SECURITY GUARD: 'seed_admin_mock_data' is strictly restricted to local development "
                "environments where DEBUG=True. Execution halted."
            )

        self.stdout.write("============================================================")
        self.stdout.write("DocTrust — Seeding 50 Realistic Demonstration Records")
        self.stdout.write("============================================================")

        now = timezone.now()
        storage = PrivateDocumentStorage()
        created_counts = {
            "employees": 0,
            "folders": 0,
            "documents": 0,
            "shares": 0,
            "audit_logs": 0,
            "notifications": 0,
        }
        preserved_counts = {
            "employees": 0,
            "folders": 0,
            "documents": 0,
            "shares": 0,
            "audit_logs": 0,
            "notifications": 0,
        }

        # ------------------------------------------------------------------
        # 1. Employee accounts — 12
        # ------------------------------------------------------------------
        self.stdout.write("\n[1/6] Seeding 12 Employee Accounts...")
        employee_specs = [
            {"username": "sarah.jenkins", "email": "sarah.jenkins@doctrust.local", "first": "Sarah", "last": "Jenkins", "dept": "HR", "title": "Head of People & Culture"},
            {"username": "marcus.vance", "email": "marcus.vance@doctrust.local", "first": "Marcus", "last": "Vance", "dept": "Engineering", "title": "Lead Software Architect"},
            {"username": "elena.rostova", "email": "elena.rostova@doctrust.local", "first": "Elena", "last": "Rostova", "dept": "Finance", "title": "Chief Financial Controller"},
            {"username": "david.kim", "email": "david.kim@doctrust.local", "first": "David", "last": "Kim", "dept": "Design", "title": "Principal Product Designer"},
            {"username": "rachel.green", "email": "rachel.green@doctrust.local", "first": "Rachel", "last": "Green", "dept": "Legal", "title": "Senior Corporate Counsel"},
            {"username": "carlos.mendez", "email": "carlos.mendez@doctrust.local", "first": "Carlos", "last": "Mendez", "dept": "Operations", "title": "Director of Operations"},
            {"username": "priya.sharma", "email": "priya.sharma@doctrust.local", "first": "Priya", "last": "Sharma", "dept": "Engineering", "title": "Senior Cloud Infrastructure Engineer"},
            {"username": "thomas.wright", "email": "thomas.wright@doctrust.local", "first": "Thomas", "last": "Wright", "dept": "Finance", "title": "Senior Financial Planning Analyst"},
            {"username": "aaliyah.patel", "email": "aaliyah.patel@doctrust.local", "first": "Aaliyah", "last": "Patel", "dept": "HR", "title": "Talent Acquisition Lead"},
            {"username": "lucas.moreau", "email": "lucas.moreau@doctrust.local", "first": "Lucas", "last": "Moreau", "dept": "Design", "title": "Design Systems Engineer"},
            {"username": "jessica.taylor", "email": "jessica.taylor@doctrust.local", "first": "Jessica", "last": "Taylor", "dept": "Legal", "title": "Data Protection Officer"},
            {
                "username": "nathaniel.brooks",
                "email": "nathaniel.brooks@doctrust.local",
                "first": "Nathaniel",
                "last": "Brooks",
                "dept": "Operations",
                "title": "Logistics Coordinator",
                "status": User.Status.SUSPENDED,
                "reason": "Pending annual security & data protection compliance refresher.",
            },
        ]

        employee_map = {}
        for spec in employee_specs:
            user = User.objects.filter(username=spec["username"]).first()
            if not user:
                is_suspended = spec.get("status") == User.Status.SUSPENDED
                user = User.objects.create_user(
                    username=spec["username"],
                    email=spec["email"],
                    password="DemoUser!2026",
                    role=User.Role.EMPLOYEE,
                    status=spec.get("status", User.Status.ACTIVE),
                    first_name=spec["first"],
                    last_name=spec["last"],
                    is_staff=False,
                    is_superuser=False,
                    suspended_at=now - timedelta(days=2) if is_suspended else None,
                    suspension_end=now + timedelta(days=5) if is_suspended else None,
                    suspension_reason=spec.get("reason", "") if is_suspended else "",
                )
                created_counts["employees"] += 1
                self.stdout.write(f"  + Created employee: {user.get_full_name()} ({user.username}) - {spec['dept']}")
            else:
                preserved_counts["employees"] += 1
                self.stdout.write(f"  = Preserved employee: {user.get_full_name()} ({user.username})")
            employee_map[spec["username"]] = user

        # ------------------------------------------------------------------
        # 2. Folders and categories — 5
        # ------------------------------------------------------------------
        self.stdout.write("\n[2/6] Seeding 5 Department Folders...")
        folder_specs = [
            {"name": "HR", "owner_username": "sarah.jenkins"},
            {"name": "Finance", "owner_username": "elena.rostova"},
            {"name": "Projects", "owner_username": "marcus.vance"},
            {"name": "Design", "owner_username": "david.kim"},
            {"name": "Legal", "owner_username": "rachel.green"},
        ]

        folder_map = {}
        for spec in folder_specs:
            owner = employee_map[spec["owner_username"]]
            folder = Folder.objects.filter(owner=owner, name=spec["name"]).first()
            if not folder:
                folder = Folder.objects.create(owner=owner, name=spec["name"])
                created_counts["folders"] += 1
                self.stdout.write(f"  + Created folder: '{folder.name}' (Owner: {owner.username})")
            else:
                preserved_counts["folders"] += 1
                self.stdout.write(f"  = Preserved folder: '{folder.name}' (Owner: {owner.username})")
            folder_map[spec["name"]] = folder

        # ------------------------------------------------------------------
        # 3. Documents — 15
        # ------------------------------------------------------------------
        self.stdout.write("\n[3/6] Seeding 15 Real Documents (generating valid physical storage bytes)...")
        document_specs = [
            {
                "name": "Employee_Handbook_2026.pdf",
                "file_type": Document.FileType.PDF,
                "owner": "sarah.jenkins",
                "folder": "HR",
                "status": Document.Status.ACTIVE,
                "description": "Comprehensive employee handbook covering remote work, ethics, and code of conduct.",
            },
            {
                "name": "Standard_Employment_Agreement.docx",
                "file_type": Document.FileType.DOCX,
                "owner": "sarah.jenkins",
                "folder": "HR",
                "status": Document.Status.ACTIVE,
                "description": "Enterprise standard employment contract template for full-time staff.",
            },
            {
                "name": "Annual_Talent_Review_Q3.xlsx",
                "file_type": Document.FileType.XLSX,
                "owner": "aaliyah.patel",
                "folder": None,
                "status": Document.Status.ACTIVE,
                "description": "Performance ratings, talent benchmarking, and departmental headcount projections.",
            },
            {
                "name": "Q3_Financial_Performance_Audit.pdf",
                "file_type": Document.FileType.PDF,
                "owner": "elena.rostova",
                "folder": "Finance",
                "status": Document.Status.ACTIVE,
                "description": "Audited quarterly financial statements, cash flow margins, and balance sheets.",
            },
            {
                "name": "Corporate_Tax_Filing_FY25.xlsx",
                "file_type": Document.FileType.XLSX,
                "owner": "elena.rostova",
                "folder": "Finance",
                "status": Document.Status.ARCHIVED,
                "description": "Archived corporate federal and state tax filings and reconciliations.",
            },
            {
                "name": "Vendor_Billing_Schedule_2026.xlsx",
                "file_type": Document.FileType.XLSX,
                "owner": "thomas.wright",
                "folder": None,
                "status": Document.Status.ACTIVE,
                "description": "Quarterly vendor invoice schedule and accounts payable disbursements.",
            },
            {
                "name": "Microservices_Architecture_v2.pdf",
                "file_type": Document.FileType.PDF,
                "owner": "marcus.vance",
                "folder": "Projects",
                "status": Document.Status.ACTIVE,
                "description": "Architecture diagram, service boundaries, and data contract specifications.",
            },
            {
                "name": "Cloud_Infrastructure_Deployment_Plan.pptx",
                "file_type": Document.FileType.PPTX,
                "owner": "priya.sharma",
                "folder": None,
                "status": Document.Status.ACTIVE,
                "description": "Cloud migration roadmap, high-availability clusters, and disaster recovery tiers.",
            },
            {
                "name": "Security_Hardening_Technical_Spec.docx",
                "file_type": Document.FileType.DOCX,
                "owner": "marcus.vance",
                "folder": "Projects",
                "status": Document.Status.ACTIVE,
                "description": "Zero-trust network configuration, token rotations, and encryption standards.",
            },
            {
                "name": "Brand_Identity_Guidelines_2026.pdf",
                "file_type": Document.FileType.PDF,
                "owner": "david.kim",
                "folder": "Design",
                "status": Document.Status.ACTIVE,
                "description": "DocTrust visual brand system, typography scales, accessibility contrasts, and assets.",
            },
            {
                "name": "Design_System_Component_Specs.docx",
                "file_type": Document.FileType.DOCX,
                "owner": "lucas.moreau",
                "folder": None,
                "status": Document.Status.ACTIVE,
                "description": "Reusable UI components, interactive states, token variables, and layout guidelines.",
            },
            {
                "name": "Mobile_App_Wireframes_Master.pptx",
                "file_type": Document.FileType.PPTX,
                "owner": "david.kim",
                "folder": "Design",
                "status": Document.Status.ACTIVE,
                "description": "High-fidelity mobile experience walkthroughs for iOS and Android.",
            },
            {
                "name": "Master_Services_Agreement_Template.docx",
                "file_type": Document.FileType.DOCX,
                "owner": "rachel.green",
                "folder": "Legal",
                "status": Document.Status.ACTIVE,
                "description": "Standard client engagement terms, warranties, liability caps, and governance.",
            },
            {
                "name": "GDPR_Compliance_Audit_Report.pdf",
                "file_type": Document.FileType.PDF,
                "owner": "jessica.taylor",
                "folder": None,
                "status": Document.Status.ARCHIVED,
                "description": "Annual GDPR compliance gap assessment, DPIA summaries, and privacy audit logs.",
            },
            {
                "name": "Data_Processing_Addendum_v3.pdf",
                "file_type": Document.FileType.PDF,
                "owner": "rachel.green",
                "folder": "Legal",
                "status": Document.Status.ACTIVE,
                "description": "GDPR Article 28 data processor terms and technical safeguards schedule.",
            },
        ]

        document_map = {}
        for spec in document_specs:
            owner = employee_map[spec["owner"]]
            folder = folder_map.get(spec["folder"]) if spec["folder"] else None

            # Verify folder ownership constraint
            if folder and folder.owner_id != owner.id:
                folder = None

            existing_doc = Document.objects.filter(owner=owner, name=spec["name"]).first()
            if not existing_doc:
                # Generate real physical bytes
                if spec["file_type"] == Document.FileType.PDF:
                    file_bytes = generate_valid_pdf_bytes(spec["name"], owner.get_full_name())
                elif spec["file_type"] == Document.FileType.DOCX:
                    file_bytes = generate_valid_docx_bytes(spec["name"], owner.get_full_name())
                elif spec["file_type"] == Document.FileType.XLSX:
                    file_bytes = generate_valid_xlsx_bytes(spec["name"], owner.get_full_name())
                elif spec["file_type"] == Document.FileType.PPTX:
                    file_bytes = generate_valid_pptx_bytes(spec["name"], owner.get_full_name())
                else:
                    file_bytes = f"DocTrust Content: {spec['name']}".encode("utf-8")

                storage_key = PrivateDocumentStorage.generate_storage_key()
                sha256 = hashlib.sha256(file_bytes).hexdigest()
                size = len(file_bytes)

                # Persist bytes through DocTrust storage adapter
                storage.save_stream(file_bytes, storage_key)

                doc = Document.objects.create(
                    owner=owner,
                    folder=folder,
                    name=spec["name"],
                    original_filename=spec["name"],
                    description=spec["description"],
                    file_type=spec["file_type"],
                    size=size,
                    sha256=sha256,
                    storage_key=storage_key,
                    status=spec["status"],
                    archived_at=now - timedelta(days=10) if spec["status"] == Document.Status.ARCHIVED else None,
                )
                created_counts["documents"] += 1
                self.stdout.write(f"  + Created document: '{doc.name}' ({doc.file_type}, {doc.size} bytes, Owner: {owner.username})")
                document_map[spec["name"]] = doc
            else:
                preserved_counts["documents"] += 1
                self.stdout.write(f"  = Preserved document: '{existing_doc.name}' ({existing_doc.file_type}, Owner: {owner.username})")
                document_map[spec["name"]] = existing_doc

        # ------------------------------------------------------------------
        # 4. Document permission/sharing records — 8
        # ------------------------------------------------------------------
        self.stdout.write("\n[4/6] Seeding 8 Document Permission & Sharing Grants...")
        share_specs = [
            {"doc_name": "Employee_Handbook_2026.pdf", "recipient": "marcus.vance", "perm": DocumentShare.Permission.VIEW},
            {"doc_name": "Employee_Handbook_2026.pdf", "recipient": "elena.rostova", "perm": DocumentShare.Permission.VIEW},
            {"doc_name": "Standard_Employment_Agreement.docx", "recipient": "rachel.green", "perm": DocumentShare.Permission.EDIT},
            {"doc_name": "Q3_Financial_Performance_Audit.pdf", "recipient": "sarah.jenkins", "perm": DocumentShare.Permission.DOWNLOAD},
            {"doc_name": "Microservices_Architecture_v2.pdf", "recipient": "priya.sharma", "perm": DocumentShare.Permission.EDIT},
            {"doc_name": "Brand_Identity_Guidelines_2026.pdf", "recipient": "lucas.moreau", "perm": DocumentShare.Permission.EDIT},
            {"doc_name": "Master_Services_Agreement_Template.docx", "recipient": "elena.rostova", "perm": DocumentShare.Permission.DOWNLOAD},
            {"doc_name": "Security_Hardening_Technical_Spec.docx", "recipient": "carlos.mendez", "perm": DocumentShare.Permission.VIEW},
        ]

        for s in share_specs:
            doc = document_map.get(s["doc_name"])
            recipient = employee_map.get(s["recipient"])
            if not doc or not recipient:
                continue

            share = DocumentShare.objects.filter(document=doc, recipient=recipient).first()
            if not share:
                share = DocumentShare.objects.create(
                    document=doc,
                    recipient=recipient,
                    permission=s["perm"],
                    expires_at=now + timedelta(days=90),
                )
                created_counts["shares"] += 1
                self.stdout.write(f"  + Created share: '{doc.name}' -> {recipient.username} ({share.permission})")
            else:
                preserved_counts["shares"] += 1
                self.stdout.write(f"  = Preserved share: '{doc.name}' -> {recipient.username} ({share.permission})")

        # ------------------------------------------------------------------
        # 5. Activity/audit demonstration records — 6
        # ------------------------------------------------------------------
        self.stdout.write("\n[5/6] Seeding 6 Demonstration Activity Audit Events...")
        audit_specs = [
            {
                "actor": "elena.rostova",
                "action": AuditEvent.Action.DOCUMENT_UPLOAD,
                "target_type": "documents.Document",
                "target_id": str(document_map["Q3_Financial_Performance_Audit.pdf"].id),
                "ip": "192.168.10.15",
                "marker": "demo_audit_upload_q3",
            },
            {
                "actor": "sarah.jenkins",
                "action": AuditEvent.Action.DOCUMENT_SHARE,
                "target_type": "documents.Document",
                "target_id": str(document_map["Standard_Employment_Agreement.docx"].id),
                "ip": "192.168.10.22",
                "marker": "demo_audit_share_agreement",
            },
            {
                "actor": "marcus.vance",
                "action": AuditEvent.Action.DOCUMENT_DOWNLOAD,
                "target_type": "documents.Document",
                "target_id": str(document_map["Employee_Handbook_2026.pdf"].id),
                "ip": "192.168.10.45",
                "marker": "demo_audit_download_handbook",
            },
            {
                "actor": "david.kim",
                "action": AuditEvent.Action.DOCUMENT_UPDATE,
                "target_type": "documents.Document",
                "target_id": str(document_map["Brand_Identity_Guidelines_2026.pdf"].id),
                "ip": "192.168.10.51",
                "marker": "demo_audit_update_brand",
            },
            {
                "actor": "elena.rostova",
                "action": AuditEvent.Action.DOCUMENT_ARCHIVE,
                "target_type": "documents.Document",
                "target_id": str(document_map["Corporate_Tax_Filing_FY25.xlsx"].id),
                "ip": "192.168.10.15",
                "marker": "demo_audit_archive_tax",
            },
            {
                "actor": "marcus.vance",
                "action": AuditEvent.Action.LOGIN_SUCCESS,
                "target_type": "accounts.User",
                "target_id": str(employee_map["marcus.vance"].id),
                "ip": "192.168.10.45",
                "marker": "demo_audit_login_marcus",
            },
        ]

        for spec in audit_specs:
            actor = employee_map.get(spec["actor"])
            marker = spec["marker"]

            existing_event = AuditEvent.objects.filter(
                actor=actor,
                action=spec["action"],
                target_id=spec["target_id"],
            ).first()

            if not existing_event:
                AuditEvent.objects.create(
                    actor=actor,
                    action=spec["action"],
                    target_type=spec["target_type"],
                    target_id=spec["target_id"],
                    ip_address=spec["ip"],
                    metadata={
                        "notes": f"Demonstration audit trail record ({marker})",
                        "status": "Demonstration",
                    },
                )
                created_counts["audit_logs"] += 1
                self.stdout.write(f"  + Created audit event: {spec['action']} by {actor.username}")
            else:
                preserved_counts["audit_logs"] += 1
                self.stdout.write(f"  = Preserved audit event: {spec['action']} by {actor.username}")

        # ------------------------------------------------------------------
        # 6. Notifications / Security Alerts — 4
        # ------------------------------------------------------------------
        self.stdout.write("\n[6/6] Seeding 4 Demonstration Notifications / Security Alerts...")
        admin_user = User.objects.filter(role=User.Role.ADMIN).first() or employee_map["sarah.jenkins"]

        alert_specs = [
            {
                "title": "Unusual off-hours document export pattern",
                "severity": SecurityAlert.Severity.MEDIUM,
                "status": SecurityAlert.Status.OPEN,
                "scope": SecurityAlert.Scope.EMPLOYEE,
                "alert_type": "UNUSUAL_EXPORT_PATTERN",
                "details": "Demonstration notification: Batch export threshold exceeded outside standard business hours.",
                "target": employee_map["nathaniel.brooks"],
                "ip": "192.168.10.92",
            },
            {
                "title": "Multiple concurrent login sessions detected",
                "severity": SecurityAlert.Severity.LOW,
                "status": SecurityAlert.Status.OPEN,
                "scope": SecurityAlert.Scope.EMPLOYEE,
                "alert_type": "CONCURRENT_SESSIONS",
                "details": "Demonstration notification: User authenticated on two distinct subnet IP ranges within 5 minutes.",
                "target": employee_map["marcus.vance"],
                "ip": "192.168.10.45",
            },
            {
                "title": "Repeated failed document access authorization",
                "severity": SecurityAlert.Severity.HIGH,
                "status": SecurityAlert.Status.REVIEW,
                "scope": SecurityAlert.Scope.EMPLOYEE,
                "alert_type": "ACCESS_DENIED_REPEATED",
                "details": "Demonstration notification: Consecutive unauthorized access attempts on restricted legal documents.",
                "target": employee_map["carlos.mendez"],
                "ip": "192.168.10.77",
            },
            {
                "title": "Privileged administrator session idle timeout",
                "severity": SecurityAlert.Severity.LOW,
                "status": SecurityAlert.Status.RESOLVED,
                "scope": SecurityAlert.Scope.ADMIN,
                "alert_type": "IDLE_TIMEOUT_TRIGGERED",
                "details": "Demonstration notification: Administrative session terminated automatically after inactivity window.",
                "target": admin_user,
                "ip": "127.0.0.1",
                "resolved_by": admin_user,
            },
        ]

        for spec in alert_specs:
            existing_alert = SecurityAlert.objects.filter(alert_type=spec["alert_type"]).first()
            if not existing_alert:
                alert = SecurityAlert.objects.create(
                    title=spec["title"],
                    severity=spec["severity"],
                    status=spec["status"],
                    scope=spec["scope"],
                    alert_type=spec["alert_type"],
                    details=spec["details"],
                    target_user=spec["target"],
                    ip_address=spec["ip"],
                    resolved_by=spec.get("resolved_by"),
                    resolved_at=now if spec.get("resolved_by") else None,
                    resolution_notes="Authorized administrative session policy validation." if spec.get("resolved_by") else "",
                )
                created_counts["notifications"] += 1
                self.stdout.write(f"  + Created alert/notification: '{alert.title}' ({alert.severity}, {alert.status})")
            else:
                preserved_counts["notifications"] += 1
                self.stdout.write(f"  = Preserved alert/notification: '{existing_alert.title}' ({existing_alert.severity})")

        # ------------------------------------------------------------------
        # Final Summary
        # ------------------------------------------------------------------
        total_created = sum(created_counts.values())
        total_preserved = sum(preserved_counts.values())

        self.stdout.write("\n============================================================")
        self.stdout.write(self.style.SUCCESS(f"Seeding completed successfully!"))
        self.stdout.write(f"New Demonstration Records Created: {total_created}")
        self.stdout.write(f"Existing Records Preserved:       {total_preserved}")
        self.stdout.write("Breakdown:")
        self.stdout.write(f"  * Employee accounts:                  {created_counts['employees']} created ({preserved_counts['employees']} preserved)")
        self.stdout.write(f"  * Documents (with real file storage): {created_counts['documents']} created ({preserved_counts['documents']} preserved)")
        self.stdout.write(f"  * Folders & Categories:               {created_counts['folders']} created ({preserved_counts['folders']} preserved)")
        self.stdout.write(f"  * Document Permission Shares:         {created_counts['shares']} created ({preserved_counts['shares']} preserved)")
        self.stdout.write(f"  * Activity / Audit Logs:              {created_counts['audit_logs']} created ({preserved_counts['audit_logs']} preserved)")
        self.stdout.write(f"  * Notifications & Security Alerts:    {created_counts['notifications']} created ({preserved_counts['notifications']} preserved)")
        self.stdout.write("============================================================\n")
