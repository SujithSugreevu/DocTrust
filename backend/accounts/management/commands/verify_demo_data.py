"""Read-only verification for the complete persisted DocTrust demo dataset."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from auditlog.models import AuditEvent, SecurityAlert
from documents.models import Document, DocumentShare, EmployeeNotification, Folder
from documents.storage import PrivateDocumentStorage


User = get_user_model()

ADMIN_DEMO_USERS = (
    "sarah.jenkins", "marcus.vance", "elena.rostova", "david.kim",
    "rachel.green", "carlos.mendez", "priya.sharma", "thomas.wright",
    "aaliyah.patel", "lucas.moreau", "jessica.taylor", "nathaniel.brooks",
)
EMPLOYEE_SUPPORT_USERS = (
    "aria.hughes.demo", "ben.moreno.demo", "chen.wei.demo",
    "danielle.ross.demo", "ethan.clark.demo", "farah.ali.demo",
    "gabriel.santos.demo",
)
ADMIN_DEMO_FOLDER_NAMES = ("HR", "Finance", "Projects", "Design", "Legal")
EMPLOYEE_DEMO_FOLDER_NAMES = (
    "People Operations", "Financial Planning", "Engineering Delivery",
    "Product Design", "Legal Contracts",
)


class Command(BaseCommand):
    help = "Read-only verification of persisted DocTrust demonstration records and document files."

    def handle(self, *args, **options):
        admin_users = User.objects.filter(username__in=ADMIN_DEMO_USERS)
        support_users = User.objects.filter(username__in=EMPLOYEE_SUPPORT_USERS)
        employee_demo = User.objects.filter(username="employee_demo").first()

        checks = [
            (
                "primary demo users",
                User.objects.filter(username__in=("admin_demo", "employee_demo")).count(),
                2,
            ),
            ("administrator fixture employees", admin_users.count(), 12),
            ("employee fixture support users", support_users.count(), 7),
        ]
        admin_folders = Folder.objects.filter(
            owner__in=admin_users,
            name__in=ADMIN_DEMO_FOLDER_NAMES,
        )
        admin_documents = Document.objects.filter(owner__in=admin_users)
        checks.extend([
            ("administrator fixture folders", admin_folders.count(), 5),
            ("administrator fixture documents", admin_documents.count(), 15),
            (
                "administrator fixture shares",
                DocumentShare.objects.filter(document__owner__in=admin_users).count(),
                8,
            ),
            (
                "administrator fixture audit records",
                AuditEvent.objects.filter(
                    metadata__notes__startswith="Demonstration audit trail record"
                ).count(),
                6,
            ),
            (
                "demonstration security alerts",
                SecurityAlert.objects.filter(
                    details__startswith="Demonstration notification"
                ).count(),
                4,
            ),
        ])

        scale_users = User.objects.filter(username__startswith="scale_demo_employee_")
        scale_folders = Folder.objects.filter(name__startswith="Scale Demo Folder ")
        scale_documents = Document.objects.filter(
            description__startswith="Scale demonstration record:"
        )
        scale_shares = DocumentShare.objects.filter(
            document__description__startswith="Scale demonstration record:"
        )
        scale_audit = AuditEvent.objects.filter(
            metadata__notes__startswith="scale-demo:audit:"
        )
        scale_notifications = EmployeeNotification.objects.filter(
            event_key__startswith="scale-demo:notification:"
        )
        scale_alerts = SecurityAlert.objects.filter(
            alert_type__startswith="SCALE_DEMO_ALERT_"
        )
        checks.extend([
            ("scale demo employees", scale_users.count(), 30),
            ("scale demo folders", scale_folders.count(), 30),
            ("scale demo documents", scale_documents.count(), 120),
            ("scale demo shares", scale_shares.count(), 80),
            ("scale demo audit records", scale_audit.count(), 120),
            ("scale demo notifications", scale_notifications.count(), 30),
            ("scale demo security alerts", scale_alerts.count(), 10),
        ])

        employee_documents = (
            Document.objects.filter(
                owner=employee_demo,
                description__startswith="Demonstration data:",
            )
            if employee_demo
            else Document.objects.none()
        )
        employee_folders = (
            Folder.objects.filter(
                owner=employee_demo,
                name__in=EMPLOYEE_DEMO_FOLDER_NAMES,
            )
            if employee_demo
            else Folder.objects.none()
        )
        checks.extend([
            ("employee demo folders", employee_folders.count(), 5),
            ("employee demo documents", employee_documents.count(), 50),
            (
                "employee demo shares",
                DocumentShare.objects.filter(document__owner=employee_demo).count()
                if employee_demo else 0,
                10,
            ),
            (
                "employee demo audit records",
                AuditEvent.objects.filter(
                    metadata__notes__startswith="employee-seed:"
                ).count(),
                8,
            ),
            (
                "employee demo notifications",
                EmployeeNotification.objects.filter(
                    event_key__startswith="employee-seed:notification:"
                ).count(),
                5,
            ),
        ])

        storage = PrivateDocumentStorage()
        demo_documents = list(admin_documents) + list(employee_documents) + list(scale_documents)
        missing_files = sum(not storage.exists(document.storage_key) for document in demo_documents)

        relationship_failures = []
        for document in demo_documents:
            if document.folder_id and document.folder.owner_id != document.owner_id:
                relationship_failures.append(
                    f"document {document.name} points to a folder owned by another user"
                )
            try:
                storage_path = storage.get_path(document.storage_key)
                storage_path.relative_to(storage.root_path)
            except Exception as exc:
                relationship_failures.append(
                    f"document {document.name} has an invalid storage path ({type(exc).__name__})"
                )

        demo_shares = DocumentShare.objects.filter(document__in=demo_documents).select_related(
            "document", "recipient"
        )
        for share in demo_shares:
            if share.document.owner_id == share.recipient_id:
                relationship_failures.append(
                    f"share {share.pk} grants a document to its owner"
                )
            if share.recipient.role != User.Role.EMPLOYEE:
                relationship_failures.append(
                    f"share {share.pk} targets a non-employee account"
                )

        demo_audits = AuditEvent.objects.filter(
            Q(metadata__notes__startswith="Demonstration audit trail record")
            | Q(metadata__notes__startswith="employee-seed:")
            | Q(metadata__notes__startswith="scale-demo:audit:")
        ).select_related("actor")
        for event in demo_audits:
            if event.actor_id is None:
                relationship_failures.append(f"audit event {event.pk} has no actor")
            target_type = (event.target_type or "").lower()
            if target_type == "documents.document" and not Document.objects.filter(pk=event.target_id).exists():
                relationship_failures.append(f"audit event {event.pk} targets a missing document")
            if target_type == "accounts.user" and not User.objects.filter(pk=event.target_id).exists():
                relationship_failures.append(f"audit event {event.pk} targets a missing user")

        demo_notifications = EmployeeNotification.objects.filter(
            Q(event_key__startswith="employee-seed:notification:")
            | Q(event_key__startswith="scale-demo:notification:")
        ).select_related("recipient", "document")
        for notification in demo_notifications:
            if notification.document_id and notification.document is None:
                relationship_failures.append(
                    f"notification {notification.pk} targets a missing document"
                )
            if notification.recipient.role != User.Role.EMPLOYEE:
                relationship_failures.append(
                    f"notification {notification.pk} targets a non-employee account"
                )

        demo_alerts = SecurityAlert.objects.filter(
            Q(details__startswith="Demonstration notification")
            | Q(alert_type__startswith="SCALE_DEMO_ALERT_")
        ).select_related("target_user")
        for alert in demo_alerts:
            if alert.target_user_id and alert.target_user is None:
                relationship_failures.append(f"security alert {alert.pk} targets a missing user")

        self.stdout.write("DocTrust demonstration data verification (read-only)")
        failures = []
        for label, actual, expected in checks:
            passed = actual >= expected
            marker = "PASS" if passed else "MISSING"
            self.stdout.write(f"{marker}: {label}: {actual}/{expected}")
            if not passed:
                failures.append(f"{label} ({actual}/{expected})")

        self.stdout.write(
            f"{'PASS' if missing_files == 0 else 'MISSING'}: demo document files present: "
            f"{len(demo_documents) - missing_files}/{len(demo_documents)}"
        )
        if missing_files:
            failures.append(f"demo document files ({missing_files} missing)")
        if relationship_failures:
            failures.extend(relationship_failures[:20])
            if len(relationship_failures) > 20:
                failures.append(f"... and {len(relationship_failures) - 20} more relationship errors")

        demo_record_count = sum(actual for _label, actual, _expected in checks)
        self.stdout.write(f"Demo records counted: {demo_record_count} (target: approximately 500)")
        if demo_record_count < 500:
            failures.append(f"total coordinated demo records ({demo_record_count}/500)")

        if failures:
            raise CommandError("Demo data verification failed: " + "; ".join(failures))
        self.stdout.write(self.style.SUCCESS("All expected demonstration records and files are present."))
