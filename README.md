# ГосДок — Облачная платформа документооборота

Дипломный проект. Система электронного документооборота для государственных организаций.

## Технологии

**Backend:** Python 3.12 · Django 5 · Django REST Framework · PostgreSQL 16 · Redis · Celery · AWS S3  
**Frontend:** React 18 · TypeScript · Vite · Tailwind CSS · Zustand · React Query

---

## Структура репозитория

```
edoc/
├── gosdoc-backend/   # Django API
└── gosdoc-frontend/  # React приложение
```

---

## Быстрый старт

### Вариант 1 — Docker (рекомендуется)

Требования: [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/edoc.git
cd edoc

# 2. Настроить переменные окружения
cd gosdoc-backend
cp .env.example .env
# Отредактируйте .env — заполните AWS, Email, OpenAI ключи

# 3. Запустить backend (DB + Redis + Django + Celery)
docker compose up -d

# 4. Запустить frontend
cd ../gosdoc-frontend
npm install
npm run dev
```

Открыть в браузере: **http://localhost:3000**  
Swagger API: **http://localhost:8000/api/schema/swagger-ui/**

---

### Вариант 2 — Без Docker (локальная разработка)

#### Требования
- Python 3.12+
- Node.js 18+
- PostgreSQL 16
- Redis

#### Backend

```bash
cd gosdoc-backend

# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate
# Активировать (macOS/Linux)
source venv/bin/activate

# Установить зависимости
pip install -r requirements/base.txt

# Настроить переменные
cp .env.example .env
# Отредактируйте .env: укажите DATABASE_URL с localhost

# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Запустить сервер
python manage.py runserver
```

В отдельных терминалах:

```bash
# Celery worker
celery -A config worker -l info

# Celery beat (планировщик)
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

#### Frontend

```bash
cd gosdoc-frontend
npm install
npm run dev
```

---

### Вариант 3 — Docker только для сервисов, frontend локально

```bash
cd gosdoc-backend

# Запустить только DB и Redis
docker compose up -d db redis

# Backend локально
source venv/bin/activate
python manage.py runserver

# Frontend локально (другой терминал)
cd ../gosdoc-frontend
npm run dev
```

---

## Настройка переменных окружения

Скопируйте `gosdoc-backend/.env.example` в `gosdoc-backend/.env` и заполните:

| Переменная | Описание |
|---|---|
| `DJANGO_SECRET_KEY` | Случайная строка 50+ символов |
| `AWS_ACCESS_KEY_ID` | AWS IAM ключ (для S3) |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM секрет |
| `AWS_STORAGE_BUCKET_NAME` | Имя S3 бакета |
| `AWS_S3_REGION_NAME` | Регион бакета (напр. `us-east-2`) |
| `EMAIL_HOST_USER` | Gmail адрес |
| `EMAIL_HOST_PASSWORD` | Пароль приложения Gmail |
| `OPENAI_API_KEY` | OpenAI API ключ (для AI-diff) |

### Получение пароля приложения Gmail
1. Включить двухфакторную аутентификацию: [myaccount.google.com](https://myaccount.google.com) → Безопасность
2. Безопасность → **Пароли приложений** → Другое → ввести название → Создать
3. Скопировать 16-значный пароль в `EMAIL_HOST_PASSWORD`

### Настройка AWS S3
1. Создать бакет в [AWS Console](https://console.aws.amazon.com/s3/)
2. IAM → Пользователи → Создать пользователя → Политика `AmazonS3FullAccess`
3. Создать ключи доступа → скопировать в `.env`
4. Настроить CORS на бакете (разрешить `POST`, `GET` с `http://localhost:3000`)

---

## Основные команды

```bash
# Пересобрать Docker образы
docker compose build

# Просмотр логов
docker compose logs -f backend
docker compose logs -f celery

# Остановить всё
docker compose down

# Остановить + удалить данные БД
docker compose down -v

# Применить миграции вручную
docker compose exec backend python manage.py migrate

# Создать суперпользователя
docker compose exec backend python manage.py createsuperuser

# Сборка фронтенда для продакшна
cd gosdoc-frontend
npm run build
```

---

## API документация

После запуска backend:

- **Swagger UI:** http://localhost:8000/api/schema/swagger-ui/
- **ReDoc:** http://localhost:8000/api/schema/redoc/

---

## Функциональность

- Регистрация с подтверждением email (6-значный код)
- JWT аутентификация (access 15 мин, refresh 7 дней)
- Рабочие кабинеты с ролевой моделью (owner, editor, signer, viewer)
- Загрузка документов напрямую в AWS S3 (presigned POST)
- Версионирование документов с AI-анализом изменений (OpenAI)
- Workflow согласования документов по шагам
- Электронные подписи (canvas)
- Комментарии с ответами
- Уведомления в реальном времени
- Ежемесячные отчёты с экспортом PDF/XLSX
- Сброс пароля через email
