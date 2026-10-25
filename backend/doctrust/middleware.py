"""Request middleware for safe production configuration validation."""

import logging

from django.conf import settings
from django.http import JsonResponse


logger = logging.getLogger("doctrust.configuration")


class ProductionConfigurationMiddleware:
    """Reject requests when required production settings are not configured."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        errors = tuple(getattr(settings, "PRODUCTION_CONFIGURATION_ERRORS", ()))
        if not settings.DEBUG and errors:
            logger.critical(
                "Production configuration validation failed: %s",
                "; ".join(errors),
            )
            return JsonResponse(
                {
                    "detail": "Server configuration is incomplete.",
                    "error": "production_configuration_invalid",
                    "configuration_errors": list(errors),
                },
                status=500,
            )

        return self.get_response(request)
