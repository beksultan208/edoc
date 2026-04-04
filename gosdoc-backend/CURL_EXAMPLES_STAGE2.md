# ГосДок — Примеры curl-запросов (Этап 2)

Base URL: `http://localhost:8000`

```bash
# Сохраните токен после логина:
ACCESS_TOKEN="eyJ0eXAiOiJKV1Q..."
```

---

## 1. Создание организации (POST /api/v1/organizations/)

```bash
curl -X POST http://localhost:8000/api/v1/organizations/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Министерство цифрового развития",
    "type": "corporate",
    "inn": "123456789012",
    "address": "г. Алматы, ул. Примерная, 1"
  }'
```

**Ответ (201):**
```json
{
  "id": "org-uuid",
  "name": "Министерство цифрового развития",
  "type": "corporate",
  "inn": "123456789012",
  "owner": "user-uuid",
  "created_at": "2026-03-29T10:00:00Z"
}
```

---

## 2. Создание рабочего кабинета (POST /api/v1/workspaces/)

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Согласование приказа №42",
    "type": "individual",
    "organization": "org-uuid",
    "description": "Согласование внутреннего приказа об отпусках",
    "deadline": "2026-04-30"
  }'
```

**Ответ (201):**
```json
{
  "id": "workspace-uuid",
  "title": "Согласование приказа №42",
  "type": "individual",
  "status": "active",
  "members_count": 1
}
```

---

## 3. Добавление участника в кабинет (POST /api/v1/workspaces/{id}/members/)

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/workspace-uuid/members/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-2-uuid",
    "role": "editor",
    "step_order": 1
  }'
```

---

## 4. Двухэтапная загрузка документа

### Шаг 1: Получить presigned POST URL

```bash
curl -X POST http://localhost:8000/api/v1/documents/request-upload/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace": "workspace-uuid",
    "title": "Приказ №42 об отпусках",
    "file_name": "prikaz_42.pdf",
    "file_size": 1048576
  }'
```

**Ответ (200):**
```json
{
  "upload_url": "https://gosdoc-documents.s3.amazonaws.com/",
  "upload_fields": {
    "key": "documents/workspace-uuid/abc123/prikaz_42.pdf",
    "AWSAccessKeyId": "AKIA...",
    "policy": "eyJ...",
    "signature": "xxx",
    "Content-Type": "application/pdf",
    "x-amz-server-side-encryption": "AES256"
  },
  "storage_key": "documents/workspace-uuid/abc123/prikaz_42.pdf",
  "expires_in": 3600
}
```

### Шаг 2: Загрузить файл напрямую в S3

```bash
# Используйте данные из ответа шага 1:
UPLOAD_URL="https://gosdoc-documents.s3.amazonaws.com/"
STORAGE_KEY="documents/workspace-uuid/abc123/prikaz_42.pdf"

curl -X POST "$UPLOAD_URL" \
  -F "key=$STORAGE_KEY" \
  -F "AWSAccessKeyId=AKIA..." \
  -F "policy=eyJ..." \
  -F "signature=xxx" \
  -F "Content-Type=application/pdf" \
  -F "x-amz-server-side-encryption=AES256" \
  -F "file=@/path/to/prikaz_42.pdf"
```

### Шаг 3: Подтвердить загрузку (создать запись в БД)

```bash
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace": "workspace-uuid",
    "title": "Приказ №42 об отпусках",
    "storage_key": "documents/workspace-uuid/abc123/prikaz_42.pdf",
    "file_name": "prikaz_42.pdf"
  }'
```

**Ответ (201):**
```json
{
  "id": "doc-uuid",
  "title": "Приказ №42 об отпусках",
  "file_type": "pdf",
  "status": "draft",
  "current_version_number": 1,
  "created_at": "2026-03-29T10:15:00Z"
}
```

---

## 5. Получить presigned URL для скачивания (GET /api/v1/documents/{id}/download/)

```bash
curl -X GET http://localhost:8000/api/v1/documents/doc-uuid/download/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Ответ (200):**
```json
{
  "download_url": "https://gosdoc-documents.s3.amazonaws.com/documents/...?X-Amz-Signature=...",
  "expires_in": 3600,
  "file_name": "Приказ №42 об отпусках.pdf",
  "file_type": "pdf"
}
```

---

## 6. Запустить workflow (POST /api/v1/documents/{id}/workflow/start/)

```bash
curl -X POST http://localhost:8000/api/v1/documents/doc-uuid/workflow/start/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Ответ (200):**
```json
{
  "detail": "Workflow запущен.",
  "status": "review",
  "tasks_created": 3
}
```

---

## 7. Загрузить новую версию документа

### Шаг 1: Получить presigned URL для новой версии

```bash
curl -X POST http://localhost:8000/api/v1/documents/doc-uuid/versions/request-upload/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "prikaz_42_v2.pdf",
    "file_size": 1200000
  }'
```

### Шаг 2: Загрузить в S3 (аналогично п. 4, шаг 2)

### Шаг 3: Подтвердить

```bash
curl -X POST http://localhost:8000/api/v1/documents/doc-uuid/versions/confirm/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "storage_key": "documents/workspace-uuid/def456/prikaz_42_v2.pdf",
    "file_name": "prikaz_42_v2.pdf"
  }'
```

---

## 8. Просмотр AI-diff версии (GET /api/v1/documents/{id}/versions/{vid}/diff/)

```bash
curl -X GET http://localhost:8000/api/v1/documents/doc-uuid/versions/version-uuid/diff/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Ответ (200):**
```json
{
  "version_id": "version-uuid",
  "version_number": 2,
  "ai_changes_detected": true,
  "ai_diff_summary": {
    "summary": "В новой версии добавлены 3 пункта об условиях отпуска. Удалён раздел о компенсациях.",
    "additions_count": 15,
    "deletions_count": 7
  }
}
```

---

## 9. Подписать документ (POST /api/v1/documents/{id}/sign/)

```bash
curl -X POST http://localhost:8000/api/v1/documents/doc-uuid/sign/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "signature_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "certificate_id": ""
  }'
```

---

## 10. Список задач workflow (GET /api/v1/tasks/)

```bash
curl -X GET "http://localhost:8000/api/v1/tasks/?status=in_progress" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## Тест S3-подключения (проверка без реального бакета)

```bash
# Убедитесь что .env заполнен, затем:
docker-compose exec backend python manage.py shell -c "
from apps.documents.storage import get_s3_client
client = get_s3_client()
buckets = client.list_buckets()
print('S3 OK:', [b['Name'] for b in buckets['Buckets']])
"
```
