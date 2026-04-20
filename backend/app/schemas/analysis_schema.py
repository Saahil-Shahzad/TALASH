from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    candidate_id: str


class AnalysisResponse(BaseModel):
    candidate_id: str
    message: str
    status: str


class RoleAlignmentRequest(BaseModel):
    job_description: str
