from __future__ import annotations

import re
from typing import Any

import httpx

from backend.app.core.config import settings


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _extract_isbn(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    # Strip common prefixes and punctuation.
    text = re.sub(r"(?i)\bisbn\b\s*:?\s*", "", text)
    digits = re.sub(r"[^0-9xX]", "", text)
    if len(digits) in {10, 13}:
        return digits.upper()

    # Look for embedded ISBN-like sequences.
    match = re.search(r"\b(?:97[89])?[0-9]{9}[0-9Xx]\b", text)
    return match.group(0).upper() if match else ""


def _http_client() -> httpx.Client:
    timeout = settings.RESEARCH_VERIFY_TIMEOUT_SECONDS
    return httpx.Client(timeout=timeout, headers={"Accept": "application/json", "User-Agent": "TALASH/0.1"})


class BooksVerificationService:
    def verify_book(self, book: dict[str, Any]) -> dict[str, Any]:
        isbn = _extract_isbn(book.get("isbn")) or _extract_isbn(book.get("title"))
        if not isbn:
            return {"status": "unverified", "reason": "isbn_missing"}

        # OpenLibrary: https://openlibrary.org/isbn/{isbn}.json
        url = f"https://openlibrary.org/isbn/{isbn}.json"
        try:
            with _http_client() as client:
                resp = client.get(url)
                if resp.status_code == 404:
                    return {"status": "not_found", "isbn": isbn}
                resp.raise_for_status()
                payload = resp.json() or {}
        except Exception as exc:
            return {"status": "error", "isbn": isbn, "error": type(exc).__name__}

        return {
            "status": "verified",
            "isbn": isbn,
            "title": payload.get("title") or "",
            "publish_date": payload.get("publish_date") or "",
            "publishers": payload.get("publishers") or [],
            "number_of_pages": payload.get("number_of_pages"),
            "openlibrary_url": f"https://openlibrary.org/isbn/{isbn}",
        }


class PatentsVerificationService:
    def verify_patent(self, patent: dict[str, Any]) -> dict[str, Any]:
        patent_number = _clean_text(patent.get("patent_number"))
        title = _clean_text(patent.get("title"))

        if not patent_number and not title:
            return {"status": "unverified", "reason": "no_patent_number_or_title"}

        # PatentsView (US patents): https://patentsview.org/apis/purpose
        # We use a best-effort query; non-US patents may not be found.
        if patent_number:
            q = {"patent_number": patent_number}
        else:
            q = {"_text_any": {"patent_title": title}}

        url = "https://api.patentsview.org/patents/query"
        # PatentsView expects JSON in query string keys; we'll build manually.
        try:
            import json

            query = json.dumps(q)
            fields = json.dumps(
                [
                    "patent_number",
                    "patent_title",
                    "patent_date",
                    "patent_type",
                    "patent_kind",
                ]
            )

            with _http_client() as client:
                resp = client.get(url, params={"q": query, "f": fields, "o": json.dumps({"per_page": 3})})
                resp.raise_for_status()
                payload = resp.json() or {}
        except Exception as exc:
            return {"status": "error", "error": type(exc).__name__}

        patents = payload.get("patents") or []
        if not patents:
            return {"status": "not_found", "patent_number": patent_number, "title": title}

        best = patents[0]
        return {
            "status": "verified",
            "patent_number": best.get("patent_number") or "",
            "title": best.get("patent_title") or "",
            "date": best.get("patent_date") or "",
            "patent_type": best.get("patent_type") or "",
            "patent_kind": best.get("patent_kind") or "",
            "source": "patentsview",
        }
