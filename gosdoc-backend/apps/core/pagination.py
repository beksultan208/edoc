"""
ГосДок — Стандартная пагинация (apps/core/pagination.py)
Раздел 6 ТЗ: page_size по умолчанию 20.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Стандартная пагинация для всех списковых эндпоинтов.
    Поддерживает параметры ?page=N&page_size=M (макс. 100).
    """
    page_size = 20               # По умолчанию 20 (раздел 6 ТЗ)
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })
