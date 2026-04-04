# ============================================================
# ГосДок — Dockerfile для Django backend
# ============================================================

FROM python:3.12-slim

# Системные зависимости (для psycopg2, WeasyPrint, PyMuPDF)
# Примечание: libgdk-pixbuf2.0-0 переименован в Debian Trixie → libgdk-pixbuf-2.0-0
# PyMuPDF 1.24+ везёт MuPDF бинарники сам, libmupdf-dev не нужен
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем зависимости отдельно (кэш Docker)
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/base.txt

# Копируем исходный код
COPY . .

# Создаём непривилегированного пользователя
RUN addgroup --system gosdoc && adduser --system --ingroup gosdoc gosdoc
RUN chown -R gosdoc:gosdoc /app
USER gosdoc

# Переменные окружения
ENV DJANGO_SETTINGS_MODULE=config.settings.production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

# Entrypoint: собираем статику и запускаем gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && \
     python manage.py collectstatic --noinput && \
     gunicorn config.wsgi:application \
       --bind 0.0.0.0:${PORT} \
       --workers 4 \
       --worker-class sync \
       --timeout 120 \
       --access-logfile - \
       --error-logfile -"]
