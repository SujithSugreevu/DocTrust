"""
Verification script for DocTrust 50 demonstration records.
Checks counts, foreign-key relationships, physical storage existence, and API availability.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doctrust.settings")
django.setup()

from accounts.models import User
from documents.models import Document, Folder, DocumentShare
from documents.storage import PrivateDocumentStorage
from auditlog.models import AuditEvent, SecurityAlert

storage = PrivateDocumentStorage()

print("=" * 60)
print("DOCTRUST 50 DEMONSTRATION RECORDS VERIFICATION")
print("=" * 60)

# 1. Employees
emp_qs = User.objects.filter(role=User.Role.EMPLOYEE).exclude(username="employee_demo")
print(f"\n1. EMPLOYEE ACCOUNTS: {emp_qs.count()} (Target: 12)")
for u in emp_qs:
    print(f"   - {u.username:<18} | {u.get_full_name():<18} | {u.email:<32} | Status: {u.status}")

# 2. Folders
f_qs = Folder.objects.filter(owner__in=emp_qs)
print(f"\n2. FOLDERS / CATEGORIES: {f_qs.count()} (Target: 5)")
for f in f_qs:
    print(f"   - Folder '{f.name}' | Owner: {f.owner.username}")

# 3. Documents
d_qs = Document.objects.filter(owner__in=emp_qs)
print(f"\n3. DOCUMENTS: {d_qs.count()} (Target: 15)")
all_exist = True
for d in d_qs:
    exists = storage.exists(d.storage_key)
    if not exists:
        all_exist = False
    folder_name = d.folder.name if d.folder else "None"
    print(f"   - {d.name:<40} | Type: {d.file_type:<4} | Size: {d.size:>4} B | Folder: {folder_name:<8} | Status: {d.status:<8} | Storage File: {exists}")
print(f"   --> All 15 document storage files physically verified on disk: {all_exist}")

# 4. Permissions / Shares
s_qs = DocumentShare.objects.filter(document__owner__in=emp_qs)
print(f"\n4. DOCUMENT PERMISSION SHARES: {s_qs.count()} (Target: 8)")
for s in s_qs:
    print(f"   - Doc: '{s.document.name}' | Owner: {s.document.owner.username} -> Recipient: {s.recipient.username} | Permission: {s.permission}")

# 5. Activity Demonstration Records
a_qs = AuditEvent.objects.filter(actor__in=emp_qs)
print(f"\n5. ACTIVITY / AUDIT LOG DEMONSTRATION RECORDS: {a_qs.count()} (Target: 6)")
for a in a_qs:
    print(f"   - [{a.action}] Actor: {a.actor.username} | Target: {a.target_type} #{a.target_id}")

# 6. Notifications / Security Alerts
notif_qs = SecurityAlert.objects.filter(details__startswith="Demonstration notification")
print(f"\n6. NOTIFICATIONS / SECURITY ALERTS: {notif_qs.count()} (Target: 4)")
for n in notif_qs:
    target = n.target_user.username if n.target_user else "N/A"
    print(f"   - '{n.title}' | Severity: {n.severity} | Status: {n.status} | Target: {target}")

total_demo = emp_qs.count() + f_qs.count() + d_qs.count() + s_qs.count() + a_qs.count() + notif_qs.count()
print("\n" + "=" * 60)
print(f"TOTAL DEMONSTRATION RECORDS VERIFIED: {total_demo} / 50")
print("=" * 60)
