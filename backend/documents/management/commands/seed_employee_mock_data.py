"""Seed safe, idempotent Employee-portal demonstration data."""

import hashlib
import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.management.commands.demo_seed_support import (
    add_demo_seed_arguments,
    ensure_demo_seed_allowed,
    ensure_demo_storage_is_persistent,
)
from accounts.management.commands.seed_admin_mock_data import (
    generate_valid_docx_bytes,
    generate_valid_pdf_bytes,
    generate_valid_pptx_bytes,
    generate_valid_xlsx_bytes,
)
from auditlog.models import AuditEvent
from documents.models import Document, DocumentShare, EmployeeNotification, Folder
from documents.storage import PrivateDocumentStorage


User = get_user_model()
PRIMARY_EMPLOYEE_USERNAME = "employee_demo"


class Command(BaseCommand):
    help = (
        "Seed 50 idempotent Employee demonstration documents with supporting "
        "folders, shares, activity, and notifications."
    )

    def add_arguments(self, parser):
        add_demo_seed_arguments(parser)

    def handle(self, *args, **options):
        ensure_demo_seed_allowed(options)
        ensure_demo_storage_is_persistent(options)

        now = timezone.now()
        storage = PrivateDocumentStorage()
        mock_employee_password = os.environ.get("DOCTRUST_MOCK_EMPLOYEE_PASSWORD")
        counts = {key: 0 for key in ("employees", "folders", "documents", "documents_migrated", "documents_repaired", "shares", "activity", "notifications")}
        existing = {key: 0 for key in counts}

        employee_specs = [
            ("aria.hughes.demo", "Aria", "Hughes", "People Operations"),
            ("ben.moreno.demo", "Ben", "Moreno", "Finance"),
            ("chen.wei.demo", "Chen", "Wei", "Engineering"),
            ("danielle.ross.demo", "Danielle", "Ross", "Product Design"),
            ("ethan.clark.demo", "Ethan", "Clark", "Legal"),
            ("farah.ali.demo", "Farah", "Ali", "Operations"),
            ("gabriel.santos.demo", "Gabriel", "Santos", "Customer Success"),
        ]
        employees = {}
        for username, first, last, _department in employee_specs:
            user = User.objects.filter(username=username).first()
            if user is None:
                user = User.objects.create_user(
                    username=username,
                    email=f"{username}@example.test",
                    password=mock_employee_password or None,
                    first_name=first,
                    last_name=last,
                    role=User.Role.EMPLOYEE,
                    status=User.Status.ACTIVE,
                    is_staff=False,
                    is_superuser=False,
                )
                counts["employees"] += 1
            else:
                existing["employees"] += 1
            employees[username] = user
            if user.role != User.Role.EMPLOYEE:
                self.stdout.write(
                    self.style.WARNING(
                        f"  = Preserved conflicting non-Employee account '{username}'; "
                        "related demo records will be skipped."
                    )
                )
                employees[username] = None

        try:
            primary_employee = User.objects.get(
                username=PRIMARY_EMPLOYEE_USERNAME,
                role=User.Role.EMPLOYEE,
                status=User.Status.ACTIVE,
                is_active=True,
            )
        except User.DoesNotExist as exc:
            raise CommandError(
                f"The development Employee account '{PRIMARY_EMPLOYEE_USERNAME}' is required. "
                "Run seed_dev_users before seeding Employee demonstration documents."
            ) from exc

        folder_specs = [
            ("People Operations", "aria.hughes.demo"),
            ("Financial Planning", "ben.moreno.demo"),
            ("Engineering Delivery", "chen.wei.demo"),
            ("Product Design", "danielle.ross.demo"),
            ("Legal Contracts", "ethan.clark.demo"),
        ]
        folders = {}
        for name, _owner_name in folder_specs:
            folder, created = Folder.objects.get_or_create(owner=primary_employee, name=name)
            counts["folders"] += int(created)
            existing["folders"] += int(not created)
            folders[name] = folder

        document_specs = [
            ("Remote_Work_Policy_2026.pdf", "PDF", "aria.hughes.demo", "People Operations", "Approved hybrid-work policy and equipment guidance."),
            ("Benefits_Enrollment_Guide.docx", "DOCX", "aria.hughes.demo", "People Operations", "Annual benefits enrollment instructions and contacts."),
            ("Workforce_Planning_Q4.xlsx", "XLSX", "aria.hughes.demo", None, "Quarterly hiring and headcount planning workbook."),
            ("FY27_Budget_Proposal.xlsx", "XLSX", "ben.moreno.demo", "Financial Planning", "Department budget proposal with forecast assumptions."),
            ("October_Vendor_Invoices.pdf", "PDF", "ben.moreno.demo", "Financial Planning", "Approved vendor invoices and payment schedule."),
            ("Revenue_Forecast_Brief.pptx", "PPTX", "ben.moreno.demo", None, "Revenue forecast review for the leadership meeting."),
            ("API_Integration_Architecture.pdf", "PDF", "chen.wei.demo", "Engineering Delivery", "Service boundaries, interfaces, and deployment topology."),
            ("Release_Readiness_Checklist.docx", "DOCX", "chen.wei.demo", "Engineering Delivery", "Production release controls and owner checklist."),
            ("Incident_Response_Runbook.docx", "DOCX", "chen.wei.demo", None, "On-call incident response and escalation procedure."),
            ("Design_System_Audit.pdf", "PDF", "danielle.ross.demo", "Product Design", "Accessibility and component-consistency assessment."),
            ("Mobile_Onboarding_Wireframes.pptx", "PPTX", "danielle.ross.demo", "Product Design", "Mobile onboarding flows for usability review."),
            ("Customer_Research_Themes.xlsx", "XLSX", "danielle.ross.demo", None, "Anonymised customer research themes and priorities."),
            ("Master_Service_Agreement.docx", "DOCX", "ethan.clark.demo", "Legal Contracts", "Standard customer service agreement template."),
            ("Data_Processing_Addendum.pdf", "PDF", "ethan.clark.demo", "Legal Contracts", "Data processing obligations for enterprise clients."),
            ("Customer_QBR_Notes.docx", "DOCX", "gabriel.santos.demo", None, "Customer quarterly business-review meeting notes."),
            ("New_Hire_Onboarding_Plan.docx", "DOCX", "aria.hughes.demo", "People Operations", "New-hire onboarding milestones, responsibilities, and completion dates."),
            ("Employee_Handbook_Update.pdf", "PDF", "aria.hughes.demo", "People Operations", "Employee handbook update covering workplace conduct and support resources."),
            ("Learning_Development_Calendar.xlsx", "XLSX", "aria.hughes.demo", "People Operations", "Learning and development sessions scheduled for the coming quarter."),
            ("Performance_Review_Guidance.pptx", "PPTX", "aria.hughes.demo", None, "Manager guidance for the annual performance review cycle."),
            ("Compensation_Benchmark_Summary.pdf", "PDF", "aria.hughes.demo", None, "Compensation benchmark summary prepared for people-operations planning."),
            ("Cash_Flow_Analysis.xlsx", "XLSX", "ben.moreno.demo", "Financial Planning", "Cash-flow analysis with operating and investment planning assumptions."),
            ("Procurement_Policy.docx", "DOCX", "ben.moreno.demo", "Financial Planning", "Procurement policy covering approvals, purchasing limits, and records."),
            ("Quarterly_Finance_Review.pptx", "PPTX", "ben.moreno.demo", "Financial Planning", "Quarterly finance review prepared for department leaders."),
            ("Travel_Expense_Guidelines.pdf", "PDF", "ben.moreno.demo", None, "Travel and expense reimbursement guidance for employees."),
            ("Capital_Investment_Register.xlsx", "XLSX", "ben.moreno.demo", None, "Capital investment register and forecasted approval dates."),
            ("Platform_Roadmap.pptx", "PPTX", "chen.wei.demo", "Engineering Delivery", "Engineering platform roadmap and delivery milestones."),
            ("Database_Migration_Plan.docx", "DOCX", "chen.wei.demo", "Engineering Delivery", "Database migration sequence, validation criteria, and rollback plan."),
            ("Service_Level_Objectives.pdf", "PDF", "chen.wei.demo", "Engineering Delivery", "Service-level objectives and error-budget operating guidance."),
            ("Dependency_Inventory.xlsx", "XLSX", "chen.wei.demo", None, "Third-party dependency inventory and ownership assignments."),
            ("Secure_Coding_Standards.docx", "DOCX", "chen.wei.demo", None, "Secure coding standards for application development and review."),
            ("Accessibility_Review_Checklist.docx", "DOCX", "danielle.ross.demo", "Product Design", "Accessibility review checklist for product-design handoffs."),
            ("Brand_Refresh_Overview.pptx", "PPTX", "danielle.ross.demo", "Product Design", "Brand refresh overview and design-system adoption plan."),
            ("Usability_Testing_Results.pdf", "PDF", "danielle.ross.demo", "Product Design", "Usability testing results, observations, and prioritized recommendations."),
            ("Content_Inventory.xlsx", "XLSX", "danielle.ross.demo", None, "Content inventory for the customer onboarding experience."),
            ("Design_Critique_Notes.docx", "DOCX", "danielle.ross.demo", None, "Design critique notes with agreed actions and owners."),
            ("Contract_Approval_Playbook.pdf", "PDF", "ethan.clark.demo", "Legal Contracts", "Contract approval playbook for legal review and business sign-off."),
            ("NDA_Template.docx", "DOCX", "ethan.clark.demo", "Legal Contracts", "Standard non-disclosure agreement template for prospective partners."),
            ("Regulatory_Change_Tracker.xlsx", "XLSX", "ethan.clark.demo", "Legal Contracts", "Regulatory change tracker with responsible stakeholders and target dates."),
            ("Privacy_Training_Deck.pptx", "PPTX", "ethan.clark.demo", None, "Privacy awareness training for all employees."),
            ("Contract_Renewal_Schedule.xlsx", "XLSX", "ethan.clark.demo", None, "Contract renewal schedule and advance-notice requirements."),
            ("Facilities_Inspection_Checklist.docx", "DOCX", "farah.ali.demo", None, "Facilities inspection checklist for office operations."),
            ("Business_Continuity_Plan.pdf", "PDF", "farah.ali.demo", None, "Business continuity plan for critical operational services."),
            ("Operations_KPI_Dashboard.xlsx", "XLSX", "farah.ali.demo", None, "Operations KPI inputs for weekly performance review."),
            ("Vendor_Management_Guide.pdf", "PDF", "farah.ali.demo", None, "Vendor management guidance covering due diligence and service reviews."),
            ("Office_Safety_Briefing.pptx", "PPTX", "farah.ali.demo", None, "Office safety briefing for facilities and workplace operations."),
            ("Customer_Success_Playbook.docx", "DOCX", "gabriel.santos.demo", None, "Customer-success engagement playbook and escalation guidance."),
            ("Account_Health_Scorecard.xlsx", "XLSX", "gabriel.santos.demo", None, "Customer account health scorecard and follow-up priorities."),
            ("Executive_Business_Review.pptx", "PPTX", "gabriel.santos.demo", None, "Executive business-review presentation for key customer accounts."),
            ("Customer_Escalation_Procedure.pdf", "PDF", "gabriel.santos.demo", None, "Customer escalation procedure and response ownership matrix."),
            ("Renewal_Conversation_Guide.docx", "DOCX", "gabriel.santos.demo", None, "Renewal conversation guide for customer-success managers."),
        ]
        if len(document_specs) != 50:
            raise CommandError(
                f"Employee demonstration document seed must define exactly 50 documents; found {len(document_specs)}."
            )

        documents = {}
        generators = {
            "PDF": generate_valid_pdf_bytes,
            "DOCX": generate_valid_docx_bytes,
            "XLSX": generate_valid_xlsx_bytes,
            "PPTX": generate_valid_pptx_bytes,
        }
        for name, file_type, owner_name, folder_name, summary in document_specs:
            legacy_owner = employees.get(owner_name) or primary_employee
            description = f"Demonstration data: {summary}"
            # A previous version of this command distributed documents across
            # seed-only employees.  Match only this command's demonstrably
            # marked records, then consolidate them into the actual local
            # Employee demo account used by the portal.
            document = Document.objects.filter(
                owner__in=[primary_employee, legacy_owner],
                name=name,
                description=description,
            ).first()
            if document is None:
                content = generators[file_type](name, primary_employee.get_full_name() or primary_employee.username)
                key = PrivateDocumentStorage.generate_storage_key()
                storage.save_stream(content, key)
                try:
                    with transaction.atomic():
                        document = Document.objects.create(
                            owner=primary_employee,
                            folder=folders.get(folder_name),
                            name=name,
                            original_filename=name,
                            description=description,
                            file_type=file_type,
                            size=len(content),
                            sha256=hashlib.sha256(content).hexdigest(),
                            storage_key=key,
                        )
                except Exception:
                    try:
                        storage.delete(key)
                    except Exception:
                        pass
                    raise
                counts["documents"] += 1
            else:
                existing["documents"] += 1
                if document.owner_id != primary_employee.id or document.folder_id != getattr(folders.get(folder_name), "id", None):
                    conflict = Document.objects.filter(
                        owner=primary_employee,
                        name__iexact=name,
                        status__in=[Document.Status.ACTIVE, Document.Status.ARCHIVED],
                    ).exclude(pk=document.pk).exists()
                    if conflict:
                        raise CommandError(
                            f"Cannot safely move demonstration document '{name}': the target account already has an active document with that name."
                        )
                    document.owner = primary_employee
                    document.folder = folders.get(folder_name)
                    document.save(update_fields=["owner", "folder", "updated_at"])
                    counts["documents_migrated"] += 1
                if not storage.exists(document.storage_key):
                    storage.save_stream(
                        generators[file_type](name, primary_employee.get_full_name() or primary_employee.username),
                        document.storage_key,
                    )
                    counts["documents_repaired"] += 1
            documents[name] = document

        share_specs = [
            ("Remote_Work_Policy_2026.pdf", "ben.moreno.demo", DocumentShare.Permission.VIEW),
            ("Benefits_Enrollment_Guide.docx", "gabriel.santos.demo", DocumentShare.Permission.VIEW),
            ("FY27_Budget_Proposal.xlsx", "aria.hughes.demo", DocumentShare.Permission.DOWNLOAD),
            ("October_Vendor_Invoices.pdf", "farah.ali.demo", DocumentShare.Permission.VIEW),
            ("API_Integration_Architecture.pdf", "farah.ali.demo", DocumentShare.Permission.EDIT),
            ("Release_Readiness_Checklist.docx", "gabriel.santos.demo", DocumentShare.Permission.DOWNLOAD),
            ("Design_System_Audit.pdf", "chen.wei.demo", DocumentShare.Permission.EDIT),
            ("Mobile_Onboarding_Wireframes.pptx", "gabriel.santos.demo", DocumentShare.Permission.VIEW),
            ("Master_Service_Agreement.docx", "ben.moreno.demo", DocumentShare.Permission.DOWNLOAD),
            ("Data_Processing_Addendum.pdf", "aria.hughes.demo", DocumentShare.Permission.VIEW),
        ]
        for doc_name, recipient_name, permission in share_specs:
            recipient = employees.get(recipient_name)
            if recipient is None:
                continue
            _share, created = DocumentShare.objects.get_or_create(
                document=documents[doc_name], recipient=recipient,
                defaults={"permission": permission, "expires_at": now + timedelta(days=90)},
            )
            counts["shares"] += int(created)
            existing["shares"] += int(not created)

        activity_specs = [
            ("aria.hughes.demo", AuditEvent.Action.DOCUMENT_UPLOAD, "Remote_Work_Policy_2026.pdf", "upload-policy"),
            ("ben.moreno.demo", AuditEvent.Action.DOCUMENT_UPLOAD, "FY27_Budget_Proposal.xlsx", "upload-budget"),
            ("chen.wei.demo", AuditEvent.Action.DOCUMENT_SHARE, "API_Integration_Architecture.pdf", "share-architecture"),
            ("danielle.ross.demo", AuditEvent.Action.DOCUMENT_UPDATE, "Design_System_Audit.pdf", "update-design-audit"),
            ("ethan.clark.demo", AuditEvent.Action.DOCUMENT_DOWNLOAD, "Master_Service_Agreement.docx", "download-msa"),
            ("farah.ali.demo", AuditEvent.Action.LOGIN_SUCCESS, None, "login-farah"),
            ("gabriel.santos.demo", AuditEvent.Action.DOCUMENT_VIEW, "Customer_QBR_Notes.docx", "view-qbr"),
            ("chen.wei.demo", AuditEvent.Action.DOCUMENT_ARCHIVE, "Incident_Response_Runbook.docx", "archive-runbook"),
        ]
        for actor_name, action, document_name, marker in activity_specs:
            actor = employees.get(actor_name)
            if actor is None:
                continue
            if AuditEvent.objects.filter(metadata__notes=f"employee-seed:{marker}").exists():
                existing["activity"] += 1
                continue
            target = documents.get(document_name)
            AuditEvent.objects.create(
                actor=actor,
                action=action,
                target_type="documents.document" if target else "accounts.user",
                target_id=str(target.id if target else actor.id),
                ip_address="192.0.2.10",
                metadata={"notes": f"employee-seed:{marker}", "status": "demonstration"},
            )
            counts["activity"] += 1

        notification_specs = [
            ("ben.moreno.demo", "Remote_Work_Policy_2026.pdf", "A demonstration copy of Remote Work Policy 2026 was shared with you."),
            ("farah.ali.demo", "API_Integration_Architecture.pdf", "You have edit access to the API Integration Architecture demonstration document."),
            ("gabriel.santos.demo", "Release_Readiness_Checklist.docx", "Release Readiness Checklist is available for download."),
            ("chen.wei.demo", "Design_System_Audit.pdf", "Design System Audit was shared with you for review."),
            ("aria.hughes.demo", "Data_Processing_Addendum.pdf", "Data Processing Addendum was shared with you for review."),
        ]
        for index, (recipient_name, document_name, message) in enumerate(notification_specs, start=1):
            recipient = employees.get(recipient_name)
            if recipient is None:
                continue
            _notification, created = EmployeeNotification.objects.get_or_create(
                event_key=f"employee-seed:notification:{index}",
                defaults={"recipient": recipient, "document": documents[document_name], "message": message},
            )
            counts["notifications"] += int(created)
            existing["notifications"] += int(not created)

        self.stdout.write(self.style.SUCCESS("Employee demonstration seed completed."))
        for key in counts:
            self.stdout.write(f"  {key}: {counts[key]} created, {existing[key]} already present")
        demo_document_count = Document.objects.filter(
            owner=primary_employee,
            description__startswith="Demonstration data:",
        ).count()
        self.stdout.write(f"  total records created: {sum(value for key, value in counts.items() if key not in {'documents_migrated', 'documents_repaired'})}")
        self.stdout.write(f"  demonstration documents migrated: {counts['documents_migrated']}")
        self.stdout.write(f"  demonstration document files repaired: {counts['documents_repaired']}")
        self.stdout.write(f"  demonstration documents: {demo_document_count}; target: 50")
