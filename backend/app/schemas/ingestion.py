from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field, computed_field


class RowError(BaseModel):
    row_number: int = Field(..., description="1-indexed line number in CSV (excluding header)")
    field: Optional[str] = None
    reason: str
    raw_data: Optional[Dict[str, Any]] = None


class UploadResult(BaseModel):
    batch_id: int
    filename: str
    file_hash: str
    data_source: str
    is_synthetic: bool
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_rows: int
    status: str = Field(..., description="'completed', 'partial_success', or 'failed'")
    errors: List[RowError] = []
    message: str


class ImportBatchRead(BaseModel):
    id: int
    filename: str
    file_hash: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    data_source: str
    is_synthetic: bool
    created_at: datetime
    error_summary: Optional[str] = None

    @computed_field
    @property
    def duplicate_rows(self) -> int:
        return max(0, self.total_rows - self.accepted_rows - self.rejected_rows)

    @computed_field
    @property
    def status(self) -> str:
        if self.accepted_rows == 0 and self.rejected_rows > 0:
            return "failed"
        if self.rejected_rows > 0:
            return "partial_success"
        return "completed"

    model_config = ConfigDict(from_attributes=True)
