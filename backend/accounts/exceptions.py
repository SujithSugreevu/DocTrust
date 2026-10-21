from rest_framework import exceptions, status
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom exception handler to ensure unauthenticated requests return 401 Unauthorized
    rather than 403 Forbidden, allowing SPA clients to distinguish unauthenticated
    from permission-denied responses.
    """
    response = exception_handler(exc, context)

    if response is not None and isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        response.status_code = status.HTTP_401_UNAUTHORIZED

    return response
