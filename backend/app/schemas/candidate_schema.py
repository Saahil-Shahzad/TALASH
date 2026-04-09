from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CandidateOut(BaseModel):
    id: str
    source_file: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    skills_csv: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateDetail(CandidateOut):
    parsed_json: dict[str, Any]


class ProcessFolderRequest(BaseModel):
    folder_path: str
    overwrite_existing: bool = False


class ProcessResult(BaseModel):
    processed_count: int
    skipped_count: int
    failed_count: int
    files: list[dict[str, Any]]
    export_csv: str
    export_xlsx: str
    export_tables: dict[str, str] | None = None
