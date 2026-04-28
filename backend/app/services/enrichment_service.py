import json
import re

from rapidfuzz import fuzz, process

from backend.app.core.config import settings

class EnrichmentService:
    def __init__(self):
        pass

    def detect_missing_info(self, parsed_json: dict) -> list[str]:
        missing_fields: list[str] = []
        info = parsed_json.get("personal_info", {})

        if not info.get("full_name"):
            missing_fields.append("personal_info.full_name")
        if not info.get("email"):
            missing_fields.append("personal_info.email")
        if not info.get("phone"):
            missing_fields.append("personal_info.phone")
        if not info.get("location"):
            missing_fields.append("personal_info.location")

        if not parsed_json.get("education"):
            missing_fields.append("education")
        if not parsed_json.get("experience"):
            missing_fields.append("experience")
        if not parsed_json.get("skills"):
            missing_fields.append("skills")
        # Publications/patents/books/supervision are often legitimately empty.
        # However, if they are present, we still want to flag missing critical metadata.

        publications_entries = parsed_json.get("publications") or []
        if isinstance(publications_entries, list):
            for index, pub in enumerate(publications_entries):
                if not isinstance(pub, dict):
                    continue
                if not str(pub.get("title") or "").strip():
                    missing_fields.append(f"publications[{index}].title")
                if not str(pub.get("published_in") or "").strip():
                    missing_fields.append(f"publications[{index}].published_in")
                if not str(pub.get("date") or pub.get("year") or "").strip():
                    missing_fields.append(f"publications[{index}].date")
                if not str(pub.get("author") or "").strip() and not str(pub.get("co-author") or pub.get("co_authors") or "").strip():
                    missing_fields.append(f"publications[{index}].authors")

        books_entries = parsed_json.get("books") or []
        if isinstance(books_entries, list):
            for index, book in enumerate(books_entries):
                if not isinstance(book, dict):
                    continue
                if not str(book.get("title") or book.get("book_name") or "").strip():
                    missing_fields.append(f"books[{index}].title")
                if not str(book.get("isbn") or "").strip():
                    missing_fields.append(f"books[{index}].isbn")

        patents_entries = parsed_json.get("patents") or []
        if isinstance(patents_entries, list):
            for index, patent in enumerate(patents_entries):
                if not isinstance(patent, dict):
                    continue
                if not str(patent.get("patent_number") or "").strip() and not str(patent.get("title") or "").strip():
                    missing_fields.append(f"patents[{index}].patent_number")

        # Finer-grained checks (best-effort; CVs vary widely).
        education_entries = parsed_json.get("education") or []
        if isinstance(education_entries, list):
            for index, entry in enumerate(education_entries):
                if not isinstance(entry, dict):
                    continue
                degree = str(entry.get("degree") or "").strip()
                institution = str(entry.get("institution") or "").strip()
                if not degree:
                    missing_fields.append(f"education[{index}].degree")
                if not institution:
                    missing_fields.append(f"education[{index}].institution")
                if not str(entry.get("passing_year") or "").strip() and not str(entry.get("end_year") or "").strip():
                    missing_fields.append(f"education[{index}].passing_year")
                if not str(entry.get("cgpa_or_score") or "").strip():
                    missing_fields.append(f"education[{index}].cgpa_or_score")

        experience_entries = parsed_json.get("experience") or []
        if isinstance(experience_entries, list):
            for index, entry in enumerate(experience_entries):
                if not isinstance(entry, dict):
                    continue
                if not str(entry.get("role") or "").strip():
                    missing_fields.append(f"experience[{index}].role")
                if not str(entry.get("organization") or "").strip():
                    missing_fields.append(f"experience[{index}].organization")
                if not str(entry.get("duration_of_employment") or "").strip() and not (
                    str(entry.get("start_date") or "").strip() or str(entry.get("end_date") or "").strip()
                ):
                    missing_fields.append(f"experience[{index}].duration_of_employment")

        return missing_fields

    def _parse_date_token(self, token: str, is_end: bool):
        import calendar
        from datetime import date, datetime

        if not token:
            return None

        cleaned = token.strip().lower()
        if not cleaned:
            return None

        if cleaned in {"present", "current", "now", "to date"}:
            return date.today() if is_end else None

        if cleaned.isdigit() and len(cleaned) == 4:
            year = int(cleaned)
            if is_end:
                return date(year, 12, 31)
            return date(year, 1, 1)

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
                    year = parsed.year
                    month = parsed.month
                    if is_end:
                        last_day = calendar.monthrange(year, month)[1]
                        return date(year, month, last_day)
                    return date(year, month, 1)
                return parsed.date()
            except ValueError:
                continue

        return None

    def _parse_duration_range(self, text: str):
        import re

        if not text:
            return None, None

        normalized = text.replace("–", "-")
        parts = re.split(r"\s+-\s+|\s+to\s+", normalized, maxsplit=1)
        if len(parts) == 1:
            start = self._parse_date_token(parts[0], is_end=False)
            return start, None

        start = self._parse_date_token(parts[0], is_end=False)
        end = self._parse_date_token(parts[1], is_end=True)
        return start, end

    def _merge_intervals(self, intervals):
        if not intervals:
            return []

        intervals = sorted(intervals, key=lambda item: item[0])
        merged = [intervals[0]]
        for start, end in intervals[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return merged

    def _subtract_intervals(self, gaps, coverage):
        from datetime import timedelta

        if not gaps:
            return []
        if not coverage:
            return gaps

        coverage = self._merge_intervals(coverage)
        result = []
        for gap_start, gap_end in gaps:
            cursor = gap_start
            for cover_start, cover_end in coverage:
                if cover_end < cursor:
                    continue
                if cover_start > gap_end:
                    break
                if cover_start > cursor:
                    result.append((cursor, min(gap_end, cover_start - timedelta(days=1))))
                if cover_end >= gap_end:
                    cursor = None
                    break
                cursor = cover_end + timedelta(days=1)
            if cursor and cursor <= gap_end:
                result.append((cursor, gap_end))
        return result

    def _build_gap_intervals(self, parsed_json):
        from datetime import date, timedelta

        experience_entries = parsed_json.get("experience", [])
        education_entries = parsed_json.get("education", [])

        experiences = []
        for entry in experience_entries:
            start, end = self._parse_duration_range(entry.get("duration_of_employment", ""))
            experiences.append({"start": start, "end": end})

        def sort_key(item):
            return item["start"] or item["end"] or date.max

        experiences.sort(key=sort_key)

        last_known_end = None
        for item in experiences:
            if item["start"] is None and last_known_end:
                item["start"] = last_known_end
            if item["end"] is None:
                item["end"] = None
            if item["end"]:
                last_known_end = item["end"]

        for index, item in enumerate(experiences):
            if item["end"] is None:
                next_start = None
                for future in experiences[index + 1 :]:
                    if future["start"]:
                        next_start = future["start"]
                        break
                item["end"] = next_start or date.today()

            if item["start"] and item["end"] and item["end"] < item["start"]:
                item["start"], item["end"] = item["end"], item["start"]

        experience_intervals = [
            (item["start"], item["end"])
            for item in experiences
            if item["start"] and item["end"]
        ]
        experience_intervals = self._merge_intervals(experience_intervals)

        education_intervals = []
        for entry in education_entries:
            passing_date = self._parse_date_token(entry.get("passing_year", ""), is_end=True)
            if passing_date:
                start_of_year = date(passing_date.year, 1, 1)
                end_of_year = date(passing_date.year, 12, 31)
                education_intervals.append((start_of_year, end_of_year))
        education_intervals = self._merge_intervals(education_intervals)

        gaps = []
        for prev, current in zip(experience_intervals, experience_intervals[1:]):
            prev_end = prev[1]
            next_start = current[0]
            if prev_end + timedelta(days=1) < next_start:
                gaps.append((prev_end + timedelta(days=1), next_start - timedelta(days=1)))

        gaps = self._subtract_intervals(gaps, education_intervals)
        return [
            {
                "start_date": gap_start.isoformat(),
                "end_date": gap_end.isoformat(),
            }
            for gap_start, gap_end in gaps
        ]

    def normalize_scores(self, parsed_json):
        # If score is below 4 take maximum score as 4 and normalize
        # Otherwise take 100 as max score and normalize
        # Add the normalized score back to the original parsed JSON
        education_entries = parsed_json.get("education") or []
        if not isinstance(education_entries, list):
            return parsed_json

        for education in education_entries:
            if not isinstance(education, dict):
                continue
            raw = str(education.get("cgpa_or_score") or "").strip()
            if not raw:
                continue

            numeric = re.findall(r"\d+(?:\.\d+)?", raw.replace(",", ""))
            if not numeric:
                continue

            score = float(numeric[0])
            if "%" in raw:
                max_score = 100
            elif score <= 4.0:
                max_score = 4
            elif score <= 5.0:
                max_score = 5
            elif score <= 10.0:
                max_score = 10
            else:
                max_score = 100

            education["normalized_score"] = round((score / max_score) * 100, 2)
        return parsed_json
    
    def find_university_from_the_rankings(self, data, query, threshold=80):
        # Extract all university names
        names = [item["name"] for item in data["data"]]
        query_norm = self.normalize(query)
        norm_names = [self.normalize(name) for name in names]

        for i, name in enumerate(norm_names):
            if query_norm in name or name in query_norm:
                return data["data"][i]
            
        query_abbr = self.get_abbreviation(query_norm)
        
        for i, name in enumerate(norm_names):
            if self.get_abbreviation(name) == query_abbr:
                return data["data"][i]
        
        # Find best match
        match, score, index = process.extractOne(
            query,
            names,
            scorer=fuzz.WRatio
        )
        
        # Check if score passes threshold
        if score >= threshold:
            return data["data"][index]
        
        return None
    
    def _load_rankings_data(self):
        path = settings.DATA_DIR / "the_rankings.json"
        if not path.exists():
            return {"data": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_qs_rankings_data(self):
        path = settings.DATA_DIR / "qs_rankings.json"
        if not path.exists():
            return {"data": []}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"data": []}
        

    def normalize(self, text):
        text = text.lower()
        text = re.sub(r'\(.*?\)', '', text)  # remove brackets
        text = re.sub(r'[-,)()]', ' ', text)
        text = re.sub(r'[^a-z0-9 ]', '', text)
        return text.strip()

    def get_abbreviation(self, text):
        STOPWORDS = {"of", "and", "the", "in", "for"}
        words = text.split()
        return ''.join(word[0] for word in words if word and word not in STOPWORDS)
    
    def enrich_json(self, parsed_json, cv_text):
        enriched_json = parsed_json if isinstance(parsed_json, dict) else {}
        enriched_json = self.normalize_scores(enriched_json)
        enriched_json["gaps in experience"] = self._build_gap_intervals(enriched_json)

        education_entries = enriched_json.get("education") or []
        if isinstance(education_entries, list):
            the_rankings = self._load_rankings_data()
            qs_rankings = self._load_qs_rankings_data()
            for education in education_entries:
                if not isinstance(education, dict):
                    continue
                degree = str(education.get("degree") or "").lower()
                if any(token in degree for token in ("hssc", "ssc", "fsc", "matric", "intermediate", "o level", "a level")):
                    continue

                university_name = str(education.get("institution") or "").strip()
                if not university_name:
                    continue

                the_info = self.find_university_from_the_rankings(
                    data=the_rankings,
                    query=university_name,
                )
                qs_info = self.find_university_from_the_rankings(
                    data=qs_rankings,
                    query=university_name,
                )

                education["university_rankings"] = {
                    "the": the_info or {"rank": None, "source": "the", "status": "unverified"},
                    "qs": qs_info or {"rank": None, "source": "qs", "status": "unverified"},
                }
                # Back-compat: keep a flat university_info with THE rank.
                education["university_info"] = the_info or {"rank": None, "source": "the", "status": "unverified"}

        enriched_json["missing_info"] = self.detect_missing_info(enriched_json)
        return enriched_json