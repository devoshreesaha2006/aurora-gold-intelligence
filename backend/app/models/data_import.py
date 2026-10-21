from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from backend.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ImportBatch(Base):
    """
    Audit record for ingested data batches.
    Guarantees transparency, traceability, and deduplication for CSV uploads.
    """
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), index=True, nullable=False) # SHA-256
    total_rows = Column(Integer, default=0, nullable=False)
    accepted_rows = Column(Integer, default=0, nullable=False)
    rejected_rows = Column(Integer, default=0, nullable=False)
    error_summary = Column(Text, nullable=True) # JSON array of row errors
    data_source = Column(String(100), default="csv_upload", nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
