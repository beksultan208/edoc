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
RUN pip install --no-cache-dir --default-timeout=300 --retries 5 -r requirements/base.txt

# Копируем исходный код
COPY . .

# Создаём непривилегированного пользователя с домашней директорией
RUN addgroup --system gosdoc && adduser --system --home /home/gosdoc --ingroup gosdoc gosdoc

# Кэш для sentence-transformers / HuggingFace моделей
RUN mkdir -p /home/gosdoc/.cache && chown -R gosdoc:gosdoc /home/gosdoc
RUN chown -R gosdoc:gosdoc /app
USER gosdoc

# Переменные окружения
ENV DJANGO_SETTINGS_MODULE=config.settings.production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HF_HOME=/home/gosdoc/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/gosdoc/.cache/sentence-transformers

EXPOSE 8000

# Entrypoint: собираем статику и запускаем gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && \
     python manage.py collectstatic --noinput && \
     gunicorn config.wsgi:application \
       --bind 0.0.0.0:${PORT} \
       --workers 2 \
       --worker-class gthread \
       --threads 8 \
       --timeout 120 \
       --access-logfile - \
       --error-logfile -"]
