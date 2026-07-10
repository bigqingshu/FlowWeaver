from __future__ import annotations

from typing import Any

from fastapi import Request

from flowweaver.api.responses import error_response, ok_response


def pagination_rejection(
    request: Request,
    *,
    offset: int,
    limit: int,
):
    if offset < 0:
        return error_response(
            request,
            error_code="INVALID_PAGINATION",
            message="offset must be non-negative",
            status_code=422,
            details={"offset": offset},
        )
    if limit < 1 or limit > 500:
        return error_response(
            request,
            error_code="INVALID_PAGINATION",
            message="limit must be between 1 and 500",
            status_code=422,
            details={"limit": limit},
        )
    return None


def paginated_ok_response(
    request: Request,
    *,
    items: list[Any],
    offset: int,
    limit: int,
    total: int,
    paged: bool,
):
    has_more = offset + len(items) < total
    data: Any = items
    if paged:
        data = {
            "items": items,
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": has_more,
        }
    response = ok_response(request, data)
    response.headers["X-Pagination-Offset"] = str(offset)
    response.headers["X-Pagination-Limit"] = str(limit)
    response.headers["X-Pagination-Total"] = str(total)
    response.headers["X-Pagination-Has-More"] = str(has_more).lower()
    return response
