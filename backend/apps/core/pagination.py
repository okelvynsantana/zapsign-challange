"""Default pagination for every list endpoint (``contracts/rest-api.md`` conventions)."""

from rest_framework.pagination import PageNumberPagination

__all__ = ["DefaultPageNumberPagination"]


class DefaultPageNumberPagination(PageNumberPagination):
    """``?page=<n>&page_size=<1..100>`` returning ``{count, next, previous, results}``."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
