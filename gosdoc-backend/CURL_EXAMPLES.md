# ГосДок — Примеры curl-запросов

Base URL: `http://localhost:8000`

---

## 1. Регистрация (POST /api/v1/auth/register/)

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ivanov@gosdoc.kz",
    "full_name": "Иванов Иван Иванович",
    "phone": "+77001234567",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
  }'
```

**Ответ (201):**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "ivanov@gosdoc.kz",
    "full_name": "Иванов Иван Иванович"
  },
  "tokens": {
    "refresh": "eyJ0eXAiOiJKV1Q...",
    "access": "eyJ0eXAiOiJKV1Q..."
  }
}
```

---

## 2. Вход (POST /api/v1/auth/login/)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ivanov@gosdoc.kz",
    "password": "SecurePass123!"
  }'
```

**Ответ (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1Q...",
  "refresh": "eyJ0eXAiOiJKV1Q...",
  "user": {
    "id": "550e8400-...",
    "email": "ivanov@gosdoc.kz",
    "full_name": "Иванов Иван Иванович"
  }
}
```

---

## 3. Обновление токена (POST /api/v1/auth/refresh/)

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJ0eXAiOiJKV1Q..."
  }'
```

**Ответ (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1Q..."
}
```

---

## 4. Профиль текущего пользователя (GET /api/v1/users/me/)

```bash
# Сохраните access-токен в переменную:
ACCESS_TOKEN="eyJ0eXAiOiJKV1Q..."

curl -X GET http://localhost:8000/api/v1/users/me/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Ответ (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "ivanov@gosdoc.kz",
  "full_name": "Иванов Иван Иванович",
  "phone": "+77001234567",
  "organization": null,
  "organization_name": null,
  "is_active": true,
  "created_at": "2026-03-29T10:00:00Z",
  "last_login": "2026-03-29T10:05:00Z"
}
```

---

## 5. Выход (POST /api/v1/auth/logout/)

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJ0eXAiOiJKV1Q..."}'
```

---

## 6. Смена пароля (POST /api/v1/auth/password/change/)

```bash
curl -X POST http://localhost:8000/api/v1/auth/password/change/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "SecurePass123!",
    "new_password": "NewPass456!",
    "new_password_confirm": "NewPass456!"
  }'
```

---

## 7. Создание организации (POST /api/v1/organizations/)

```bash
curl -X POST http://localhost:8000/api/v1/organizations/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Министерство цифрового развития",
    "type": "corporate",
    "inn": "123456789012"
  }'
```

---

## 8. Создание кабинета (POST /api/v1/workspaces/)

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Согласование приказа №42",
    "type": "individual",
    "organization": "ORG_UUID_HERE",
    "description": "Согласование внутреннего приказа"
  }'
```

---

## 9. Загрузка документа (POST /api/v1/documents/)

```bash
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "title=Приказ №42" \
  -F "workspace=WORKSPACE_UUID_HERE" \
  -F "file=@/path/to/document.pdf"
```

---

## 10. Swagger UI

Откройте в браузере: http://localhost:8000/api/schema/swagger-ui/
