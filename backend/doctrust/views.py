import logging
from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint verifying Django server and PostgreSQL connectivity.
    Returns HTTP 200 when database query succeeds, 503 if unreachable.
    """
    db_connected = False
    error_message = None

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()
            if result and result[0] == 1:
                db_connected = True
    except Exception as exc:
        logger.exception("Health check failed to communicate with PostgreSQL")
        error_message = str(exc)

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
            "error": error_message,
        },
        status=503,
    )
