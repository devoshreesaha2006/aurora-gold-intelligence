from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
import backend.app.models  # Register all models on Base.metadata
from backend.app.services.contract_service import seed_default_contracts
from backend.app.api.router import api_router
from backend.app.schemas.common import ErrorResponse, ErrorDetail


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context:
    1. Initializes database schema (creates tables if not present).
    2. Seeds official MCX Gold contract specifications.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_contracts(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AURORA is an explainable Commodity Intelligence & Relative-Value Platform "
        "designed for MCX gold futures (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL). "
        "Normalizes contracts to a common fine-gold basis, inspects liquidity/expiry, "
        "and tracks relative-value opportunities."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include main API router
app.include_router(api_router)


# Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=str(exc.detail),
            details=[ErrorDetail(message=str(exc.detail), code=str(exc.status_code))]
        ).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        error_details.append(
            ErrorDetail(
                field=field,
                message=err.get("msg", "Validation error"),
                code=err.get("type")
            )
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            success=False,
            error="Input validation failed",
            details=error_details
        ).model_dump()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error="An unexpected internal server error occurred",
            details=[ErrorDetail(message=str(exc), code="INTERNAL_SERVER_ERROR")]
        ).model_dump()
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "platform": settings.app_name,
        "version": settings.app_version,
        "docs_url": "/docs",
        "health_url": "/api/health",
        "market_status_url": "/api/market/status"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.aurora_host, port=settings.aurora_port, reload=True)
