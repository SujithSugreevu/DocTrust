import logging
from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from doctrust.startup import format_safe_exception

logger = logging.getLogger(__name__)

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint verifying Django server and PostgreSQL connectivity.
    Returns HTTP 200 when database query succeeds, 503 if unreachable.
    """
    db_connected = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            if result and result[0] == 1:
                db_connected = True
    except Exception as exc:
        logger.error(
            "Health check failed to communicate with PostgreSQL:\n%s",
            format_safe_exception(exc),
        )

    if db_connected:
        return JsonResponse(
            {
                "status": "healthy",
                "database": "connected",
                "engine": "postgresql",
            },
            status=200,
        )

    return JsonResponse(
        {
            "status": "unhealthy",
            "database": "disconnected",
            "error": "database_unavailable",
        },
        status=503,
    )
