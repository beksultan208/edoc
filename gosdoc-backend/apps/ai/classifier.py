"""
ГосДок — ML-классификатор типа документа (apps/ai/classifier.py)

Определяет тип документа по тексту: contract, order, act, invoice, report, letter, other.

Алгоритм:
  1. Если на диске лежит обученная модель (TF-IDF + LogisticRegression) — используем её.
  2. Если модели нет — fallback на keyword-based классификацию по словарю.

Модель ожидается в settings.AI_CLASSIFIER_MODEL_PATH (.joblib),
сериализованная как dict {"vectorizer": TfidfVectorizer, "model": LogisticRegression}.
"""

import logging
import os
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


# Человекочитаемые названия типов на русском
TYPE_LABELS = {
    "contract": "Договор",
    "order": "Приказ",
    "act": "Акт",
    "invoice": "Счёт-фактура",
    "report": "Отчёт",
    "letter": "Письмо",
    "other": "Прочее",
}

# Keyword fallback: ключевые слова для каждого типа на русском и казахском.
# Чем больше совпадений в тексте — тем выше уверенность.
KEYWORDS = {
    "contract": [
        # RU
        "договор", "соглашение", "контракт", "стороны", "обязуется",
        "предмет договора", "заключили настоящий",
        # KZ
        "шарт", "келісім", "тараптар", "міндеттенеді",
    ],
    "order": [
        # RU
        "приказ", "приказываю", "распоряжение", "поручаю", "назначить",
        # KZ
        "бұйрық", "бұйырамын", "тағайындау", "өкім",
    ],
    "act": [
        # RU
        "акт", "акт приёма", "акт выполненных", "составили настоящий акт",
        "комиссия в составе",
        # KZ
        "акт", "қабылдау актісі", "комиссия құрамында",
    ],
    "invoice": [
        # RU
        "счёт-фактура", "счет-фактура", "счёт", "ндс", "итого к оплате",
        "поставщик", "покупатель",
        # KZ
        "шот-фактура", "шот", "қсқ", "төлеуге барлығы",
    ],
    "report": [
        # RU
        "отчёт", "отчет", "анализ", "результаты", "за период",
        "выводы", "рекомендации",
        # KZ
        "есеп", "талдау", "нәтижелер", "қорытынды",
    ],
    "letter": [
        # RU
        "уважаемый", "уважаемая", "просим", "сообщаем", "направляем",
        "с уважением",
        # KZ
        "құрметті", "сұраймыз", "хабарлаймыз", "құрметпен",
    ],
}


class DocumentClassifier:
    """
    Классификатор типа документа.

    Использует обученную TF-IDF + LogisticRegression модель,
    если она доступна на диске. Иначе — keyword-based fallback.
    """

    _cached_pipeline: Optional[dict] = None
    _cache_loaded: bool = False

    def __init__(self):
        self._pipeline = self._load_pipeline()

    @classmethod
    def _load_pipeline(cls) -> Optional[dict]:
        """
        Лениво загружает обученную модель из AI_CLASSIFIER_MODEL_PATH.
        Кэшируется на уровне класса — модель грузится один раз на процесс.

        Returns:
            dict с ключами {"vectorizer", "model", "labels"} или None.
        """
        if cls._cache_loaded:
            return cls._cached_pipeline

        cls._cache_loaded = True
        path = getattr(settings, "AI_CLASSIFIER_MODEL_PATH", "")
        if not path or not os.path.exists(path):
            logger.info(
                "DocumentClassifier: обученная модель не найдена (%s), "
                "используется keyword fallback",
                path or "путь не задан",
            )
            return None

        try:
            import joblib
            pipeline = joblib.load(path)
            logger.info("DocumentClassifier: модель загружена из %s", path)
            cls._cached_pipeline = pipeline
            return pipeline
        except Exception as exc:
            logger.error(
                "DocumentClassifier: не удалось загрузить модель из %s: %s",
                path, exc,
            )
            return None

    def classify(self, text: str) -> dict:
        """
        Определяет тип документа.

        Args:
            text: исходный текст документа

        Returns:
            {"type": str, "confidence": float, "label": str}
        """
        if not text or not text.strip():
            return {"type": "other", "confidence": 0.0, "label": TYPE_LABELS["other"]}

        if self._pipeline:
            try:
                return self._classify_ml(text)
            except Exception as exc:
                logger.error(
                    "DocumentClassifier: сбой ML-классификации, fallback на keyword: %s",
                    exc,
                )

        return self._classify_keywords(text)

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _classify_ml(self, text: str) -> dict:
        """TF-IDF + LogisticRegression."""
        vectorizer = self._pipeline["vectorizer"]
        model = self._pipeline["model"]

        features = vectorizer.transform([text[:20_000]])
        probabilities = model.predict_proba(features)[0]
        idx = int(probabilities.argmax())
        doc_type = str(model.classes_[idx])
        confidence = float(probabilities[idx])

        return {
            "type": doc_type,
            "confidence": round(confidence, 4),
            "label": TYPE_LABELS.get(doc_type, doc_type),
        }

    def _classify_keywords(self, text: str) -> dict:
        """
        Считает совпадения ключевых слов для каждого типа.
        Confidence = доля совпадений лидера от суммы всех совпадений.
        """
        lowered = text.lower()
        scores = {
            doc_type: sum(1 for kw in keywords if kw in lowered)
            for doc_type, keywords in KEYWORDS.items()
        }

        total = sum(scores.values())
        if total == 0:
            return {"type": "other", "confidence": 0.0, "label": TYPE_LABELS["other"]}

        best_type = max(scores, key=scores.get)
        confidence = scores[best_type] / total

        return {
            "type": best_type,
            "confidence": round(confidence, 4),
            "label": TYPE_LABELS[best_type],
        }
