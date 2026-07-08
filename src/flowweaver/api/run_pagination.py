from __future__ import annotations

from fastapi import Request

from flowweaver.api.responses import error_response


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
