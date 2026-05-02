import os

from backend.app.services.research_verification_service import ResearchVerificationService


def test_verification_disabled_no_title_match() -> None:
    os.environ["RESEARCH_VERIFY_ENABLED"] = "0"

    service = ResearchVerificationService()
    pub = {
        "title": "A Study on Something",
        "published_in": "Journal of Tests",
        "date": "2024",
        "author": "Ada Lovelace",
        "co-author": "Alan Turing",
    }
    result = service.verify_publication(pub, candidate_name="ada lovelace")

    assert result["status"] in {"verification_disabled", "unverified_external"}
    assert "indexing" in result
    assert result["best_match"] is None
