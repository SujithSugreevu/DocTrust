"""
URL configuration for the Permission Audits API.

All endpoints require admin role authentication.
"""

from django.urls import path
from auditlog import views

urlpatterns = [
    # Admin audit events
    path("admin/", views.AdminAuditListView.as_view(), name="audit-admin-list"),
    path("admin/export/", views.AdminAuditExportView.as_view(), name="audit-admin-export"),
    # Employee audit events
    path("employee/", views.EmployeeAuditListView.as_view(), name="audit-employee-list"),
    path("employee/export/", views.EmployeeAuditExportView.as_view(), name="audit-employee-export"),
    # Event detail
    path("events/<int:pk>/", views.AuditEventDetailView.as_view(), name="audit-event-detail"),
    # Filter dropdown data
    path("action-types/", views.ActionTypeListView.as_view(), name="audit-action-types"),
    path("users/", views.AuditUsersListView.as_view(), name="audit-users"),
    # Security alerts & monitoring
    path("security-alerts/", views.SecurityAlertListView.as_view(), name="security-alerts-list"),
    path("security-alerts/<int:pk>/resolve/", views.SecurityAlertResolveView.as_view(), name="security-alerts-resolve"),
    # Dashboard stats, activity summary & document overview
    path("dashboard-stats/", views.DashboardStatsView.as_view(), name="dashboard-stats"),
    path("activity-summary/", views.ActivitySummaryView.as_view(), name="activity-summary"),
    path("documents-overview/", views.AdminDocumentOverviewView.as_view(), name="documents-overview"),
]

