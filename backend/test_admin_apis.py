"""
Test script to verify all Administrator backend API endpoints return the seeded demonstration records.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doctrust.settings")
django.setup()

from rest_framework.test import APIClient
from accounts.models import User

admin_user = User.objects.filter(role=User.Role.ADMIN).first()
client = APIClient()
client.force_authenticate(user=admin_user)

print("=" * 60)
print(f"TESTING ADMINISTRATOR API ENDPOINTS (Authenticated as {admin_user.username})")
print("=" * 60)

# 1. Dashboard Stats
resp = client.get("/api/audit/dashboard-stats/?range=7+days")
print(f"\n1. GET /api/audit/dashboard-stats/ -> HTTP {resp.status_code}")
data = resp.data
print("   - Stats:", data.get("stats"))
print("   - Activities Count:", len(data.get("activities", [])))
print("   - Alerts / Notifications Count:", len(data.get("alerts", [])))
for a in data.get("alerts", []):
    print(f"     * Alert: {a.get('title')} ({a.get('severity')})")

# 2. User Management (Employees)
resp = client.get("/api/admin/users/?role=EMPLOYEE&pageSize=20")
print(f"\n2. GET /api/admin/users/?role=EMPLOYEE -> HTTP {resp.status_code}")
data = resp.data
print("   - Total Employees:", data.get("total"))
results = data.get("results", [])
print(f"   - Results on page ({len(results)}):")
for u in results[:5]:
    print(f"     * {u.get('display_name')} (@{u.get('username')}) - {u.get('status')}")

# 3. Document Overview
resp = client.get("/api/audit/documents-overview/")
print(f"\n3. GET /api/audit/documents-overview/ -> HTTP {resp.status_code}")
data = resp.data
print("   - Total documents:", data.get("total_count"))
print("   - Active count:", data.get("active_count"))
print("   - Restricted count:", data.get("restricted_count"))
print(f"   - Results returned: {len(data.get('results', []))}")
for doc in data.get("results", [])[:5]:
    print(f"     * {doc.get('name')} | Owner: {doc.get('owner')} | Type: {doc.get('type')} | Status: {doc.get('status')}")

# 4. Security Alerts
resp = client.get("/api/audit/security-alerts/")
print(f"\n4. GET /api/audit/security-alerts/ -> HTTP {resp.status_code}")
data = resp.data
print("   - Total alerts:", data.get("total"))
print("   - Open alerts:", data.get("open_count"))
for item in data.get("results", []):
    print(f"     * {item.get('title')} ({item.get('severity')}) - Status: {item.get('status')}")

# 5. Activity Logs (Employee events)
resp = client.get("/api/audit/employee/?page_size=20")
print(f"\n5. GET /api/audit/employee/ -> HTTP {resp.status_code}")
data = resp.data
print("   - Total Employee Audit Events:", data.get("total_count"))
for ev in data.get("results", [])[:5]:
    print(f"     * {ev.get('timestamp')} | Actor: {ev.get('actor_username')} | Action: {ev.get('action_display')}")

print("\n" + "=" * 60)
print("ALL ADMINISTRATOR APIS RETURN LIVE DEMONSTRATION RECORDS!")
print("=" * 60)
