from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session
from backend.app.models.contract import Contract
from backend.app.services.normalization import MCX_GOLD_DEFAULTS


def seed_default_contracts(db: Session) -> List[Contract]:
    """
    Ensures default MCX Gold contracts exist in the database.
    Idempotent operation run at application startup.
    """
    seeded = []
    for symbol, spec in MCX_GOLD_DEFAULTS.items():
        existing = db.query(Contract).filter(Contract.symbol == symbol).first()
        if not existing:
            contract = Contract(
                symbol=symbol,
                name=spec["name"],
                trading_unit=spec["trading_unit"],
                trading_unit_grams=spec["trading_unit_grams"],
                quote_unit=spec["quote_unit"],
                quote_unit_grams=spec["quote_unit_grams"],
                purity=spec["purity"],
                purity_factor=spec["purity_factor"],
                expiry_window=spec.get("expiry_window"),
                listing_date=date(2025, 1, 1) if symbol == "GOLDTEN" else None,
                is_active=True,
                description=spec.get("description")
            )
            db.add(contract)
            seeded.append(contract)
    if seeded:
        db.commit()
    return db.query(Contract).all()


def get_all_contracts(db: Session, active_only: bool = False) -> List[Contract]:
    query = db.query(Contract)
    if active_only:
        query = query.filter(Contract.is_active == True)
    return query.order_by(Contract.id).all()


def get_contract_by_symbol(db: Session, symbol: str) -> Optional[Contract]:
    return db.query(Contract).filter(Contract.symbol == symbol.strip().upper()).first()
