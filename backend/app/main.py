from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes_analysis import router as analysis_router
from backend.app.api.routes_candidates import router as candidates_router
from backend.app.api.routes_upload import router as upload_router
def create_app() -> FastAPI:
    app = FastAPI(
        title="TALASH API",
        version="0.1.0",
        description="Milestone 1 backend for CV preprocessing and candidate ingestion.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
    app.include_router(candidates_router, prefix="/api/candidates", tags=["candidates"])
    app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])

    return app


app = create_app()

