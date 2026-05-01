from __future__ import annotations

import math
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

from rapidfuzz import fuzz

from backend.app.services.email_service import EmailService
from backend.app.services.books_patents_verification_service import (
    BooksVerificationService,
    PatentsVerificationService,
)
from backend.app.services.research_verification_service import ResearchVerificationService


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _parse_year(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value)
    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _tokenize(text: str) -> list[str]:
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    tokens = [t for t in text.split() if t and t not in _STOPWORDS and len(t) > 2]
    return tokens


def _entropy(proportions: list[float]) -> float:
    total = 0.0
    for p in proportions:
        if p <= 0:
            continue
        total -= p * math.log(p)
    return total


def _normalize_entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    proportions = [value / total for value in counts.values()]
    ent = _entropy(proportions)
    max_ent = math.log(len(counts)) if len(counts) > 1 else 1.0
    return float(ent / max_ent) if max_ent > 0 else 0.0


def _degree_level(degree: str) -> str:
    d = degree.lower()
    if any(k in d for k in ("phd", "ph.d", "doctorate")):
        return "phd"
    if any(k in d for k in ("ms", "m.s", "msc", "m.sc", "mphil", "m phil", "mba")):
        return "pg"
    if any(k in d for k in ("bs", "b.s", "bsc", "b.sc", "be", "b.e", "beng", "undergraduate")):
        return "ug"
    if any(k in d for k in ("hssc", "intermediate", "fsc", "f.sc", "a level", "alevel")):
        return "hssc"
    if any(k in d for k in ("ssc", "matric", "o level", "olevel", "sse")):
        return "ssc"
    return "other"


def _parse_score_to_percent(raw: Any) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        return {"raw": "", "percent": None, "scale": None}
    numeric = re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))
    if not numeric:
        return {"raw": text, "percent": None, "scale": None}
    score = float(numeric[0])

    if "%" in text:
        scale = 100.0
    elif score <= 4.0:
        scale = 4.0
    elif score <= 5.0:
        scale = 5.0
    elif score <= 10.0:
        scale = 10.0
    else:
        scale = 100.0

    percent = round((score / scale) * 100.0, 2) if scale else None
    return {"raw": text, "percent": percent, "scale": scale}


def _parse_score_fields(entry: dict[str, Any]) -> dict[str, Any]:
    """Parse best-effort score percent from multiple possible CV fields."""
    percent_field = entry.get("percentage")
    if percent_field:
        parsed = _parse_score_to_percent(str(percent_field))
        if parsed.get("percent") is not None:
            parsed["source"] = "percentage"
            return parsed

    cgpa = entry.get("cgpa_or_score")
    parsed = _parse_score_to_percent(cgpa)
    parsed["source"] = "cgpa_or_score" if cgpa else ""
    scale_hint = str(entry.get("cgpa_scale") or "").strip()
    if scale_hint:
        parsed["scale_hint"] = scale_hint
    return parsed


def _year_to_date(year: int | None, is_end: bool) -> date | None:
    if not year:
        return None
    return date(year, 12, 31) if is_end else date(year, 1, 1)


def _intervals_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return a_start <= b_end and a_end >= b_start


def _research_verify_enabled() -> bool:
    value = os.getenv("RESEARCH_VERIFY_ENABLED", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_duration_range(text: str) -> tuple[date | None, date | None]:
    if not text:
        return None, None

    text = text.replace("–", "-")
    parts = re.split(r"\s+-\s+|\s+to\s+", text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 1:
        return _parse_date_token(parts[0], is_end=False), None
    return _parse_date_token(parts[0], is_end=False), _parse_date_token(parts[1], is_end=True)


def _parse_date_token(token: str, is_end: bool) -> date | None:
    import calendar

    if not token:
        return None
    cleaned = token.strip().lower()
    if not cleaned:
        return None
    if cleaned in {"present", "current", "now", "to date"}:
        return date.today() if is_end else None

    year = _parse_year(cleaned)
    if year:
        return date(year, 12, 31) if is_end else date(year, 1, 1)

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d-%B-%Y",
        "%d %B %Y",
        "%b-%Y",
        "%b %Y",
        "%B %Y",
        "%m-%Y",
        "%m/%Y",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(token.strip(), fmt)
            if fmt in {"%b-%Y", "%b %Y", "%B %Y", "%m-%Y", "%m/%Y"}:
                month = parsed.month
                year = parsed.year
                if is_end:
                    last_day = calendar.monthrange(year, month)[1]
                    return date(year, month, last_day)
                return date(year, month, 1)
            return parsed.date()
        except ValueError:
            continue
    return None


class AnalysisService:
    def build_full_report(self, candidate_doc: dict[str, Any]) -> dict[str, Any]:
        parsed = candidate_doc.get("parsed_json")
        parsed_obj = parsed
        if isinstance(parsed_obj, str):
            try:
                import json

                parsed_obj = json.loads(parsed_obj)
            except Exception:
                parsed_obj = {}
        parsed_obj = _as_dict(parsed_obj)
        raw_text = str(candidate_doc.get("raw_text") or "")

        educational = self._analyze_education(parsed_obj)
        professional = self._analyze_professional(parsed_obj, educational=educational)
        research = self._analyze_research(parsed_obj)
        skills = self._analyze_skills_alignment(parsed_obj, raw_text)
        supervision = self._analyze_supervision(parsed_obj)
        books = self._analyze_books(parsed_obj)
        patents = self._analyze_patents(parsed_obj)

        missing_fields = self._missing_fields(parsed_obj)
        email_draft = EmailService().draft_missing_info_email({**candidate_doc, "parsed_json": parsed_obj})

        summary = self._build_summary(
            candidate_doc,
            educational,
            professional,
            research,
            skills,
            supervision,
            books,
            patents,
            missing_fields,
        )

        return {
            "candidate_id": candidate_doc.get("id"),
            "educational": educational,
            "professional": professional,
            "research": research,
            "supervision": supervision,
            "books": books,
            "patents": patents,
            "skills_alignment": skills,
            "missing_info": {
                "fields": missing_fields,
                "email_draft": email_draft,
            },
            "summary": summary,
        }

    def generate_summary(self, candidate_doc: dict[str, Any]) -> dict[str, str]:
        report = self.build_full_report(candidate_doc)
        status = "complete" if len(report.get("missing_info", {}).get("fields", [])) == 0 else "missing_info"
        message = report.get("summary", {}).get("text") or ""
        return {"summary": message, "status": status}

    def _missing_fields(self, parsed_json: dict[str, Any]) -> list[str]:
        missing = parsed_json.get("missing_info")
        if isinstance(missing, list):
            return [str(item).strip() for item in missing if str(item).strip()]
        if isinstance(missing, dict) and isinstance(missing.get("missing_fields"), list):
            return [str(item).strip() for item in missing["missing_fields"] if str(item).strip()]
        return []

    def _analyze_education(self, parsed_json: dict[str, Any]) -> dict[str, Any]:
        education = [item for item in _as_list(parsed_json.get("education")) if isinstance(item, dict)]
        records: list[dict[str, Any]] = []
        for entry in education:
            degree = str(entry.get("degree") or "").strip()
            level = _degree_level(degree)
            score = _parse_score_fields(entry)
            passing_year = _parse_year(entry.get("passing_year")) or _parse_year(entry.get("end_year"))
            rankings = _as_dict(entry.get("university_rankings"))
            the_rank = _as_dict(rankings.get("the")).get("rank")
            qs_rank = _as_dict(rankings.get("qs")).get("rank")

            start_year = _parse_year(entry.get("start_year"))
            end_year = _parse_year(entry.get("end_year")) or passing_year

            estimated = False
            if start_year is None and end_year is not None and level in {"ug", "pg", "phd"}:
                # Best-effort estimate if CV only provides passing year.
                delta = 4 if level == "ug" else 2 if level == "pg" else 4
                start_year = max(1900, end_year - delta)
                estimated = True

            records.append(
                {
                    "degree": degree,
                    "level": level,
                    "institution": str(entry.get("institution") or "").strip(),
                    "specialization": str(entry.get("specialization") or "").strip(),
                    "board_or_institution": str(entry.get("board_or_institution") or "").strip(),
                    "start_year": start_year,
                    "end_year": end_year,
                    "passing_year": passing_year,
                    "score_raw": score["raw"],
                    "score_percent": score["percent"],
                    "institution_rank": _as_dict(entry.get("university_info")).get("rank"),
                    "institution_rankings": {"the": the_rank, "qs": qs_rank},
                    "date_range_estimated": estimated,
                }
            )

        def sort_key(item: dict[str, Any]) -> int:
            return item.get("end_year") or item.get("passing_year") or 9999

        records.sort(key=sort_key)

        # Stage presence (SSE/SSC and HSSC are typically required in Talash workflows).
        has_ssc = any(r["level"] == "ssc" for r in records)
        has_hssc = any(r["level"] == "hssc" for r in records)
        has_ug = any(r["level"] == "ug" for r in records)
        has_pg = any(r["level"] == "pg" for r in records)
        has_phd = any(r["level"] == "phd" for r in records)

        # Educational gaps between stages (year-based).
        gaps: list[dict[str, Any]] = []
        for prev, cur in zip(records, records[1:]):
            prev_year = prev.get("end_year") or prev.get("passing_year")
            cur_year = cur.get("start_year") or cur.get("end_year") or cur.get("passing_year")
            if prev_year and cur_year and cur_year - prev_year > 1:
                gaps.append({"from": prev_year, "to": cur_year, "gap_years": cur_year - prev_year})

        # Education progression (simple ordering checks).
        level_order = {"ssc": 1, "hssc": 2, "ug": 3, "pg": 4, "phd": 5, "other": 0}
        progression_ok = True
        for prev, cur in zip(records, records[1:]):
            if level_order.get(cur["level"], 0) < level_order.get(prev["level"], 0):
                progression_ok = False
                break

        # Trend and simple strength score.
        score_points = [r["score_percent"] for r in records if isinstance(r.get("score_percent"), (int, float))]
        avg_score = round(sum(score_points) / len(score_points), 2) if score_points else None
        highest = None
        for record in records:
            if highest is None or level_order.get(record["level"], 0) > level_order.get(highest["level"], 0):
                highest = record

        notes: list[str] = []
        if gaps:
            notes.append(f"Detected {len(gaps)} education gap(s) between stages.")
        if avg_score is None:
            notes.append("Insufficient academic scores to compute a normalized trend.")
        if not has_ssc:
            notes.append("SSC/SSE (or equivalent) record not found in extracted education entries.")
        if not has_hssc:
            notes.append("HSSC/FSc/A-level (or equivalent) record not found in extracted education entries.")
        if not progression_ok and records:
            notes.append("Education levels appear out-of-order; verify extraction (e.g., missing years/labels).")

        institution_quality: list[dict[str, Any]] = []
        for record in records:
            ranks = _as_dict(record.get("institution_rankings"))
            if ranks.get("the") or ranks.get("qs"):
                institution_quality.append(
                    {
                        "institution": record.get("institution") or "",
                        "level": record.get("level"),
                        "rankings": ranks,
                    }
                )

        return {
            "records": records,
            "average_score_percent": avg_score,
            "highest_level": highest.get("level") if highest else None,
            "education_gaps": gaps,
            "progression_ok": progression_ok,
            "stage_presence": {
                "ssc": has_ssc,
                "hssc": has_hssc,
                "ug": has_ug,
                "pg": has_pg,
                "phd": has_phd,
            },
            "institution_quality": institution_quality,
            "notes": notes,
        }

    def _analyze_professional(self, parsed_json: dict[str, Any], educational: dict[str, Any] | None = None) -> dict[str, Any]:
        experience = [item for item in _as_list(parsed_json.get("experience")) if isinstance(item, dict)]
        intervals: list[dict[str, Any]] = []
        for entry in experience:
            duration = str(entry.get("duration_of_employment") or "").strip()
            start = _parse_date_token(str(entry.get("start_date") or ""), is_end=False) or None
            end = _parse_date_token(str(entry.get("end_date") or ""), is_end=True) or None
            if duration and (start is None and end is None):
                start, end = _parse_duration_range(duration)
            if start is None and end is not None:
                start = date(end.year, 1, 1)
            if end is None and start is not None:
                end = date.today()

            intervals.append(
                {
                    "role": str(entry.get("role") or "").strip(),
                    "organization": str(entry.get("organization") or "").strip(),
                    "location": str(entry.get("location") or "").strip(),
                    "employment_type": str(entry.get("employment_type") or "").strip(),
                    "start_date": start.isoformat() if start else None,
                    "end_date": end.isoformat() if end else None,
                }
            )

        def dt(item: dict[str, Any], key: str) -> date | None:
            value = item.get(key)
            if not value:
                return None
            try:
                return date.fromisoformat(value)
            except Exception:
                return None

        intervals.sort(key=lambda i: dt(i, "start_date") or date.max)

        overlaps: list[dict[str, Any]] = []
        for i in range(len(intervals)):
            a_start = dt(intervals[i], "start_date")
            a_end = dt(intervals[i], "end_date")
            if not a_start or not a_end:
                continue
            for j in range(i + 1, len(intervals)):
                b_start = dt(intervals[j], "start_date")
                b_end = dt(intervals[j], "end_date")
                if not b_start or not b_end:
                    continue
                if b_start <= a_end and b_end >= a_start:
                    overlaps.append(
                        {
                            "a": {"role": intervals[i]["role"], "org": intervals[i]["organization"]},
                            "b": {"role": intervals[j]["role"], "org": intervals[j]["organization"]},
                            "overlap": {
                                "start": max(a_start, b_start).isoformat(),
                                "end": min(a_end, b_end).isoformat(),
                            },
                        }
                    )

        gaps: list[dict[str, Any]] = []
        for prev, cur in zip(intervals, intervals[1:]):
            prev_end = dt(prev, "end_date")
            cur_start = dt(cur, "start_date")
            if not prev_end or not cur_start:
                continue
            if cur_start > prev_end:
                delta = (cur_start - prev_end).days
                if delta >= 30:
                    gaps.append({"from": prev_end.isoformat(), "to": cur_start.isoformat(), "gap_days": delta})

        education_employment_overlaps: list[dict[str, Any]] = []
        education_gap_justification: list[dict[str, Any]] = []
        if educational:
            edu_records = [r for r in _as_list(educational.get("records")) if isinstance(r, dict)]
            edu_intervals: list[dict[str, Any]] = []
            for r in edu_records:
                start = _year_to_date(r.get("start_year"), is_end=False) or _year_to_date(r.get("passing_year"), is_end=False)
                end = _year_to_date(r.get("end_year"), is_end=True) or _year_to_date(r.get("passing_year"), is_end=True)
                if not start or not end:
                    continue
                edu_intervals.append(
                    {
                        "level": r.get("level"),
                        "degree": r.get("degree"),
                        "institution": r.get("institution"),
                        "estimated": bool(r.get("date_range_estimated")),
                        "start": start,
                        "end": end,
                    }
                )

            for edu in edu_intervals:
                for job in intervals:
                    js = dt(job, "start_date")
                    je = dt(job, "end_date")
                    if not js or not je:
                        continue
                    if _intervals_overlap(edu["start"], edu["end"], js, je):
                        education_employment_overlaps.append(
                            {
                                "education": {
                                    "level": edu["level"],
                                    "degree": edu["degree"],
                                    "institution": edu["institution"],
                                    "estimated": edu["estimated"],
                                    "start": edu["start"].isoformat(),
                                    "end": edu["end"].isoformat(),
                                },
                                "employment": {
                                    "role": job.get("role"),
                                    "organization": job.get("organization"),
                                    "employment_type": job.get("employment_type"),
                                    "start": js.isoformat(),
                                    "end": je.isoformat(),
                                },
                            }
                        )

            # Justify education gaps using employment coverage.
            for gap in _as_list(educational.get("education_gaps")):
                if not isinstance(gap, dict):
                    continue
                start = _year_to_date(gap.get("from"), is_end=True)
                end = _year_to_date(gap.get("to"), is_end=False)
                if not start or not end:
                    continue
                covered_by = []
                for job in intervals:
                    js = dt(job, "start_date")
                    je = dt(job, "end_date")
                    if not js or not je:
                        continue
                    if _intervals_overlap(start, end, js, je):
                        covered_by.append({"role": job.get("role"), "organization": job.get("organization")})
                education_gap_justification.append(
                    {
                        "gap": gap,
                        "covered_by_employment": covered_by,
                        "status": "justified" if covered_by else "unjustified",
                    }
                )

        notes: list[str] = []
        if overlaps:
            notes.append(f"Detected {len(overlaps)} overlapping employment interval(s).")
        if not intervals:
            notes.append("No experience entries found.")
        if education_employment_overlaps:
            notes.append("Education/employment overlap detected; verify full-time vs part-time status.")

        return {
            "positions": intervals,
            "overlaps": overlaps,
            "gaps": gaps,
            "education_employment_overlaps": education_employment_overlaps,
            "education_gap_justification": education_gap_justification,
            "notes": notes,
        }

    def _analyze_supervision(self, parsed_json: dict[str, Any]) -> dict[str, Any]:
        supervision = _as_dict(parsed_json.get("supervision"))
        main = [s for s in _as_list(supervision.get("main_supervisor_students")) if isinstance(s, dict)]
        co = [s for s in _as_list(supervision.get("co_supervisor_students")) if isinstance(s, dict)]

        counts = {
            "main_supervisor_students": len(main),
            "co_supervisor_students": len(co),
            "total": len(main) + len(co),
        }
        notes: list[str] = []
        if counts["total"] == 0:
            notes.append("No supervision records found in extracted data.")
        return {"counts": counts, "main_supervisor_students": main, "co_supervisor_students": co, "notes": notes}

    def _analyze_books(self, parsed_json: dict[str, Any]) -> dict[str, Any]:
        books = [b for b in _as_list(parsed_json.get("books")) if isinstance(b, dict)]
        verifier = BooksVerificationService()
        rows: list[dict[str, Any]] = []
        verified = 0
        for book in books:
            record = {
                "title": str(book.get("title") or "").strip(),
                "year": _parse_year(book.get("year")),
                "publisher": str(book.get("publisher") or "").strip(),
                "authors": str(book.get("authors") or "").strip(),
                "isbn": str(book.get("isbn") or "").strip(),
                "link": str(book.get("link") or "").strip(),
                "verification": {"status": "verification_disabled"},
            }
            if _research_verify_enabled():
                record["verification"] = verifier.verify_book(book)
            if record["verification"].get("status") == "verified":
                verified += 1
            rows.append(record)
        return {"items": rows, "verification_summary": {"total": len(rows), "verified": verified}}

    def _analyze_patents(self, parsed_json: dict[str, Any]) -> dict[str, Any]:
        patents = [p for p in _as_list(parsed_json.get("patents")) if isinstance(p, dict)]
        verifier = PatentsVerificationService()
        rows: list[dict[str, Any]] = []
        verified = 0
        for patent in patents:
            record = {
                "title": str(patent.get("title") or "").strip(),
                "patent_number": str(patent.get("patent_number") or "").strip(),
                "date": str(patent.get("date") or "").strip(),
                "year": _parse_year(patent.get("year")) or _parse_year(patent.get("date")),
                "status": str(patent.get("status") or "").strip(),
                "country": str(patent.get("country") or "").strip(),
                "inventors": str(patent.get("inventors") or "").strip(),
                "link": str(patent.get("link") or "").strip(),
                "verification": {"status": "verification_disabled"},
            }
            if _research_verify_enabled():
                record["verification"] = verifier.verify_patent(patent)
            if record["verification"].get("status") == "verified":
                verified += 1
            rows.append(record)
        return {"items": rows, "verification_summary": {"total": len(rows), "verified": verified}}

    def analyze_job_role_alignment(self, candidate_doc: dict[str, Any], job_description: str) -> dict[str, Any]:
        parsed = candidate_doc.get("parsed_json")
        parsed_obj = parsed
        if isinstance(parsed_obj, str):
            try:
                import json

                parsed_obj = json.loads(parsed_obj)
            except Exception:
                parsed_obj = {}
        parsed_obj = _as_dict(parsed_obj)
        raw_text = str(candidate_doc.get("raw_text") or "")
        return self._analyze_job_alignment(parsed_obj, raw_text, job_description)

    def _analyze_job_alignment(self, parsed_json: dict[str, Any], raw_text: str, job_description: str) -> dict[str, Any]:
        job_text = str(job_description or "").strip()
        if not job_text:
            return {"status": "no_job_description", "matches": []}

        skills_alignment = self._analyze_skills_alignment(parsed_json, raw_text)
        skill_rows = [r for r in _as_list(skills_alignment.get("skills")) if isinstance(r, dict)]

        matches: list[dict[str, Any]] = []
        for row in skill_rows:
            skill = str(row.get("skill") or "").strip()
            if not skill:
                continue
            score = fuzz.token_set_ratio(skill.lower(), job_text.lower())
            matches.append(
                {
                    "skill": skill,
                    "job_match_score": score,
                    "evidence_strength": row.get("strength"),
                }
            )

        matches.sort(key=lambda m: m.get("job_match_score") or 0, reverse=True)
        top = matches[:25]
        coverage = sum(1 for m in top if (m.get("job_match_score") or 0) >= 70)
        return {
            "status": "ok",
            "job_description_chars": len(job_text),
            "top_matches": top,
            "coverage": {"skills_considered": len(matches), "skills_matched_70_plus": coverage},
        }

    def _analyze_research(self, parsed_json: dict[str, Any]) -> dict[str, Any]:
        publications = [item for item in _as_list(parsed_json.get("publications")) if isinstance(item, dict)]
        personal = _as_dict(parsed_json.get("personal_info"))
        candidate_name = str(personal.get("full_name") or "").strip().lower()

        verifier = ResearchVerificationService()

        journal_papers: list[dict[str, Any]] = []
        conference_papers: list[dict[str, Any]] = []
        coauthors: list[str] = []
        topic_counts: Counter[str] = Counter()

        topic_map = {
            "machine learning": ["machine", "learning", "ml"],
            "computer vision": ["vision", "image", "cnn", "segmentation", "detection"],
            "nlp": ["nlp", "language", "text", "transformer", "bert"],
            "networks": ["network", "routing", "wireless", "iot"],
            "cybersecurity": ["security", "malware", "attack", "encryption"],
            "software engineering": ["software", "testing", "requirements", "devops"],
            "data analytics": ["data", "analytics", "mining", "visualization"],
        }

        def classify_topic(title: str) -> str:
            tokens = set(_tokenize(title))
            best = "other"
            best_score = 0
            for topic, keys in topic_map.items():
                score = sum(1 for k in keys if k in tokens)
                if score > best_score:
                    best_score = score
                    best = topic
            return best

        for pub in publications:
            title = str(pub.get("title") or "").strip()
            venue = str(pub.get("published_in") or "").strip()
            authors = str(pub.get("author") or "").strip()
            co = str(pub.get("co-author") or pub.get("co_authors") or "").strip()
            year = _parse_year(pub.get("date"))

            venue_type = "conference" if re.search(r"\b(conf|conference|proceedings|proc\.)\b", venue.lower()) else "journal"
            topic = classify_topic(title)
            topic_counts[topic] += 1

            # Co-author list (string-based; CV formats vary).
            co_list = [
                n.strip()
                for n in re.split(r",|;|\band\b", co, flags=re.IGNORECASE)
                if n.strip()
            ]
            for name in co_list:
                cleaned = re.sub(r"[*\d]", "", name).strip()
                if cleaned and (not candidate_name or candidate_name not in cleaned.lower()):
                    coauthors.append(cleaned)

            record = {
                "title": title,
                "venue": venue,
                "year": year,
                "authors": authors,
                "co_authors": co_list,
                "topic": topic,
                "verification": {
                    "status": "unverified_offline",
                    "impact_factor": pub.get("impact_factor") or None,
                },
            }

            # External verification (optional via env toggle; failures are swallowed inside the service).
            try:
                external = verifier.verify_publication(pub, candidate_name=candidate_name)
                record["verification"].update(external)
            except Exception:
                record["verification"].update({"status": "verification_error"})

            if venue_type == "conference":
                conference_papers.append(record)
            else:
                journal_papers.append(record)

        co_counts = Counter([c for c in coauthors if c])
        diversity_score = round(_normalize_entropy(topic_counts), 3) if topic_counts else 0.0

        verified = 0
        disabled = 0
        for row in journal_papers + conference_papers:
            status = _as_dict(row.get("verification")).get("status")
            if status == "verified_external":
                verified += 1
            if status == "verification_disabled":
                disabled += 1

        return {
            "journal_papers": journal_papers,
            "conference_papers": conference_papers,
            "verification_summary": {
                "total": len(journal_papers) + len(conference_papers),
                "verified_external": verified,
                "verification_disabled": disabled,
            },
            "topic_variability": {
                "topic_counts": dict(topic_counts),
                "diversity_score": diversity_score,
            },
            "coauthor_analysis": {
                "unique_coauthors": len(co_counts),
                "top_coauthors": [
                    {"name": name, "count": count}
                    for name, count in co_counts.most_common(10)
                ],
            },
        }

    def _analyze_skills_alignment(self, parsed_json: dict[str, Any], raw_text: str) -> dict[str, Any]:
        skills = parsed_json.get("skills")
        if isinstance(skills, str):
            skills_list = [s.strip() for s in re.split(r",|;|\n", skills) if s.strip()]
        else:
            skills_list = [str(s).strip() for s in _as_list(skills) if str(s).strip()]

        experience = [item for item in _as_list(parsed_json.get("experience")) if isinstance(item, dict)]
        publications = [item for item in _as_list(parsed_json.get("publications")) if isinstance(item, dict)]
        education = [item for item in _as_list(parsed_json.get("education")) if isinstance(item, dict)]

        evidence_corpus: list[str] = [raw_text]
        evidence_corpus.extend([str(e.get("role") or "") for e in experience])
        evidence_corpus.extend([str(e.get("organization") or "") for e in experience])
        evidence_corpus.extend([str(p.get("title") or "") for p in publications])
        evidence_corpus.extend([str(p.get("published_in") or "") for p in publications])
        evidence_corpus.extend([str(ed.get("degree") or "") for ed in education])
        evidence_corpus.extend([str(ed.get("specialization") or "") for ed in education])
        evidence_corpus = [c for c in evidence_corpus if c]

        skill_rows: list[dict[str, Any]] = []
        for skill in skills_list:
            best = 0
            best_source = ""
            for chunk in evidence_corpus:
                score = fuzz.partial_ratio(skill.lower(), chunk.lower())
                if score > best:
                    best = score
                    best_source = chunk
            strength = "unsupported"
            if best >= 90:
                strength = "strong"
            elif best >= 75:
                strength = "partial"
            elif best >= 60:
                strength = "weak"
            skill_rows.append(
                {
                    "skill": skill,
                    "evidence_score": best,
                    "strength": strength,
                    "best_evidence_snippet": best_source[:160] if best_source else "",
                }
            )

        counts = Counter([row["strength"] for row in skill_rows])
        return {
            "skills": skill_rows,
            "counts": dict(counts),
        }

    def _build_summary(
        self,
        candidate_doc: dict[str, Any],
        educational: dict[str, Any],
        professional: dict[str, Any],
        research: dict[str, Any],
        skills: dict[str, Any],
        supervision: dict[str, Any],
        books: dict[str, Any],
        patents: dict[str, Any],
        missing_fields: list[str],
    ) -> dict[str, Any]:
        name = candidate_doc.get("full_name") or _as_dict(candidate_doc.get("parsed_json")).get("personal_info", {}).get("full_name")
        name = name or candidate_doc.get("source_file") or "Candidate"

        strengths: list[str] = []
        concerns: list[str] = []

        avg = educational.get("average_score_percent")
        if isinstance(avg, (int, float)):
            strengths.append(f"Average normalized academic score: {avg}.")
        if educational.get("education_gaps"):
            concerns.append("Education gaps detected between stages.")

        if professional.get("overlaps"):
            concerns.append("Overlapping employment intervals detected; verify timeline.")
        if professional.get("gaps"):
            concerns.append("Professional gaps detected; may need justification.")
        if professional.get("education_employment_overlaps"):
            concerns.append("Education/employment overlap detected; verify eligibility requirements.")

        pubs = len(research.get("journal_papers", [])) + len(research.get("conference_papers", []))
        if pubs:
            strengths.append(f"Publications listed: {pubs} (unverified indexing in current build).")

        if _as_dict(supervision.get("counts")).get("total"):
            strengths.append(f"Supervision records listed: {supervision['counts']['total']}.")

        if _as_dict(books.get("verification_summary")).get("total"):
            strengths.append(f"Books listed: {books['verification_summary']['total']}.")
        if _as_dict(patents.get("verification_summary")).get("total"):
            strengths.append(f"Patents listed: {patents['verification_summary']['total']}.")

        strong_skills = sum(1 for s in skills.get("skills", []) if s.get("strength") == "strong")
        if strong_skills:
            strengths.append(f"Strong evidence for {strong_skills} listed skill(s).")

        if missing_fields:
            concerns.append(f"Missing/incomplete fields detected: {len(missing_fields)}.")

        text_parts = [f"Profile summary for {name}."]
        if strengths:
            text_parts.append("Strengths: " + " ".join(strengths))
        if concerns:
            text_parts.append("Concerns: " + " ".join(concerns))
        if not strengths and not concerns:
            text_parts.append("Insufficient structured data extracted to produce a strong assessment.")

        return {
            "strengths": strengths,
            "concerns": concerns,
            "text": "\n".join(text_parts),
        }

