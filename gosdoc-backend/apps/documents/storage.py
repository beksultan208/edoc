"""
ГосДок — Утилиты для работы с S3/Object Storage (apps/documents/storage.py)
Раздел 2.5, 6 ТЗ: приватные бакеты, presigned URL TTL 60 мин,
прямая загрузка через presigned POST (без проксирования через Django).
"""

import hashlib
import logging
import uuid
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

# Допустимые MIME-типы для каждого расширения
CONTENT_TYPE_MAP = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "odt": "application/vnd.oasis.opendocument.text",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
}


def get_s3_client():
    """
    Создаёт boto3 S3-клиент.
    Поддерживает AWS S3 и Yandex Object Storage (через AWS_S3_ENDPOINT_URL).
    """
    endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
    # Если кастомный endpoint не задан — используем региональный AWS endpoint.
    # Это критично для presigned POST: глобальный s3.amazonaws.com делает 307 redirect,
    # который браузер не проксирует с CORS заголовками.
    if not endpoint_url:
        region = settings.AWS_S3_REGION_NAME
        endpoint_url = f"https://s3.{region}.amazonaws.com"

    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        endpoint_url=endpoint_url,
        config=Config(signature_version="s3v4"),
    )


def generate_storage_key(workspace_id: str, filename: str) -> str:
    """
    Генерирует уникальный ключ объекта в S3.
    Формат: documents/{workspace_id}/{uuid}/{sanitized_filename}

    Имя файла санируется: пробелы → подчёркивания, кириллица сохраняется.
    """
    unique_id = uuid.uuid4().hex
    # Простая санация: убираем путь (безопасность), оставляем имя
    safe_name = filename.replace(" ", "_").split("/")[-1].split("\\")[-1]
    return f"documents/{workspace_id}/{unique_id}/{safe_name}"


def compute_sha256(file_obj) -> str:
    """
    Вычисляет SHA-256 чексумму открытого файлового объекта.
    Раздел 2.5 ТЗ: контроль целостности при загрузке новой версии.
    Возвращает указатель в начало файла после вычисления.
    """
    sha256 = hashlib.sha256()
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(8192), b""):
        sha256.update(chunk)
    file_obj.seek(0)
    return sha256.hexdigest()


# ============================================================
# Загрузка через Django (для небольших файлов / тестов)
# ============================================================

def upload_to_s3(file_obj, storage_key: str, content_type: str = "application/octet-stream") -> bool:
    """
    Загружает файл в S3 напрямую через Django (серверная загрузка).
    Используется для тестов и случаев, когда клиент не поддерживает presigned POST.
    Для production рекомендуется presigned POST (раздел 6 ТЗ).
    """
    try:
        client = get_s3_client()
        file_obj.seek(0)
        client.upload_fileobj(
            file_obj,
            settings.AWS_STORAGE_BUCKET_NAME,
            storage_key,
            ExtraArgs={
                "ContentType": content_type,
                "ServerSideEncryption": "AES256",  # Шифрование на стороне сервера
            },
        )
        logger.info("Файл загружен в S3 (server-side): %s", storage_key)
        return True
    except ClientError as exc:
        logger.error("Ошибка загрузки в S3: %s — %s", storage_key, exc)
        return False


# ============================================================
# Presigned POST — прямая загрузка с клиента (раздел 6 ТЗ)
# ============================================================

def generate_presigned_post(
    storage_key: str,
    content_type: str,
    max_size_bytes: int = None,
    expiration: int = 3600,
) -> Optional[dict]:
    """
    Генерирует данные для presigned POST URL.
    Клиент загружает файл напрямую в S3, Django не проксирует файл.

    Возвращает словарь вида:
    {
        "url": "https://bucket.s3.amazonaws.com/",
        "fields": {
            "key": "documents/...",
            "AWSAccessKeyId": "...",
            "policy": "...",
            "signature": "...",
            "Content-Type": "application/pdf",
            "x-amz-server-side-encryption": "AES256"
        }
    }

    Использование на клиенте (JS):
        const formData = new FormData();
        Object.entries(presigned.fields).forEach(([k, v]) => formData.append(k, v));
        formData.append('file', fileObject);
        await fetch(presigned.url, { method: 'POST', body: formData });
    """
    if max_size_bytes is None:
        max_size_bytes = settings.MAX_DOCUMENT_SIZE_BYTES

    conditions = [
        {"bucket": settings.AWS_STORAGE_BUCKET_NAME},
        {"key": storage_key},
        {"Content-Type": content_type},
        # Ограничение размера файла (раздел 2.5 ТЗ: макс. 100 МБ)
        ["content-length-range", 1, max_size_bytes],
        # Шифрование на стороне S3
        {"x-amz-server-side-encryption": "AES256"},
    ]

    fields = {
        "Content-Type": content_type,
        "x-amz-server-side-encryption": "AES256",
    }

    try:
        client = get_s3_client()
        response = client.generate_presigned_post(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=storage_key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expiration,
        )
        logger.debug("Сгенерирован presigned POST для ключа: %s", storage_key)
        return response
    except ClientError as exc:
        logger.error("Ошибка генерации presigned POST: %s — %s", storage_key, exc)
        return None


# ============================================================
# Presigned GET URL — скачивание документа (раздел 6 ТЗ)
# ============================================================

def generate_presigned_url(storage_key: str, expiration: int = None, filename: str = None) -> Optional[str]:
    """
    Генерирует presigned GET URL для скачивания файла из S3.
    TTL по умолчанию: 3600 сек (60 мин, раздел 6 ТЗ).

    Параметр filename задаёт имя файла при скачивании (Content-Disposition header).
    """
    if expiration is None:
        expiration = settings.AWS_QUERYSTRING_EXPIRE

    params = {
        "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
        "Key": storage_key,
    }
    if filename:
        # Принудительное скачивание с заданным именем
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

    try:
        client = get_s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiration,
        )
        return url
    except ClientError as exc:
        logger.error("Ошибка генерации presigned GET URL: %s — %s", storage_key, exc)
        return None


def check_object_exists(storage_key: str) -> bool:
    """
    Проверяет, существует ли объект в S3.
    Используется для подтверждения загрузки через presigned POST.
    """
    try:
        client = get_s3_client()
        client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=storage_key,
        )
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchKey"):
            return False
        logger.error("Ошибка проверки объекта S3: %s — %s", storage_key, exc)
        return False


def get_object_size(storage_key: str) -> Optional[int]:
    """Возвращает размер объекта в байтах (из HEAD запроса)."""
    try:
        client = get_s3_client()
        response = client.head_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=storage_key,
        )
        return response.get("ContentLength")
    except ClientError:
        return None


def copy_object_in_s3(source_key: str, dest_key: str) -> bool:
    """
    Копирует объект внутри S3 (используется при создании новой версии
    для сохранения предыдущей по новому ключу).
    """
    try:
        client = get_s3_client()
        client.copy_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            CopySource={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": source_key},
            Key=dest_key,
            ServerSideEncryption="AES256",
        )
        return True
    except ClientError as exc:
        logger.error("Ошибка копирования объекта S3: %s → %s — %s", source_key, dest_key, exc)
        return False


def delete_from_s3(storage_key: str) -> bool:
    """Удаляет объект из S3."""
    try:
        client = get_s3_client()
        client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=storage_key,
        )
        logger.info("Объект удалён из S3: %s", storage_key)
        return True
    except ClientError as exc:
        logger.error("Ошибка удаления из S3: %s — %s", storage_key, exc)
        return False


# ============================================================
# Валидация файлов
# ============================================================

def validate_file_extension(filename: str) -> bool:
    """Проверяет допустимость расширения файла (раздел 2.5 ТЗ)."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in settings.ALLOWED_DOCUMENT_EXTENSIONS


def validate_file_size(file_obj) -> bool:
    """Проверяет размер файла (макс. 100 МБ, раздел 2.5 ТЗ)."""
    file_obj.seek(0, 2)  # Seek to end
    size = file_obj.tell()
    file_obj.seek(0)
    return size <= settings.MAX_DOCUMENT_SIZE_BYTES


def get_content_type(filename: str) -> str:
    """Возвращает MIME-тип по расширению файла."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return CONTENT_TYPE_MAP.get(ext, "application/octet-stream")
