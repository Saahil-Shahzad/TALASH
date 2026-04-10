from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.core.config import settings
from backend.app.db.mongo import get_db
from backend.app.schemas.candidate_schema import ProcessFolderRequest, ProcessResult
from backend.app.services.parser_service import ParserService


router = APIRouter()


@router.post("/process-folder", response_model=ProcessResult)
def process_folder(payload: ProcessFolderRequest, db=Depends(get_db)):
    service = ParserService(db)
    try:
        return service.process_folder(payload.folder_path, payload.overwrite_existing)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload-files", response_model=ProcessResult)
def upload_and_process(files: list[UploadFile] = File(...), db=Depends(get_db)):
    saved = []
    for item in files:
        if not item.filename.lower().endswith(".pdf"):
            continue
        target = settings.RAW_CV_DIR / item.filename
        with target.open("wb") as buffer:
            shutil.copyfileobj(item.file, buffer)
        saved.append(target)

    if not saved:
        raise HTTPException(status_code=400, detail="No valid PDF files uploaded.")

    service = ParserService(db)
    return service.process_folder(str(Path(settings.RAW_CV_DIR)), overwrite_existing=True)


@router.get("/status")
def get_processing_status(folder_path: str | None = None, db=Depends(get_db)):
    service = ParserService(db)
    target_path = folder_path or str(Path(settings.RAW_CV_DIR))
    try:
        return service.get_processing_status(target_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

