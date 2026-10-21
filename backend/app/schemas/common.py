from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    """Unified API response wrapper."""
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None
    meta: Optional[dict] = None


class ErrorDetail(BaseModel):
    """Structured error descriptor."""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized API error envelope."""
    success: bool = False
    error: str
    details: Optional[List[ErrorDetail]] = None


class PaginationMeta(BaseModel):
    """Pagination metadata for bounded collections."""
    total: int
    limit: int
    offset: int
    has_more: bool
