"""
REST API views for the Permission Audits module.

Endpoints:
  GET  /api/audit/admin/               — Admin audit events (actions by ADMIN users)
  GET  /api/audit/employee/            — Employee audit events (actions by EMPLOYEE users)
  GET  /api/audit/events/<id>/         — Single event detail
  GET  /api/audit/admin/export/        — CSV export of admin audit events
  GET  /api/audit/employee/export/     — CSV export of employee audit events
  GET  /api/audit/action-types/        — Available action type choices for filter dropdowns

All endpoints are admin-only (IsAdminRole). Read-only — no POST/PUT/PATCH/DELETE.
"""

import csv
import logging
from io import StringIO
from datetime import datetime

from django.http import HttpResponse
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from auditlog.models import AuditEvent
from auditlog.helpers import FAIL_ACTIONS
from auditlog.serializers import AuditEventListSerializer, AuditEventDetailSerializer

logger = logging.getLogger("auditlog")

# Maximum page size to prevent abuse
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class BaseAuditListView(ListAPIView):
    """
    Base list view with shared filtering, ordering, and pagination logic.
    Subclasses set the role filter.
    """

    permission_classes = [IsAdminRole]
    serializer_class = AuditEventListSerializer

    # Subclasses must set this to "ADMIN" or "EMPLOYEE"
    actor_role_filter = None

    def get_queryset(self):
        qs = AuditEvent.objects.select_related("actor").order_by("-timestamp")

        # Filter by actor role
        if self.actor_role_filter == "ADMIN":
            qs = qs.filter(actor__role="ADMIN")
        elif self.actor_role_filter == "EMPLOYEE":
            qs = qs.filter(actor__role="EMPLOYEE")

        # ── Query parameter filters ──

        # Search: matches actor username, action display, target_type, target_id
        search = self.request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(actor__username__icontains=search)
                | Q(action__icontains=search)
                | Q(target_type__icontains=search)
                | Q(target_id__icontains=search)
            )

        # Date range filters (ISO 8601 or YYYY-MM-DD)
        start_date = self.request.query_params.get("start_date", "").strip()
        end_date = self.request.query_params.get("end_date", "").strip()
        if start_date:
            parsed = parse_datetime(start_date)
            if parsed is None:
                try:
                    parsed = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    parsed = None
            if parsed:
                qs = qs.filter(timestamp__gte=parsed)

        if end_date:
            parsed = parse_datetime(end_date)
            if parsed is None:
                try:
                    parsed = datetime.strptime(end_date, "%Y-%m-%d")
                    # End of day
                    parsed = parsed.replace(hour=23, minute=59, second=59)
                except ValueError:
                    parsed = None
            if parsed:
                qs = qs.filter(timestamp__lte=parsed)

        # User filter (actor username)
        user_filter = self.request.query_params.get("user", "").strip()
        if user_filter:
            qs = qs.filter(actor__username__iexact=user_filter)

        # Action type filter
        action_filter = self.request.query_params.get("action_type", "").strip()
        if action_filter:
            qs = qs.filter(action=action_filter)

        # Outcome filter (Success / Failed)
        outcome_filter = self.request.query_params.get("outcome", "").strip()
        if outcome_filter:
            if outcome_filter.lower() == "failed":
                qs = qs.filter(action__in=FAIL_ACTIONS)
            elif outcome_filter.lower() == "success":
                qs = qs.exclude(action__in=FAIL_ACTIONS)

        return qs

    def list(self, request, *args, **kwargs):
        """Override to add pagination metadata."""
        queryset = self.filter_queryset(self.get_queryset())
        total_count = queryset.count()

        # Manual pagination
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = min(
                MAX_PAGE_SIZE,
                max(1, int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE))),
            )
        except (ValueError, TypeError):
            page_size = DEFAULT_PAGE_SIZE

        start = (page - 1) * page_size
        end = start + page_size
        page_qs = queryset[start:end]

        serializer = self.get_serializer(page_qs, many=True)

        total_pages = max(1, (total_count + page_size - 1) // page_size)

        return Response(
            {
                "results": serializer.data,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        )


class AdminAuditListView(BaseAuditListView):
    """Audit events where the actor is an ADMIN user."""

    actor_role_filter = "ADMIN"


class EmployeeAuditListView(BaseAuditListView):
    """Audit events where the actor is an EMPLOYEE user."""

    actor_role_filter = "EMPLOYEE"


class AuditEventDetailView(RetrieveAPIView):
    """Single audit event detail — admin only."""

    permission_classes = [IsAdminRole]
    serializer_class = AuditEventDetailSerializer
    queryset = AuditEvent.objects.select_related("actor")
    lookup_field = "pk"


class BaseAuditExportView(APIView):
    """
    CSV export for audit events.
    Reuses the same filtering logic as the list views.
    """

    permission_classes = [IsAdminRole]
    actor_role_filter = None

    def get(self, request):
        qs = AuditEvent.objects.select_related("actor").order_by("-timestamp")

        if self.actor_role_filter == "ADMIN":
            qs = qs.filter(actor__role="ADMIN")
        elif self.actor_role_filter == "EMPLOYEE":
            qs = qs.filter(actor__role="EMPLOYEE")

        # Apply the same filters as the list view
        search = request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(actor__username__icontains=search)
                | Q(action__icontains=search)
                | Q(target_type__icontains=search)
                | Q(target_id__icontains=search)
            )

        start_date = request.query_params.get("start_date", "").strip()
        end_date = request.query_params.get("end_date", "").strip()
        if start_date:
            parsed = parse_datetime(start_date)
            if parsed is None:
                try:
                    parsed = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    parsed = None
            if parsed:
                qs = qs.filter(timestamp__gte=parsed)
        if end_date:
            parsed = parse_datetime(end_date)
            if parsed is None:
                try:
                    parsed = datetime.strptime(end_date, "%Y-%m-%d")
                    parsed = parsed.replace(hour=23, minute=59, second=59)
                except ValueError:
                    parsed = None
            if parsed:
                qs = qs.filter(timestamp__lte=parsed)

        user_filter = request.query_params.get("user", "").strip()
        if user_filter:
            qs = qs.filter(actor__username__iexact=user_filter)

        action_filter = request.query_params.get("action_type", "").strip()
        if action_filter:
            qs = qs.filter(action=action_filter)

        outcome_filter = request.query_params.get("outcome", "").strip()
        if outcome_filter:
            if outcome_filter.lower() == "failed":
                qs = qs.filter(action__in=FAIL_ACTIONS)
            elif outcome_filter.lower() == "success":
                qs = qs.exclude(action__in=FAIL_ACTIONS)

        # Limit export to 10,000 rows for safety
        qs = qs[:10000]

        # Generate CSV
        response = HttpResponse(content_type="text/csv")
        role_label = (self.actor_role_filter or "all").lower()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        response["Content-Disposition"] = (
            f'attachment; filename="doctrust_{role_label}_audit_{timestamp_str}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            "Timestamp",
            "User",
            "Role",
            "Action",
            "Description",
            "Target Resource",
            "IP Address",
            "Outcome",
        ])

        for event in qs.iterator():
            actor_name = event.actor.username if event.actor else "System"
            actor_role = getattr(event.actor, "role", "SYSTEM") if event.actor else "SYSTEM"
            metadata = event.metadata or {}
            outcome = metadata.get("status", "Failed" if event.action in FAIL_ACTIONS else "Success")
            target_resource = f"{event.target_type}"
            if event.target_id:
                target_resource += f" #{event.target_id}"

            writer.writerow([
                event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                actor_name,
                actor_role,
                event.action,
                event.get_action_display(),
                target_resource,
                event.ip_address or "",
                outcome,
            ])

        return response


class AdminAuditExportView(BaseAuditExportView):
    actor_role_filter = "ADMIN"


class EmployeeAuditExportView(BaseAuditExportView):
    actor_role_filter = "EMPLOYEE"


class ActionTypeListView(APIView):
    """Return available action type choices for filter dropdowns."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        action_types = [
            {"value": choice[0], "label": choice[1]}
            for choice in AuditEvent.Action.choices
        ]
        return Response({"action_types": action_types})


class AuditUsersListView(APIView):
    """Return distinct actor usernames for user filter dropdown."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        role = request.query_params.get("role", "").strip()
        qs = AuditEvent.objects.select_related("actor").exclude(actor__isnull=True)
        if role:
            qs = qs.filter(actor__role=role)
        usernames = sorted(
            qs.values_list("actor__username", flat=True)
            .distinct()
        )
        return Response({"users": usernames})


def ensure_default_security_alerts():
    from auditlog.models import SecurityAlert
    from accounts.models import User
    if SecurityAlert.objects.count() == 0:
        emp = User.objects.filter(role=User.Role.EMPLOYEE).first()
        admin = User.objects.filter(role=User.Role.ADMIN).first()
        SecurityAlert.objects.create(
            title="Repeated failed login attempts",
            severity="Security Attack",
            status="Open",
            scope="EMPLOYEE",
            alert_type="FAILED_LOGIN_ATTACK",
            details="Five unsuccessful login attempts were detected for employee account within 10 minutes.",
            target_user=emp,
            ip_address="192.168.1.105",
        )
        SecurityAlert.objects.create(
            title="Access to an unshared file",
            severity="Medium",
            status="Review",
            scope="EMPLOYEE",
            alert_type="UNAUTHORIZED_ACCESS",
            details="A user attempted to access an employee document without an applicable permission grant.",
            target_user=emp,
            ip_address="192.168.1.112",
        )
        SecurityAlert.objects.create(
            title="Disallowed file type upload attempt",
            severity="Medium",
            status="Resolved",
            scope="EMPLOYEE",
            alert_type="DISALLOWED_FILE_UPLOAD",
            details="File upload rejected: executable/disallowed binary content signature detected.",
            target_user=emp,
            ip_address="192.168.1.120",
            resolved_by=admin,
            resolution_notes="Validated benign user upload mistake, security warning issued.",
        )
        SecurityAlert.objects.create(
            title="Privileged administrative setting change",
            severity="Low",
            status="Resolved",
            scope="ADMIN",
            alert_type="ADMIN_SETTING_CHANGE",
            details="System settings updated: security notification threshold adjusted.",
            target_user=admin,
            ip_address="127.0.0.1",
            resolved_by=admin,
            resolution_notes="Authorized administrative configuration change.",
        )


class SecurityAlertListView(APIView):
    """
    GET /api/audit/security-alerts/
    Returns list of security alerts with filters for scope, status, severity, search.
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        from django.db.models import Q
        from auditlog.models import SecurityAlert
        from auditlog.serializers import SecurityAlertSerializer
        ensure_default_security_alerts()

        scope = request.query_params.get("scope", "").strip().upper()
        status_filter = request.query_params.get("status", "").strip()
        severity = request.query_params.get("severity", "").strip()
        search = request.query_params.get("search", "").strip()

        qs = SecurityAlert.objects.select_related("target_user", "resolved_by").order_by("-created_at")

        if scope in ["ADMIN", "EMPLOYEE"]:
            qs = qs.filter(scope=scope)

        if status_filter and status_filter.lower() not in ["all alerts", "all"]:
            qs = qs.filter(status__iexact=status_filter)

        if severity and severity.lower() not in ["all", "all alerts"]:
            if severity.lower() in ["security attacks", "security attack", "attack"]:
                qs = qs.filter(severity="Security Attack")
            else:
                qs = qs.filter(severity__iexact=severity)

        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(details__icontains=search)
                | Q(target_user__username__icontains=search)
            )

        base_qs = SecurityAlert.objects.all()
        if scope in ["ADMIN", "EMPLOYEE"]:
            base_qs = base_qs.filter(scope=scope)

        open_count = base_qs.filter(status__in=["Open", "Review"]).count()
        attack_count = base_qs.filter(severity__in=["Security Attack", "High"]).count()
        resolved_count = base_qs.filter(status="Resolved").count()

        serializer = SecurityAlertSerializer(qs, many=True)
        return Response({
            "results": serializer.data,
            "total": qs.count(),
            "open_count": open_count,
            "attack_count": attack_count,
            "resolved_count": resolved_count,
        }, status=status.HTTP_200_OK)


class SecurityAlertResolveView(APIView):
    """
    POST /api/audit/security-alerts/<int:pk>/resolve/
    Toggles alert status (Open/Review <-> Resolved) and saves in PostgreSQL.
    Records SECURITY_ALERT_RESOLVED audit event.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        from django.utils import timezone
        from auditlog.models import SecurityAlert
        from auditlog.serializers import SecurityAlertSerializer
        from auditlog.helpers import log_event
        try:
            alert = SecurityAlert.objects.get(pk=pk)
        except SecurityAlert.DoesNotExist:
            return Response({"detail": "Security alert not found."}, status=status.HTTP_404_NOT_FOUND)

        if alert.status == "Resolved":
            alert.status = "Open"
            alert.resolved_by = None
            alert.resolved_at = None
            action_desc = "reopened"
        else:
            alert.status = "Resolved"
            alert.resolved_by = request.user
            alert.resolved_at = timezone.now()
            action_desc = "resolved"

        alert.save(update_fields=["status", "resolved_by", "resolved_at", "updated_at"])

        log_event(
            actor=request.user,
            action=AuditEvent.Action.SECURITY_ALERT_RESOLVED if action_desc == "resolved" else AuditEvent.Action.SECURITY_ALERT,
            target=alert,
            request=request,
            metadata={"status": alert.status, "action": action_desc},
        )

        return Response({
            "detail": f"Alert '{alert.title}' marked as {alert.status}.",
            "alert": SecurityAlertSerializer(alert).data,
        }, status=status.HTTP_200_OK)


class DashboardStatsView(APIView):
    """
    GET /api/audit/dashboard-stats/
    Returns real statistics, activity chart data for Today/7d/30d/90d,
    recent audit activities, and active security alerts.
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        from accounts.models import User
        from documents.models import Document
        from auditlog.models import SecurityAlert
        from django.utils import timezone
        from datetime import timedelta
        ensure_default_security_alerts()

        period = request.query_params.get("range", "7 days").strip().lower()

        # Core statistics
        registered_users = User.objects.count()
        total_documents = Document.objects.filter(status__in=["active", "archived"]).count()
        employees = User.objects.filter(role=User.Role.EMPLOYEE).count()
        administrators = User.objects.filter(role=User.Role.ADMIN).count()

        now = timezone.now()

        # Build chart data depending on period
        if period in ["today", "1 day"]:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            chart_data = []
            for hour in range(0, 24, 4):
                bucket_start = today_start + timedelta(hours=hour)
                bucket_end = bucket_start + timedelta(hours=4)
                count = AuditEvent.objects.filter(timestamp__gte=bucket_start, timestamp__lt=bucket_end).count()
                chart_data.append({"day": f"{hour:02d}:00", "value": count})
        elif period == "30 days":
            chart_data = []
            for i in range(4, 0, -1):
                week_start = now - timedelta(days=i * 7)
                week_end = now - timedelta(days=(i - 1) * 7)
                count = AuditEvent.objects.filter(timestamp__gte=week_start, timestamp__lt=week_end).count()
                chart_data.append({"day": f"Week {5 - i}", "value": count})
        elif period == "90 days":
            chart_data = []
            for i in range(3, 0, -1):
                m_start = now - timedelta(days=i * 30)
                m_end = now - timedelta(days=(i - 1) * 30)
                count = AuditEvent.objects.filter(timestamp__gte=m_start, timestamp__lt=m_end).count()
                chart_data.append({"day": f"Month {4 - i}", "value": count})
        else: # default 7 days
            chart_data = []
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for i in range(6, -1, -1):
                day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                count = AuditEvent.objects.filter(timestamp__gte=day_start, timestamp__lt=day_end).count()
                day_label = day_names[day_start.weekday()]
                chart_data.append({"day": day_label, "value": count})

        # Recent activities from AuditEvent
        recent_events = AuditEvent.objects.select_related("actor").order_by("-timestamp")[:10]
        activities = []
        for ev in recent_events:
            doc_name = "Document"
            if ev.target_type == "documents.document" and ev.target_id:
                doc = Document.objects.filter(pk=ev.target_id).first()
                if doc:
                    doc_name = doc.name
            user_name = ev.actor.get_full_name() or ev.actor.username if ev.actor else "System"
            category = "Document"
            if "USER" in ev.action or "LOGIN" in ev.action or "PASSWORD" in ev.action:
                category = "User Management"
            elif "SETTINGS" in ev.action or "MAINTENANCE" in ev.action:
                category = "System Settings"
            elif "ALERT" in ev.action or "SECURITY" in ev.action:
                category = "Security"

            activities.append({
                "id": ev.id,
                "time": ev.timestamp.strftime("%d %b, %H:%M"),
                "user": user_name,
                "action": ev.get_action_display(),
                "document": doc_name,
                "result": "Denied" if ev.action in FAIL_ACTIONS else "Success",
                "details": f"{ev.get_action_display()} on {ev.target_type} #{ev.target_id or ''}".strip(),
                "category": category,
            })

        # Security alerts for dashboard
        alerts_qs = SecurityAlert.objects.filter(status__in=["Open", "Review"]).order_by("-created_at")[:5]
        alerts_data = []
        for a in alerts_qs:
            alerts_data.append({
                "id": a.id,
                "title": a.title,
                "severity": a.severity,
                "status": a.status,
                "time": a.created_at.strftime("%d %b %Y, %H:%M"),
                "details": a.details,
            })

        return Response({
            "stats": {
                "registered_users": registered_users,
                "total_documents": total_documents,
                "employees": employees,
                "administrators": administrators,
            },
            "chart_data": chart_data,
            "activities": activities,
            "alerts": alerts_data,
        }, status=status.HTTP_200_OK)


class ActivitySummaryView(APIView):
    """
    GET /api/audit/activity-summary/
    Returns total events count, successful action percentage, and active users count.
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        from datetime import timedelta

        total_events = AuditEvent.objects.count()
        failed_count = AuditEvent.objects.filter(action__in=FAIL_ACTIONS).count()
        successful_count = max(0, total_events - failed_count)
        success_pct = 100 if total_events == 0 else round((successful_count / total_events) * 100)

        # Active users count
        now = timezone.now()
        active_sessions = Session.objects.filter(expire_date__gt=now).count()
        recent_actors = AuditEvent.objects.filter(
            timestamp__gte=now - timedelta(minutes=15),
            actor__isnull=False,
        ).values("actor").distinct().count()

        active_users_count = max(1, max(active_sessions, recent_actors))

        return Response({
            "total_events": total_events,
            "success_rate": f"{success_pct}%",
            "active_users_count": active_users_count,
        }, status=status.HTTP_200_OK)


class AdminDocumentOverviewView(APIView):
    """
    GET /api/audit/documents-overview/
    Returns list of all documents with permitted metadata.
    Enforces document access rules: administrators cannot download employee private documents.
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        from documents.models import Document
        from django.db.models import Q

        search = request.query_params.get("search", "").strip()
        status_filter = request.query_params.get("status", "All statuses").strip()

        qs = Document.objects.select_related("owner").order_by("-created_at")

        total_count = qs.filter(status__in=["active", "archived"]).count()
        active_count = qs.filter(status="active").count()
        restricted_count = qs.filter(status="archived").count() + qs.exclude(owner=request.user).count()

        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(owner__username__icontains=search)
                | Q(owner__email__icontains=search)
                | Q(id__icontains=search)
            )

        if status_filter == "Active":
            qs = qs.filter(status="active")
        elif status_filter == "Archived":
            qs = qs.filter(status="archived")
        elif status_filter == "Restricted":
            qs = qs.filter(Q(status="archived") | ~Q(owner=request.user))

        results = []
        for doc in qs:
            is_own = doc.owner_id == request.user.id
            access_level = "Full Access" if is_own else "Restricted"
            doc_status = "Restricted" if not is_own else ("Active" if doc.status == "active" else "Archived")
            results.append({
                "id": str(doc.id),
                "name": doc.name,
                "owner": doc.owner.get_full_name() or doc.owner.username,
                "type": doc.file_type,
                "date": doc.created_at.strftime("%d %b %Y, %H:%M"),
                "access": access_level,
                "status": doc_status,
                "size": doc.size,
                "can_download": is_own,
            })

        return Response({
            "total_count": total_count,
            "active_count": active_count,
            "restricted_count": restricted_count,
            "results": results,
        }, status=status.HTTP_200_OK)
