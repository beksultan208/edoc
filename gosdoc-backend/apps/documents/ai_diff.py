"""
ГосДок — AI-детектор изменений в документах (apps/documents/ai_diff.py)
Раздел 2.6 ТЗ:
1. Извлечение текста (PDF→PyMuPDF, DOCX→python-docx)
2. Сравнение версий через difflib
3. Классификация: добавление, удаление, замена, форматирование
4. Резюме на русском через OpenAI
5. Сохранение в ai_diff_summary (JSONB)
"""

import difflib
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Извлекает текст из PDF с помощью PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except ImportError:
        logger.warning("PyMuPDF не установлен, пропускаем извлечение текста из PDF")
        return ""
    except Exception as exc:
        logger.error("Ошибка извлечения текста из PDF: %s", exc)
        return ""


def extract_text_from_docx(file_path: str) -> str:
    """Извлекает текст из DOCX с помощью python-docx."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)
    except ImportError:
        logger.warning("python-docx не установлен")
        return ""
    except Exception as exc:
        logger.error("Ошибка извлечения текста из DOCX: %s", exc)
        return ""


def extract_text(file_path: str, file_type: str) -> str:
    """Диспетчер: выбирает метод извлечения текста по типу файла."""
    file_type = file_type.lower()
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type in ("docx", "odt"):
        return extract_text_from_docx(file_path)
    else:
        # xlsx, ods — текстовое извлечение не реализовано в этапе 1
        logger.info("Тип %s: извлечение текста не поддерживается", file_type)
        return ""


def compute_diff(old_text: str, new_text: str) -> dict:
    """
    Сравнивает два текста и классифицирует изменения.
    Возвращает словарь с категориями изменений.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    differ = difflib.Differ()
    diff = list(differ.compare(old_lines, new_lines))

    additions = [line[2:] for line in diff if line.startswith("+ ")]
    deletions = [line[2:] for line in diff if line.startswith("- ")]

    return {
        "additions_count": len(additions),
        "deletions_count": len(deletions),
        "additions_sample": additions[:5],  # Первые 5 примеров
        "deletions_sample": deletions[:5],
        "has_changes": bool(additions or deletions),
    }


def generate_ai_summary(diff_data: dict, old_text: str, new_text: str) -> Optional[str]:
    """
    Генерирует краткое резюме изменений через OpenAI API.
    Возвращает строку с резюме или None при ошибке.
    """
    if not settings.OPENAI_API_KEY:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        prompt = (
            f"Проанализируй изменения в документе:\n"
            f"- Добавлено строк: {diff_data['additions_count']}\n"
            f"- Удалено строк: {diff_data['deletions_count']}\n"
            f"Примеры добавленных фрагментов: {diff_data['additions_sample']}\n"
            f"Примеры удалённых фрагментов: {diff_data['deletions_sample']}\n\n"
            f"Напиши краткое (2-3 предложения) резюме изменений на русском языке."
        )

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Ты — ассистент для анализа изменений в официальных документах."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    except Exception as exc:
        logger.error("Ошибка OpenAI API: %s", exc)
        return None


def analyze_document_diff(
    old_file_path: str,
    new_file_path: str,
    file_type: str,
) -> dict:
    """
    Основная функция AI-анализа изменений между двумя версиями документа.

    Возвращает словарь для сохранения в ai_diff_summary (JSONB):
    {
        "ai_changes_detected": bool,
        "summary": str | None,
        "additions_count": int,
        "deletions_count": int,
        "additions_sample": list,
        "deletions_sample": list,
    }
    """
    result = {
        "ai_changes_detected": False,
        "summary": None,
        "additions_count": 0,
        "deletions_count": 0,
        "additions_sample": [],
        "deletions_sample": [],
    }

    old_text = extract_text(old_file_path, file_type)
    new_text = extract_text(new_file_path, file_type)

    if not old_text and not new_text:
        result["summary"] = "Текстовое содержимое недоступно для анализа."
        return result

    diff_data = compute_diff(old_text, new_text)
    result.update(diff_data)
    result["ai_changes_detected"] = diff_data["has_changes"]

    if diff_data["has_changes"]:
        result["summary"] = generate_ai_summary(diff_data, old_text, new_text)

    return result
