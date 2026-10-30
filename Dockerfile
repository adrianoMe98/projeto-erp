FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system erp \
    && useradd --system --gid erp --create-home erp

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl

WORKDIR /app
COPY --chown=erp:erp . /app
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/erp-entrypoint
RUN mkdir -p /app/var/static /app/var/media \
    && chown -R erp:erp /app/var \
    && chmod 755 /app \
    && chmod +x /app/docker/entrypoint.sh

USER erp
EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/erp-entrypoint"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
