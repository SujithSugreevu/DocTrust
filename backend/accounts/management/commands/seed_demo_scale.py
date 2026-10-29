"""Add the deterministic scale portion of the DocTrust demo dataset."""

import hashlib
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.management.commands.demo_seed_support import (
    ensure_demo_seed_allowed,
    ensure_demo_storage_is_persistent,
)
from accounts.management.commands.seed_admin_mock_data import (
    generate_valid_docx_bytes,
    generate_valid_pdf_bytes,
    generate_valid_pptx_bytes,
    generate_valid_xlsx_bytes,
)
from accounts.models import User
from auditlog.models import AuditEvent, SecurityAlert
from documents.models import Document, DocumentShare, EmployeeNotification, Folder
from documents.storage import PrivateDocumentStorage, StorageError


SCALE_USER_COUNT = 30
SCALE_FOLDER_COUNT = 30
SCALE_DOCUMENT_COUNT = 120
SCALE_SHARE_COUNT = 80
SCALE_AUDIT_COUNT = 120
SCALE_NOTIFICATION_COUNT = 30
SCALE_ALERT_COUNT = 10

FILE_TYPES = (
    (Document.FileType.PDF, generate_valid_pdf_bytes),
    (Document.FileType.DOCX, generate_valid_docx_bytes),
    (Document.FileType.XLSX, generate_valid_xlsx_bytes),
    (Document.FileType.PPTX, generate_valid_pptx_bytes),
)
AUDIT_ACTIONS = (
    AuditEvent.Action.DOCUMENT_UPLOAD,
    AuditEvent.Action.DOCUMENT_VIEW,
    AuditEvent.Action.DOCUMENT_UPDATE,
    AuditEvent.Action.DOCUMENT_DOWNLOAD,
    AuditEvent.Action.DOCUMENT_ARCHIVE,
    AuditEvent.Action.DOCUMENT_SHARE,
)


def scale_username(index):
    return f"scale_demo_employee_{index:03d}"


def scale_email(index):
    return f"scale_demo_employee_{index:03d}@demo.doctrust.local"


def scale_folder_name(index):
    return f"Scale Demo Folder {index:03d}"


def scale_document_name(index, file_type):
    return f"Scale_Demo_Document_{index:03d}.{file_type.lower()}"


class Command(BaseCommand):
    help = "Seed approximately 400 additional coordinated DocTrust demonstration records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-production-demo",
            action="store_true",
            help="Allow deliberate production demo seeding only when DOCTRUST_DEMO_MODE is enabled.",
        )

    def handle(self, *args, **options):
        ensure_demo_seed_allowed(options)
        ensure_demo_storage_is_persistent()

        now = timezone.now()
        storage = PrivateDocumentStorage()
        counts = {
            "users": 0,
            "folders": 0,
            "documents": 0,
            "shares": 0,
            "audit": 0,
            "notifications": 0,
            "alerts": 0,
            "repaired_files": 0,
        }
        preserved = {key: 0 for key in counts}
        conflicts = []

        employees = []
        for index in range(1, SCALE_USER_COUNT + 1):
            username = scale_username(index)
            email = scale_email(index)
            user = User.objects.filter(username=username).first()
            if user is None:
                email_conflict = User.objects.filter(email=email).first()
                if email_conflict is not None:
                    conflicts.append(f"email {email} is already used by another account")
                    continue
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=None,
                    first_name="Scale Demo",
                    last_name=f"Employee {index:03d}",
                    role=User.Role.EMPLOYEE,
                    status=User.Status.SUSPENDED if index % 10 == 0 else User.Status.ACTIVE,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                )
                counts["users"] += 1
            else:
                preserved["users"] += 1
            if user.role == User.Role.EMPLOYEE:
                employees.append(user)
            else:
                conflicts.append(f"{username} exists with a non-EMPLOYEE role")

        folders = []
        for index, owner in enumerate(employees, start=1):
            name = scale_folder_name(index)
            folder = Folder.objects.filter(owner=owner, name=name).first()
            if folder is None:
                folder = Folder.objects.create(owner=owner, name=name)
                counts["folders"] += 1
            else:
                preserved["folders"] += 1
            folders.append(folder)

        documents = []
        for index in range(1, SCALE_DOCUMENT_COUNT + 1):
            if not employees:
                break
            file_type, generator = FILE_TYPES[(index - 1) % len(FILE_TYPES)]
            owner = employees[(index - 1) % len(employees)]
            folder = folders[(index - 1) % len(folders)] if folders else None
            name = scale_document_name(index, file_type)
            description = f"Scale demonstration record: document {index:03d} for coordinated dashboard testing."
            document = Document.objects.filter(owner=owner, name=name).first()

            if document is not None and document.description != description:
                conflicts.append(f"document {owner.username}/{name} already exists with different metadata")
                continue

            file_bytes = generator(name, owner.get_full_name() or owner.username)
            if document is None:
                storage_key = PrivateDocumentStorage.generate_storage_key()
                storage.save_stream(file_bytes, storage_key)
                try:
                    with transaction.atomic():
                        document = Document.objects.create(
                            owner=owner,
                            folder=folder,
                            name=name,
                            original_filename=name,
                            description=description,
                            file_type=file_type,
                            size=len(file_bytes),
                            sha256=hashlib.sha256(file_bytes).hexdigest(),
                            storage_key=storage_key,
                            status=Document.Status.ARCHIVED if index % 17 == 0 else Document.Status.ACTIVE,
                            archived_at=now - timedelta(days=10) if index % 17 == 0 else None,
                        )
                except Exception:
                    try:
                        storage.delete(storage_key)
                    except StorageError:
                        pass
                    raise
                counts["documents"] += 1
            else:
                preserved["documents"] += 1
                if document.folder_id != getattr(folder, "id", None):
                    document.folder = folder
                    document.save(update_fields=["folder", "updated_at"])
                if not storage.exists(document.storage_key):
                    storage.save_stream(file_bytes, document.storage_key)
                    counts["repaired_files"] += 1
            documents.append(document)

        active_recipients = [
            employee for employee in employees
            if employee.status == User.Status.ACTIVE and employee.is_active
        ]
        employee_demo = User.objects.filter(
            username="employee_demo",
            role=User.Role.EMPLOYEE,
            status=User.Status.ACTIVE,
            is_active=True,
        ).first()
        share_records = []
        if documents and active_recipients:
            for index in range(SCALE_SHARE_COUNT):
                document = documents[index % len(documents)]
                if index < SCALE_NOTIFICATION_COUNT and employee_demo and document.owner_id != employee_demo.id:
                    recipient = employee_demo
                else:
                    candidates = [user for user in active_recipients if user.pk != document.owner_id]
                    if not candidates:
                        continue
                    recipient = candidates[index % len(candidates)]

                share, created = DocumentShare.objects.get_or_create(
                    document=document,
                    recipient=recipient,
                    defaults={
                        "permission": DocumentShare.Permission.EDIT
                        if index % 3 == 0
                        else DocumentShare.Permission.DOWNLOAD
                        if index % 3 == 1
                        else DocumentShare.Permission.VIEW,
                        "expires_at": now + timedelta(days=180),
                    },
                )
                share_records.append(share)
                counts["shares"] += int(created)
                preserved["shares"] += int(not created)

        for index in range(SCALE_AUDIT_COUNT):
            if not documents or not employees:
                break
            marker = f"scale-demo:audit:{index + 1:03d}"
            if AuditEvent.objects.filter(metadata__notes=marker).exists():
                preserved["audit"] += 1
                continue
            actor = employees[index % len(employees)]
            document = documents[index % len(documents)]
            AuditEvent.objects.create(
                actor=actor,
                action=AUDIT_ACTIONS[index % len(AUDIT_ACTIONS)],
                target_type="documents.Document",
                target_id=str(document.pk),
                ip_address=f"198.51.100.{(index % 200) + 1}",
                metadata={
                    "notes": marker,
                    "status": "Demonstration",
                },
            )
            counts["audit"] += 1

        if employee_demo:
            employee_shares = [
                share for share in share_records
                if share.recipient_id == employee_demo.id
            ]
            for index, share in enumerate(employee_shares[:SCALE_NOTIFICATION_COUNT], start=1):
                event_key = f"scale-demo:notification:{index:03d}"
                _notification, created = EmployeeNotification.objects.get_or_create(
                    event_key=event_key,
                    defaults={
                        "recipient": employee_demo,
                        "document": share.document,
                        "message": (
                            f"Scale demonstration: {share.document.name} was shared with you "
                            f"({share.get_permission_display()})."
                        ),
                    },
                )
                counts["notifications"] += int(created)
                preserved["notifications"] += int(not created)

        for index in range(1, SCALE_ALERT_COUNT + 1):
            alert_type = f"SCALE_DEMO_ALERT_{index:03d}"
            target = employees[(index - 1) % len(employees)] if employees else None
            _alert, created = SecurityAlert.objects.get_or_create(
                alert_type=alert_type,
                defaults={
                    "title": f"Scale demonstration security event {index:03d}",
                    "severity": SecurityAlert.Severity.MEDIUM if index % 2 else SecurityAlert.Severity.LOW,
                    "status": SecurityAlert.Status.REVIEW if index % 3 else SecurityAlert.Status.OPEN,
                    "scope": SecurityAlert.Scope.EMPLOYEE,
                    "details": (
                        f"Demonstration notification: simulated monitoring event {index:03d}."
                    ),
                    "target_user": target,
                    "ip_address": f"198.51.100.{(index % 200) + 1}",
                },
            )
            counts["alerts"] += int(created)
            preserved["alerts"] += int(not created)

        if conflicts:
            self.stdout.write(self.style.WARNING("Some scale demo records were skipped due to existing conflicts:"))
            for conflict in conflicts[:20]:
                self.stdout.write(f"  - {conflict}")
            if len(conflicts) > 20:
                self.stdout.write(f"  - ... and {len(conflicts) - 20} more")

        self.stdout.write(self.style.SUCCESS("Scale demonstration seed completed."))
        for key in counts:
            self.stdout.write(f"  {key}: {counts[key]} created, {preserved[key]} preserved")
