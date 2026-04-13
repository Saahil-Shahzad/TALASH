from fastapi import APIRouter, Depends, HTTPException

from backend.app.db.mongo import get_db, normalize_mongo_doc, to_object_id
from backend.app.schemas.candidate_schema import CandidateDetail, CandidateOut


router = APIRouter()


@router.get("/", response_model=list[CandidateOut])
def list_candidates(db=Depends(get_db)):
    cursor = db["talash"].find().sort("created_at", -1)
    return [normalize_mongo_doc(item) for item in cursor]


@router.get("/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: str, db=Depends(get_db)):
    object_id = to_object_id(candidate_id)
    if object_id is None:
        raise HTTPException(status_code=400, detail="Invalid candidate id")
    candidate = db["talash"].find_one({"_id": object_id})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return normalize_mongo_doc(candidate)

