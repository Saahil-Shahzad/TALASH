from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from rapidfuzz import fuzz

from backend.app.core.config import _as_bool, settings


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm_title(title: str) -> str:
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _safe_ratio(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return int(fuzz.ratio(a, b))


def _extract_year(value: Any) -> int | None:
    text = _clean_text(value)
    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if not match:
        return None
    return _as_int(match.group(1))


def _split_names(value: Any) -> list[str]:
    text = _clean_text(value)
    if not text:
        return []
    parts = [p.strip() for p in re.split(r",|;|\band\b", text, flags=re.IGNORECASE) if p.strip()]
    return parts


def _conference_ordinal(text: str) -> int | None:
    text = _clean_text(text)
    match = re.search(r"\b(\d{1,3})(?:st|nd|rd|th)\b", text, flags=re.IGNORECASE)
    if match:
        return _as_int(match.group(1))
    return None


def _norm_issn(value: str) -> str:
    value = _clean_text(value)
    # Keep digits/X, drop hyphens/spaces.
    return re.sub(r"[^0-9Xx]", "", value).upper()


def _split_issn_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, list):
        raw = [str(v) for v in values]
    else:
        raw = re.split(r",|;|\s+", str(values))
    out: list[str] = []
    for token in raw:
        norm = _norm_issn(token)
        if len(norm) == 8:
            out.append(norm)
    # de-dup while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return unique


@dataclass
class WorkMatch:
    source: str
    score: int
    title: str
    year: int | None
    venue: str
    doi: str
    url: str
    issn: list[str]
    publisher: str
    cited_by_count: int | None
    work_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "score": self.score,
            "title": self.title,
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "url": self.url,
            "issn": self.issn,
            "publisher": self.publisher,
            "cited_by_count": self.cited_by_count,
            "type": self.work_type,
        }


class _CoreConferenceRanker:
    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path
        self._loaded = False
        self._rows: list[dict[str, str]] = []

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        path = Path(self.csv_path)
        if not self.csv_path or not path.exists():
            return
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self._rows = [dict(row) for row in reader if row]
        except Exception:
            self._rows = []

    def find_rank(self, venue: str) -> dict[str, Any] | None:
        self._load()
        venue = _clean_text(venue)
        if not venue or not self._rows:
            return None

        best: tuple[int, dict[str, str] | None] = (0, None)
        for row in self._rows:
            name = _clean_text(row.get("Conference") or row.get("Title") or row.get("Name") or "")
            if not name:
                continue
            score = _safe_ratio(_norm_title(venue), _norm_title(name))
            if score > best[0]:
                best = (score, row)

        score, row = best
        if not row or score < 85:
            return None

        rank = _clean_text(row.get("Rank") or row.get("CORE Rank") or row.get("Ranking") or "")
        return {"match_score": score, "rank": rank or None, "matched_name": _clean_text(row.get("Conference") or row.get("Title") or row.get("Name") or "")}


class _SjrJournalQuartileRanker:
    """Best-effort lookup of journal quartiles from a user-provided SJR CSV export.

    This intentionally avoids scraping. If the dataset is not configured, the caller should
    return a transparent "not_configured" status.
    """

    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path
        self._loaded = False
        self._rows: list[dict[str, str]] = []
        self._by_issn: dict[str, dict[str, str]] = {}

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        path = Path(self.csv_path)
        if not self.csv_path or not path.exists():
            return

        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                rows: list[dict[str, str]] = []
                by_issn: dict[str, dict[str, str]] = {}
                for row in reader:
                    if not row:
                        continue
                    normalized = {str(k or "").strip(): str(v or "").strip() for k, v in row.items()}
                    rows.append(normalized)

                    # attempt to index by ISSN variants
                    issn_raw = (
                        normalized.get("Issn")
                        or normalized.get("ISSN")
                        or normalized.get("issn")
                        or normalized.get("Issn1")
                        or normalized.get("Issn 1")
                        or ""
                    )
                    for issn in _split_issn_list(issn_raw):
                        by_issn.setdefault(issn, normalized)

                self._rows = rows
                self._by_issn = by_issn
        except Exception:
            self._rows = []
            self._by_issn = {}

    def find_quartile(self, venue: str, issn_list: list[str]) -> dict[str, Any] | None:
        self._load()
        venue = _clean_text(venue)
        if not venue or not (self._rows or self._by_issn):
            return None

        for issn in issn_list:
            row = self._by_issn.get(_norm_issn(issn))
            if not row:
                continue
            quartile = _clean_text(
                row.get("SJR Best Quartile")
                or row.get("Best Quartile")
                or row.get("Best_Quartile")
                or row.get("Quartile")
                or ""
            )
            sjr = _clean_text(row.get("SJR") or row.get("SJR score") or "")
            h_index = _clean_text(row.get("H index") or row.get("H-index") or row.get("H_Index") or "")
            return {
                "status": "verified_dataset",
                "matched_by": "issn",
                "match_score": 100,
                "quartile": quartile or None,
                "sjr": sjr or None,
                "h_index": h_index or None,
                "matched_title": _clean_text(row.get("Title") or row.get("title") or row.get("Journal") or ""),
            }

        # fall back to venue name match
        best: tuple[int, dict[str, str] | None] = (0, None)
        wanted = _norm_title(venue)
        for row in self._rows:
            name = _clean_text(row.get("Title") or row.get("title") or row.get("Journal") or row.get("Name") or "")
            if not name:
                continue
            score = _safe_ratio(wanted, _norm_title(name))
            if score > best[0]:
                best = (score, row)

        score, row = best
        if not row or score < 90:
            return None

        quartile = _clean_text(
            row.get("SJR Best Quartile")
            or row.get("Best Quartile")
            or row.get("Best_Quartile")
            or row.get("Quartile")
            or ""
        )
        sjr = _clean_text(row.get("SJR") or row.get("SJR score") or "")
        h_index = _clean_text(row.get("H index") or row.get("H-index") or row.get("H_Index") or "")
        return {
            "status": "verified_dataset",
            "matched_by": "venue",
            "match_score": score,
            "quartile": quartile or None,
            "sjr": sjr or None,
            "h_index": h_index or None,
            "matched_title": _clean_text(row.get("Title") or row.get("title") or row.get("Journal") or ""),
        }


def _infer_proceedings_platforms(venue: str, publisher: str) -> list[str]:
    text = f"{venue} {publisher}".lower()
    platforms: list[str] = []
    if "ieee" in text or "xplore" in text:
        platforms.append("IEEE Xplore")
    if "acm" in text or "sig" in text:
        platforms.append("ACM")
    if "springer" in text or "lncs" in text or "lecture notes" in text:
        platforms.append("Springer")
    if "elsevier" in text or "sciencedirect" in text:
        platforms.append("Elsevier")
    if "scopus" in text:
        platforms.append("Scopus")
    if "wos" in text or "web of science" in text:
        platforms.append("Web of Science")
    if "google scholar" in text:
        platforms.append("Google Scholar")
    # de-dup
    seen: set[str] = set()
    out: list[str] = []
    for p in platforms:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


class ResearchVerificationService:
    def __init__(self) -> None:
        self._core_ranker = _CoreConferenceRanker(settings.CORE_CONF_RANKINGS_CSV)
        self._sjr_ranker = _SjrJournalQuartileRanker(settings.SJR_JOURNAL_RANKS_CSV)

    def verify_publication(
        self,
        publication: dict[str, Any],
        candidate_name: str,
    ) -> dict[str, Any]:
        title = _clean_text(publication.get("title"))
        venue = _clean_text(publication.get("published_in"))
        year = _extract_year(publication.get("date"))
        author = _clean_text(publication.get("author"))
        co_author = _clean_text(publication.get("co-author") or publication.get("co_authors"))

        candidate_name_norm = candidate_name.strip().lower()
        names = [n for n in _split_names(author) + _split_names(co_author) if n]

        matches: list[WorkMatch] = []
        verify_enabled = _as_bool(os.getenv("RESEARCH_VERIFY_ENABLED"), default=settings.RESEARCH_VERIFY_ENABLED)
        if verify_enabled and title:
            matches.extend(self._search_openalex(title, year))
            matches.extend(self._search_crossref(title, year))
            if (os.getenv("SEMANTIC_SCHOLAR_API_KEY") or settings.SEMANTIC_SCHOLAR_API_KEY):
                matches.extend(self._search_semantic_scholar(title, year))

        matches.sort(key=lambda m: m.score, reverse=True)
        try:
            max_matches = int(os.getenv("RESEARCH_VERIFY_MAX_MATCHES") or settings.RESEARCH_VERIFY_MAX_MATCHES)
        except Exception:
            max_matches = settings.RESEARCH_VERIFY_MAX_MATCHES
        top_matches = matches[: max(0, max_matches)]
        best = top_matches[0] if top_matches else None

        authorship = self._infer_authorship(candidate_name_norm, names)
        venue_kind = self._infer_venue_kind(venue)

        core_rank = None
        if venue_kind == "conference":
            core_rank = self._core_ranker.find_rank(venue)

        # Journal quartile lookup (optional dataset).
        issn_from_cv = _split_issn_list(publication.get("issn") or publication.get("ISSN") or "")
        issn_from_best = _split_issn_list(best.issn) if best else []
        issn_list = issn_from_cv + [x for x in issn_from_best if x not in issn_from_cv]

        if settings.SJR_JOURNAL_RANKS_CSV or os.getenv("SJR_JOURNAL_RANKS_CSV"):
            sjr_result = self._sjr_ranker.find_quartile(venue=venue, issn_list=issn_list)
            quartile_status: dict[str, Any]
            if sjr_result:
                quartile_status = sjr_result
            else:
                quartile_status = {"status": "not_found", "reason": "no_match_in_sjr_dataset"}
        else:
            quartile_status = {"status": "not_configured", "reason": "SJR_JOURNAL_RANKS_CSV is not set"}

        publisher = (best.publisher if best else "") or ""
        platforms = _infer_proceedings_platforms(venue=venue, publisher=publisher)

        return {
            "status": "verified_external" if best else ("unverified_external" if verify_enabled else "verification_disabled"),
            "best_match": best.to_dict() if best else None,
            "matches": [m.to_dict() for m in top_matches],
            "authorship": authorship,
            "venue_kind": venue_kind,
            "conference_maturity": {"ordinal": _conference_ordinal(venue), "raw": venue} if venue_kind == "conference" else None,
            "core_rank": core_rank,
            "proceedings": {
                "publisher": publisher or None,
                "platforms": platforms,
            }
            if venue_kind == "conference"
            else None,
            "indexing": {
                "wos": self._wos_status(),
                "scopus": self._scopus_status(),
                "quartile": quartile_status,
            },
        }

    def _infer_venue_kind(self, venue: str) -> str:
        v = venue.lower()
        if re.search(r"\b(conf|conference|proceedings|proc\.|symposium|workshop)\b", v):
            return "conference"
        return "journal"

    def _infer_authorship(self, candidate_name_norm: str, names: list[str]) -> dict[str, Any]:
        if not candidate_name_norm or not names:
            return {"status": "unknown", "reason": "missing_candidate_name_or_authors"}

        # crude match: candidate name substring in any author token
        matched_index: int | None = None
        for i, n in enumerate(names):
            if candidate_name_norm in n.lower():
                matched_index = i
                break

        if matched_index is None:
            return {"status": "not_found", "authors_count": len(names)}

        role = "co_author"
        if matched_index == 0:
            role = "first_author"
        elif matched_index == len(names) - 1:
            role = "last_author"

        return {
            "status": "found",
            "role": role,
            "author_index": matched_index,
            "authors_count": len(names),
            "corresponding_author": None,
        }

    def _wos_status(self) -> dict[str, Any]:
        clarivate_key = os.getenv("CLARIVATE_API_KEY") or settings.CLARIVATE_API_KEY
        if not clarivate_key:
            return {"status": "not_configured", "reason": "CLARIVATE_API_KEY is not set"}
        return {"status": "configured", "note": "WoS/MJL verification requires a paid Clarivate API; wire your endpoint here."}

    def _scopus_status(self) -> dict[str, Any]:
        scopus_key = os.getenv("SCOPUS_API_KEY") or settings.SCOPUS_API_KEY
        if not scopus_key:
            return {"status": "not_configured", "reason": "SCOPUS_API_KEY is not set"}
        return {"status": "configured", "note": "Scopus verification requires Elsevier APIs; wire your endpoint here."}

    def _http_client(self) -> httpx.Client:
        timeout = None
        try:
            timeout = float(os.getenv("RESEARCH_VERIFY_TIMEOUT_SECONDS") or settings.RESEARCH_VERIFY_TIMEOUT_SECONDS)
        except Exception:
            timeout = settings.RESEARCH_VERIFY_TIMEOUT_SECONDS
        headers: dict[str, str] = {
            "User-Agent": "TALASH/0.1 (+https://example.invalid)",
            "Accept": "application/json",
        }
        return httpx.Client(timeout=timeout, headers=headers)

    def _search_openalex(self, title: str, year: int | None) -> list[WorkMatch]:
        params: dict[str, Any] = {"search": title, "per_page": 5}
        mailto = os.getenv("OPENALEX_MAILTO") or settings.OPENALEX_MAILTO
        if mailto:
            params["mailto"] = mailto

        url = "https://api.openalex.org/works"
        try:
            with self._http_client() as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json() or {}
        except Exception:
            return []

        wanted = _norm_title(title)
        results = payload.get("results") or []
        matches: list[WorkMatch] = []
        for item in results:
            item_title = _clean_text(item.get("display_name"))
            item_year = _as_int(item.get("publication_year"))
            score = _safe_ratio(wanted, _norm_title(item_title))
            if year and item_year and abs(item_year - year) > 1:
                score = int(score * 0.85)

            host = item.get("host_venue") or {}
            venue = _clean_text(host.get("display_name"))
            issn = host.get("issn") if isinstance(host.get("issn"), list) else []
            cited = _as_int(item.get("cited_by_count"))
            doi = _clean_text(item.get("doi"))
            url = _clean_text(item.get("id"))
            work_type = _clean_text(item.get("type"))
            publisher = _clean_text(host.get("publisher"))

            if score >= 80:
                matches.append(
                    WorkMatch(
                        source="openalex",
                        score=score,
                        title=item_title,
                        year=item_year,
                        venue=venue,
                        doi=doi,
                        url=url,
                        issn=[_clean_text(x) for x in issn if _clean_text(x)],
                        publisher=publisher,
                        cited_by_count=cited,
                        work_type=work_type,
                    )
                )
        return matches

    def _search_crossref(self, title: str, year: int | None) -> list[WorkMatch]:
        params: dict[str, Any] = {"query.title": title, "rows": 5}
        url = "https://api.crossref.org/works"
        try:
            with self._http_client() as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json() or {}
        except Exception:
            return []

        wanted = _norm_title(title)
        items = (((payload.get("message") or {}).get("items")) or [])
        matches: list[WorkMatch] = []
        for item in items:
            item_title = _clean_text(((item.get("title") or [])[:1] or [""])[0])
            item_year = None
            issued = (item.get("issued") or {}).get("date-parts")
            if isinstance(issued, list) and issued and isinstance(issued[0], list) and issued[0]:
                item_year = _as_int(issued[0][0])
            score = _safe_ratio(wanted, _norm_title(item_title))
            if year and item_year and abs(item_year - year) > 1:
                score = int(score * 0.85)

            venue = _clean_text(((item.get("container-title") or [])[:1] or [""])[0])
            issn = item.get("ISSN") if isinstance(item.get("ISSN"), list) else []
            doi = _clean_text(item.get("DOI"))
            url = _clean_text(item.get("URL"))
            publisher = _clean_text(item.get("publisher"))
            cited = _as_int(item.get("is-referenced-by-count"))
            work_type = _clean_text(item.get("type"))

            if score >= 80:
                matches.append(
                    WorkMatch(
                        source="crossref",
                        score=score,
                        title=item_title,
                        year=item_year,
                        venue=venue,
                        doi=doi,
                        url=url,
                        issn=[_clean_text(x) for x in issn if _clean_text(x)],
                        publisher=publisher,
                        cited_by_count=cited,
                        work_type=work_type,
                    )
                )
        return matches

    def _search_semantic_scholar(self, title: str, year: int | None) -> list[WorkMatch]:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": title, "limit": 5, "fields": "title,venue,year,citationCount,externalIds,authors,url"}
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY") or settings.SEMANTIC_SCHOLAR_API_KEY
        if not api_key:
            return []
        headers = {"x-api-key": api_key}

        try:
            with self._http_client() as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json() or {}
        except Exception:
            return []

        wanted = _norm_title(title)
        data = payload.get("data") or []
        matches: list[WorkMatch] = []
        for item in data:
            item_title = _clean_text(item.get("title"))
            item_year = _as_int(item.get("year"))
            score = _safe_ratio(wanted, _norm_title(item_title))
            if year and item_year and abs(item_year - year) > 1:
                score = int(score * 0.85)

            ext = item.get("externalIds") or {}
            doi = _clean_text(ext.get("DOI"))
            venue = _clean_text(item.get("venue"))
            cited = _as_int(item.get("citationCount"))
            url = _clean_text(item.get("url"))
            if not url:
                url = ""

            if score >= 80:
                matches.append(
                    WorkMatch(
                        source="semantic_scholar",
                        score=score,
                        title=item_title,
                        year=item_year,
                        venue=venue,
                        doi=doi,
                        url=url,
                        issn=[],
                        publisher="",
                        cited_by_count=cited,
                        work_type="",
                    )
                )
        return matches
