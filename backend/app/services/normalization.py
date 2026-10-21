from typing import Tuple, Dict

# Standard MCX Gold Specifications lookup
MCX_GOLD_DEFAULTS: Dict[str, dict] = {
    "GOLDM": {
        "name": "Gold Mini",
        "trading_unit": "100 grams",
        "trading_unit_grams": 100.0,
        "quote_unit": "10 grams",
        "quote_unit_grams": 10.0,
        "purity": 995,
        "purity_factor": 0.995,
        "expiry_window": "3rd-5th",
        "description": "MCX Gold Mini futures contract (100g trading unit, quoted per 10g, 995 purity)."
    },
    "GOLDTEN": {
        "name": "Gold Ten Gram",
        "trading_unit": "10 grams",
        "trading_unit_grams": 10.0,
        "quote_unit": "10 grams",
        "quote_unit_grams": 10.0,
        "purity": 999,
        "purity_factor": 0.999,
        "expiry_window": "27th-31st",
        "description": "MCX Gold 10-gram futures contract (10g trading unit, quoted per 10g, 999 purity, listed 2025)."
    },
    "GOLDGUINEA": {
        "name": "Gold Guinea",
        "trading_unit": "8 grams",
        "trading_unit_grams": 8.0,
        "quote_unit": "8 grams",
        "quote_unit_grams": 8.0,
        "purity": 999,
        "purity_factor": 0.999,
        "expiry_window": "27th-31st",
        "description": "MCX Gold Guinea futures contract (8g sovereign unit, quoted per 8g, 999 purity)."
    },
    "GOLDPETAL": {
        "name": "Gold Petal",
        "trading_unit": "1 gram",
        "trading_unit_grams": 1.0,
        "quote_unit": "1 gram",
        "quote_unit_grams": 1.0,
        "purity": 999,
        "purity_factor": 0.999,
        "expiry_window": "27th-31st",
        "description": "MCX Gold Petal micro futures contract (1g trading unit, quoted per 1g, 999 purity)."
    }
}


def normalize_price(
    quoted_price: float,
    quote_unit_grams: float,
    purity_factor: float
) -> Tuple[float, float]:
    """
    Normalizes a commodity futures quoted price to:
    1. Pure fine-gold price per gram: (Quoted Price / Quoted Grams) / (Purity / 1000)
    2. Benchmark 10g 995 basis: pure_gram * 10.0 * 0.995

    Parameters:
    - quoted_price: Market settlement / trade price in INR
    - quote_unit_grams: Number of grams represented in the quote (e.g. 10.0, 8.0, 1.0)
    - purity_factor: Fine gold ratio (e.g. 0.995 or 0.999)

    Returns:
    - Tuple (normalized_price_per_gram, normalized_price_10g_basis)
    """
    if quote_unit_grams <= 0:
        raise ValueError(f"quote_unit_grams must be positive, got {quote_unit_grams}")
    if purity_factor <= 0 or purity_factor > 1.0:
        raise ValueError(f"purity_factor must be between 0 and 1.0, got {purity_factor}")

    price_per_gross_gram = quoted_price / quote_unit_grams
    price_per_fine_gram = price_per_gross_gram / purity_factor
    normalized_10g_basis = price_per_fine_gram * 10.0 * 0.995

    return round(price_per_fine_gram, 4), round(normalized_10g_basis, 2)
