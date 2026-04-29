import re
from typing import Final

from django.db.models import Q, QuerySet
from rest_framework.filters import BaseFilterBackend
from rest_framework.request import Request
from rest_framework.views import APIView


SEARCH_PREFIXES: Final[tuple[str, ...]] = ("^", "=", "@", "$")
WORD_BOUNDARY_PATTERN: Final[str] = r"(^|[^A-Za-z0-9]){}([^A-Za-z0-9]|$)"


class WholeWordSearchFilter(BaseFilterBackend):
    search_param = "search"

    def filter_queryset(
        self,
        request: Request,
        queryset: QuerySet,
        view: APIView,
    ) -> QuerySet:
        search_value = request.query_params.get(self.search_param)

        if not search_value:
            return queryset

        search_fields = self.get_search_fields(view)

        if not search_fields:
            return queryset

        for word in self.get_search_words(search_value):
            queryset = queryset.filter(
                self.build_word_query(word=word, search_fields=search_fields)
            )

        return queryset

    @staticmethod
    def get_search_fields(view: APIView) -> list[str]:
        return [
            WholeWordSearchFilter.normalize_search_field(field)
            for field in getattr(view, "search_fields", [])
        ]

    @staticmethod
    def normalize_search_field(field: str) -> str:
        if field.startswith(SEARCH_PREFIXES):
            return field[1:]

        return field

    @staticmethod
    def get_search_words(search_value: str) -> list[str]:
        return [
            word.strip()
            for word in search_value.split()
            if word.strip()
        ]

    @staticmethod
    def build_word_query(word: str, search_fields: list[str]) -> Q:
        pattern = WORD_BOUNDARY_PATTERN.format(re.escape(word))
        query = Q()

        for field in search_fields:
            query |= Q(**{f"{field}__iregex": pattern})

        return query