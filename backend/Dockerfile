FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
# Solo las dependencias de ejecución: pytest, pytest-django y httpx son para las pruebas.
RUN grep -viE '^(pytest|httpx)' requirements.txt > requirements-prod.txt \
    && pip install --no-cache-dir -r requirements-prod.txt

COPY . .
RUN python manage.py collectstatic --noinput

# Koyeb define PORT. Las migraciones se aplican en cada arranque.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec uvicorn config.asgi:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
