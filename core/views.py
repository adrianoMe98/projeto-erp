from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def healthcheck(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse(
        {
            "status": "ok",
            "database": "ok",
            "environment": settings.ERP_ENVIRONMENT,
            "version": settings.ERP_VERSION,
        }
    )
