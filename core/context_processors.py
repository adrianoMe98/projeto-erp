from django.conf import settings


def runtime_metadata(request):
    return {
        "erp_environment": settings.ERP_ENVIRONMENT,
        "erp_version": settings.ERP_VERSION,
        "pix_enabled": settings.PIX_ENABLED,
    }
