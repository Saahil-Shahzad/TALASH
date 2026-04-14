from fastapi import APIRouter, Depends, HTTPException

from backend.app.db.mongo import get_db, normalize_mongo_doc, to_object_id
from backend.app.schemas.analysis_schema import AnalysisResponse, RoleAlignmentRequest
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.email_service import EmailService


router = APIRouter()


@router.get("/summary/{candidate_id}", response_model=AnalysisResponse)
def get_summary(candidate_id: str, db=Depends(get_db)):
    object_id = to_object_id(candidate_id)
    if object_id is None:
        raise HTTPException(status_code=400, detail="Invalid candidate id")
    candidate = db["talash"].find_one({"_id": object_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate_doc = normalize_mongo_doc(candidate)
    result = AnalysisService().generate_summary(candidate_doc)
    return AnalysisResponse(candidate_id=candidate_id, message=result["summary"], status=result["status"])


@router.get("/email-draft/{candidate_id}")
def get_email_draft(candidate_id: str, db=Depends(get_db)):
    object_id = to_object_id(candidate_id)
    if object_id is None:
        raise HTTPException(status_code=400, detail="Invalid candidate id")
    candidate = db["talash"].find_one({"_id": object_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate_doc = normalize_mongo_doc(candidate)
    draft = EmailService().draft_missing_info_email(candidate_doc)
    return {"candidate_id": candidate_id, "draft": draft}


@router.get("/report/{candidate_id}")
def get_full_report(candidate_id: str, db=Depends(get_db)):
    object_id = to_object_id(candidate_id)
    if object_id is None:
        raise HTTPException(status_code=400, detail="Invalid candidate id")
    candidate = db["talash"].find_one({"_id": object_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate_doc = normalize_mongo_doc(candidate)
    report = AnalysisService().build_full_report(candidate_doc)
    return report


@router.post("/role-alignment/{candidate_id}")
def post_role_alignment(candidate_id: str, payload: RoleAlignmentRequest, db=Depends(get_db)):
    object_id = to_object_id(candidate_id)
    if object_id is None:
        raise HTTPException(status_code=400, detail="Invalid candidate id")
    candidate = db["talash"].find_one({"_id": object_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate_doc = normalize_mongo_doc(candidate)
    result = AnalysisService().analyze_job_role_alignment(candidate_doc, payload.job_description)
    return {"candidate_id": candidate_id, "alignment": result}

