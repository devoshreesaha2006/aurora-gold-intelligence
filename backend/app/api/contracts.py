from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.common import StandardResponse
from backend.app.schemas.contract import ContractRead
from backend.app.services.contract_service import get_all_contracts

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=StandardResponse[List[ContractRead]])
def list_contracts(
    active_only: bool = Query(False, description="Filter only active contracts"),
    db: Session = Depends(get_db)
):
    """
    Retrieves all supported MCX commodity contracts, their lot sizes,
    quotation specifications, and purity bases.
    """
    contracts = get_all_contracts(db, active_only=active_only)
    return StandardResponse(
        success=True,
        message=f"Retrieved {len(contracts)} contracts",
        data=[ContractRead.model_validate(c) for c in contracts]
    )
