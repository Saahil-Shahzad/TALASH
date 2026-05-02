import os

from backend.app.services.analysis_service import AnalysisService


def test_build_full_report_smoke() -> None:
    os.environ["RESEARCH_VERIFY_ENABLED"] = "0"
    candidate_doc = {
        "id": "507f1f77bcf86cd799439011",
        "source_file": "sample.pdf",
        "full_name": "Ada Lovelace",
        "raw_text": "Ada Lovelace\nEmail: ada@example.com\nPython ML FastAPI\n",
        "parsed_json": {
            "personal_info": {
                "full_name": "Ada Lovelace",
                "email": "ada@example.com",
                "phone": "",
                "location": "",
                "linkedin": "",
                "google_scholar": "",
            },
            "education": [
                {
                    "degree": "BS Computer Science",
                    "institution": "Example University",
                    "passing_year": "2021",
                    "cgpa_or_score": "3.5",
                }
            ],
            "experience": [
                {
                    "role": "Software Engineer",
                    "organization": "Example Corp",
                    "location": "",
                    "duration_of_employment": "Jan 2022 - Present",
                }
            ],
            "skills": ["Python", "FastAPI"],
            "publications": [
                {
                    "title": "Machine Learning for CV Parsing",
                    "author": "Ada Lovelace",
                    "co-author": "Alan Turing",
                    "published_in": "International Conference on AI",
                    "date": "2024",
                }
            ],
            "patents": [],
            "books": [],
            "missing_info": ["personal_info.phone", "personal_info.location"],
        },
    }

    report = AnalysisService().build_full_report(candidate_doc)
    assert report["candidate_id"] == candidate_doc["id"]
    assert "educational" in report
    assert "professional" in report
    assert "research" in report
    assert "supervision" in report
    assert "books" in report
    assert "patents" in report
    assert "skills_alignment" in report
    assert "missing_info" in report
    assert "summary" in report
    assert isinstance(report["summary"].get("text"), str)


def test_generate_summary_status_missing_info() -> None:
    os.environ["RESEARCH_VERIFY_ENABLED"] = "0"
    candidate_doc = {
        "id": "507f1f77bcf86cd799439012",
        "source_file": "sample.pdf",
        "full_name": "Candidate",
        "raw_text": "",
        "parsed_json": {"missing_info": ["personal_info.email"]},
    }

    result = AnalysisService().generate_summary(candidate_doc)
    assert result["status"] == "missing_info"
    assert isinstance(result["summary"], str)


def test_job_role_alignment_scores_skills() -> None:
    candidate_doc = {
        "id": "507f1f77bcf86cd799439013",
        "source_file": "sample.pdf",
        "raw_text": "Python FastAPI Docker",
        "parsed_json": {"skills": ["Python", "FastAPI", "Kubernetes"]},
    }

    result = AnalysisService().analyze_job_role_alignment(
        candidate_doc,
        "We need a Python developer with FastAPI experience.",
    )
    assert result["status"] == "ok"
    assert result["top_matches"]
    python_row = next((row for row in result["top_matches"] if row["skill"] == "Python"), None)
    assert python_row is not None
    assert python_row["job_match_score"] >= 70
