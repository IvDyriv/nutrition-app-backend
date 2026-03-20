import re

from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class WholeWordSearchFilter(BaseFilterBackend):
    search_param = "search"

    def filter_queryset(self, request, queryset, view):
        search_value = request.query_params.get(self.search_param)

        if not search_value:
            return queryset

        search_fields = getattr(view, "search_fields", [])
        if not search_fields:
            return queryset

        words = search_value.split()
        queryset = queryset

        for word in words:
            word = word.strip()
            if not word:
                continue

            escaped_word = re.escape(word)
            pattern = rf"(^|[^A-Za-z0-9]){escaped_word}([^A-Za-z0-9]|$)"

            query = Q()
            for field in search_fields:
                if field.startswith("^") or field.startswith("=") or field.startswith("@") or field.startswith("$"):
                    field = field[1:]
                query |= Q(**{f"{field}__iregex": pattern})

            queryset = queryset.filter(query)

        return queryset