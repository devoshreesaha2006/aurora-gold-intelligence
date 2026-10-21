from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.common import StandardResponse, PaginationMeta
from backend.app.schemas.ingestion import UploadResult, ImportBatchRead
from backend.app.services.ingestion_service import CsvIngestionService
from backend.app.models.data_import import ImportBatch

router = APIRouter(tags=["Data Ingestion & Pipeline"])


@router.post("/data/upload", response_model=StandardResponse[UploadResult])
async def upload_csv_data(
    file: UploadFile = File(..., description="MCX Bhavcopy or commodity market data CSV file"),
    data_source: str = Form("csv_upload", description="Source label, e.g. 'mcx_bhavcopy_public'"),
    is_synthetic: bool = Form(False, description="Flag indicating synthetic demo data"),
    allow_duplicates: bool = Form(False, description="Whether to re-import a file with identical checksum"),
    db: Session = Depends(get_db)
):
    """
    Ingests, validates, normalizes, and stores historical commodity market data from CSV.
    - Validates column headers, dates, numbers, and logical constraints.
    - Rejects invalid rows with line-by-line diagnostic error reports.
    - Normalizes contract prices to common ₹/g fine-gold basis.
    - Enforces deduplication via file hash and observation constraints.
    - Tags records with explicit data provenance.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files (.csv) are accepted.")

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {str(e)}")

    if not content or len(content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

    service = CsvIngestionService(db)
    result = service.process_csv(
        file_bytes=content,
        filename=file.filename,
        data_source=data_source,
        is_synthetic=is_synthetic,
        allow_duplicates=allow_duplicates
    )

    return StandardResponse(
        success=(result.status != "failed"),
        message=result.message,
        data=result
    )


@router.get("/data/imports", response_model=StandardResponse[List[ImportBatchRead]])
def list_import_batches(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieves history of ingested batches, file hashes, timestamps, and accepted/rejected metrics.
    """
    query = db.query(ImportBatch).order_by(ImportBatch.created_at.desc())
    total = query.count()
    batches = query.offset(offset).limit(limit).all()

    return StandardResponse(
        success=True,
        message=f"Retrieved {len(batches)} import batches",
        data=[ImportBatchRead.model_validate(b) for b in batches],
        meta={"total": total, "limit": limit, "offset": offset}
    )
