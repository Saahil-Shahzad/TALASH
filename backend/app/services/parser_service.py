import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from backend.app.services.enrichment_service import EnrichmentService

from backend.app.core.config import settings
from backend.app.db.mongo import normalize_mongo_doc
from backend.app.services.llm_service import LLMService
from backend.app.utils.file_utils import ensure_dir, timestamp_slug
from backend.app.utils.pdf_utils import extract_text_from_pdf


class ParserService:
    def __init__(self, db):
        self.db = db
        self.collection = db["talash"]
        self.status_collection = db["processing_status"]
        self.llm = LLMService()
        self.enricher = EnrichmentService()
        ensure_dir(settings.RAW_CV_DIR)
        ensure_dir(settings.PARSED_JSON_DIR)
        ensure_dir(settings.EXPORT_DIR)

    def _set_status(self, file_name: str, status: str, candidate_id: str | None = None, error: str | None = None) -> None:
        payload = {
            "file": file_name,
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if candidate_id is not None:
            payload["candidate_id"] = str(candidate_id)
        if error:
            payload["error"] = error
        self.status_collection.update_one({"file": file_name}, {"$set": payload}, upsert=True)

    def get_processing_status(self, folder_path: str) -> dict:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")

        items: list[dict] = []
        for pdf_path in sorted(folder.glob("*.pdf")):
            status_doc = self.status_collection.find_one({"file": pdf_path.name})
            if status_doc:
                items.append(
                    {
                        "file": status_doc.get("file"),
                        "status": status_doc.get("status"),
                        "candidate_id": status_doc.get("candidate_id"),
                        "updated_at": status_doc.get("updated_at").isoformat()
                        if status_doc.get("updated_at")
                        else None,
                    }
                )
                continue

            existing = self.collection.find_one({"source_file": pdf_path.name})
            if existing:
                items.append(
                    {
                        "file": pdf_path.name,
                        "status": "processed",
                        "candidate_id": str(existing.get("_id")),
                        "updated_at": existing.get("created_at").isoformat()
                        if existing.get("created_at")
                        else None,
                    }
                )
            else:
                items.append({"file": pdf_path.name, "status": "awaiting", "candidate_id": None, "updated_at": None})

        return {"folder_path": str(folder_path), "items": items}

    def process_folder(self, folder_path: str, overwrite_existing: bool = False) -> dict:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")

        pdf_files = sorted(folder.glob("*.pdf"))
        results: list[dict] = []

        overview_rows: list[dict] = []
        candidates_rows: list[dict] = []
        education_rows: list[dict] = []
        experience_rows: list[dict] = []
        skills_rows: list[dict] = []
        publications_rows: list[dict] = []
        patents_rows: list[dict] = []
        books_rows: list[dict] = []

        for pdf_path in pdf_files:
            existing = self.collection.find_one({"source_file": pdf_path.name})
            if existing and not overwrite_existing:
                self._set_status(pdf_path.name, "skipped", candidate_id=existing.get("_id"))
            else:
                self._set_status(pdf_path.name, "awaiting")

        processed = skipped = failed = 0
        for pdf_path in pdf_files:
            existing = self.collection.find_one({"source_file": pdf_path.name})
            if existing and not overwrite_existing:
                skipped += 1
                self._set_status(pdf_path.name, "skipped", candidate_id=existing.get("_id"))
                results.append({"file": pdf_path.name, "status": "skipped", "reason": "already_exists"})
                continue

            try:
                self._set_status(pdf_path.name, "processing")
                raw_text = extract_text_from_pdf(pdf_path)
                parsed = self.llm.parse_cv_text(raw_text)
                enriched = self.enricher.enrich_json(parsed, raw_text)
                saved = self._save_candidate(pdf_path.name, raw_text, enriched, existing)
                self._save_json_file(pdf_path.stem, enriched)

                overview_rows.append(self._flatten_for_export(saved["id"], pdf_path.name, enriched))
                self._append_relational_rows(
                    candidates_rows,
                    education_rows,
                    experience_rows,
                    skills_rows,
                    publications_rows,
                    patents_rows,
                    books_rows,
                    saved["id"],
                    pdf_path.name,
                    enriched,
                )
                processed += 1
                self._set_status(pdf_path.name, "processed", candidate_id=saved.get("id"))
                results.append({"file": pdf_path.name, "status": "processed", "candidate_id": saved["id"]})
            except Exception as exc:
                failed += 1
                self._set_status(pdf_path.name, "failed", error=str(exc))
                results.append({"file": pdf_path.name, "status": "failed", "error": str(exc)})

        export_csv, export_xlsx, export_tables = self._export_tables(
            overview_rows=overview_rows,
            candidates_rows=candidates_rows,
            education_rows=education_rows,
            experience_rows=experience_rows,
            skills_rows=skills_rows,
            publications_rows=publications_rows,
            patents_rows=patents_rows,
            books_rows=books_rows,
        )
        return {
            "processed_count": processed,
            "skipped_count": skipped,
            "failed_count": failed,
            "files": results,
            "export_csv": str(export_csv),
            "export_xlsx": str(export_xlsx),
            "export_tables": {key: str(value) for key, value in export_tables.items()},
        }

    def _save_candidate(self, source_file: str, raw_text: str, parsed: dict, existing: dict | None) -> dict:
        info = parsed.get("personal_info", {})
        skills = parsed.get("skills", [])
        created_at = (existing or {}).get("created_at") or datetime.now(timezone.utc)
        payload = {
            "source_file": source_file,
            "full_name": info.get("full_name"),
            "email": info.get("email"),
            "phone": info.get("phone"),
            "location": info.get("location"),
            "skills_csv": ", ".join(skills) if isinstance(skills, list) else str(skills),
            "raw_text": raw_text,
            "parsed_json": parsed,
            "created_at": created_at,
        }

        if existing:
            self.collection.update_one({"_id": existing["_id"]}, {"$set": payload})
            payload["_id"] = existing["_id"]
            return normalize_mongo_doc(payload)

        result = self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return normalize_mongo_doc(payload)

    def _save_json_file(self, stem: str, parsed: dict) -> Path:
        out = settings.PARSED_JSON_DIR / f"{stem}.json"
        out.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        return out

    def _flatten_for_export(self, candidate_id: str, source_file: str, parsed: dict) -> dict:
        info = parsed.get("personal_info", {})
        skills = parsed.get("skills", [])
        return {
            "candidate_id": candidate_id,
            "source_file": source_file,
            "full_name": info.get("full_name", ""),
            "email": info.get("email", ""),
            "phone": info.get("phone", ""),
            "location": info.get("location", ""),
            "skills": " | ".join(skills) if isinstance(skills, list) else str(skills),
            "education_count": len(parsed.get("education", [])),
            "experience_count": len(parsed.get("experience", [])),
            "publication_count": len(parsed.get("publications", [])),
            "patent_count": len(parsed.get("patents", [])),
            "book_count": len(parsed.get("books", [])),
        }

    def _append_relational_rows(
        self,
        candidates_rows: list[dict],
        education_rows: list[dict],
        experience_rows: list[dict],
        skills_rows: list[dict],
        publications_rows: list[dict],
        patents_rows: list[dict],
        books_rows: list[dict],
        candidate_id: str,
        source_file: str,
        parsed: dict,
    ) -> None:
        info = parsed.get("personal_info", {}) if isinstance(parsed, dict) else {}

        candidates_rows.append(
            {
                "candidate_id": candidate_id,
                "source_file": source_file,
                "full_name": info.get("full_name") or "",
                "email": info.get("email") or "",
                "phone": info.get("phone") or "",
                "location": info.get("location") or "",
                "linkedin": info.get("linkedin") or "",
                "google_scholar": info.get("google_scholar") or "",
                "skills_csv": ", ".join(parsed.get("skills", [])) if isinstance(parsed.get("skills"), list) else str(parsed.get("skills") or ""),
            }
        )

        for idx, edu in enumerate(parsed.get("education", []) if isinstance(parsed, dict) else []):
            if not isinstance(edu, dict):
                continue
            education_rows.append(
                {
                    "candidate_id": candidate_id,
                    "education_index": idx,
                    "degree": edu.get("degree") or "",
                    "specialization": edu.get("specialization") or "",
                    "institution": edu.get("institution") or "",
                    "start_year": edu.get("start_year") or "",
                    "end_year": edu.get("end_year") or "",
                    "passing_year": edu.get("passing_year") or "",
                    "cgpa_or_score": edu.get("cgpa_or_score") or "",
                    "normalized_score": edu.get("normalized_score") or "",
                    "university_rank": (edu.get("university_info") or {}).get("rank") if isinstance(edu.get("university_info"), dict) else "",
                }
            )

        for idx, exp in enumerate(parsed.get("experience", []) if isinstance(parsed, dict) else []):
            if not isinstance(exp, dict):
                continue
            experience_rows.append(
                {
                    "candidate_id": candidate_id,
                    "experience_index": idx,
                    "role": exp.get("role") or "",
                    "organization": exp.get("organization") or "",
                    "location": exp.get("location") or "",
                    "employment_type": exp.get("employment_type") or "",
                    "duration_of_employment": exp.get("duration_of_employment") or "",
                    "start_date": exp.get("start_date") or "",
                    "end_date": exp.get("end_date") or "",
                }
            )

        skills = parsed.get("skills", []) if isinstance(parsed, dict) else []
        if isinstance(skills, list):
            for idx, skill in enumerate(skills):
                text = str(skill).strip()
                if not text:
                    continue
                skills_rows.append({"candidate_id": candidate_id, "skill_index": idx, "skill": text})

        for idx, pub in enumerate(parsed.get("publications", []) if isinstance(parsed, dict) else []):
            if not isinstance(pub, dict):
                continue
            publications_rows.append(
                {
                    "candidate_id": candidate_id,
                    "publication_index": idx,
                    "title": pub.get("title") or "",
                    "author": pub.get("author") or "",
                    "co_author": pub.get("co-author") or pub.get("co_authors") or "",
                    "published_in": pub.get("published_in") or "",
                    "impact_factor": pub.get("impact_factor") or "",
                    "volume": pub.get("volume") or "",
                    "pp": pub.get("pp") or "",
                    "date": pub.get("date") or "",
                }
            )

        for idx, pat in enumerate(parsed.get("patents", []) if isinstance(parsed, dict) else []):
            if not isinstance(pat, dict):
                continue
            patents_rows.append(
                {
                    "candidate_id": candidate_id,
                    "patent_index": idx,
                    "title": pat.get("title") or "",
                    "year": pat.get("year") or "",
                    "status": pat.get("status") or "",
                    "patent_number": pat.get("patent_number") or "",
                    "country": pat.get("country") or "",
                    "link": pat.get("link") or "",
                }
            )

        for idx, book in enumerate(parsed.get("books", []) if isinstance(parsed, dict) else []):
            if not isinstance(book, dict):
                continue
            books_rows.append(
                {
                    "candidate_id": candidate_id,
                    "book_index": idx,
                    "title": book.get("title") or "",
                    "year": book.get("year") or "",
                    "publisher": book.get("publisher") or "",
                    "isbn": book.get("isbn") or "",
                    "link": book.get("link") or "",
                }
            )

    def _export_tables(
        self,
        overview_rows: list[dict],
        candidates_rows: list[dict],
        education_rows: list[dict],
        experience_rows: list[dict],
        skills_rows: list[dict],
        publications_rows: list[dict],
        patents_rows: list[dict],
        books_rows: list[dict],
    ) -> tuple[Path, Path, dict[str, Path]]:
        stamp = timestamp_slug()
        export_tables: dict[str, Path] = {}

        overview_csv = settings.EXPORT_DIR / f"talash_overview_{stamp}.csv"
        xlsx_path = settings.EXPORT_DIR / f"talash_export_{stamp}.xlsx"
        pd.DataFrame(overview_rows).to_csv(overview_csv, index=False)

        export_tables["overview"] = overview_csv

        def write_csv(name: str, rows: list[dict]) -> None:
            path = settings.EXPORT_DIR / f"talash_{name}_{stamp}.csv"
            pd.DataFrame(rows).to_csv(path, index=False)
            export_tables[name] = path

        write_csv("candidates", candidates_rows)
        write_csv("education", education_rows)
        write_csv("experience", experience_rows)
        write_csv("skills", skills_rows)
        write_csv("publications", publications_rows)
        write_csv("patents", patents_rows)
        write_csv("books", books_rows)

        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            pd.DataFrame(candidates_rows).to_excel(writer, index=False, sheet_name="candidates")
            pd.DataFrame(education_rows).to_excel(writer, index=False, sheet_name="education")
            pd.DataFrame(experience_rows).to_excel(writer, index=False, sheet_name="experience")
            pd.DataFrame(skills_rows).to_excel(writer, index=False, sheet_name="skills")
            pd.DataFrame(publications_rows).to_excel(writer, index=False, sheet_name="publications")
            pd.DataFrame(patents_rows).to_excel(writer, index=False, sheet_name="patents")
            pd.DataFrame(books_rows).to_excel(writer, index=False, sheet_name="books")
            pd.DataFrame(overview_rows).to_excel(writer, index=False, sheet_name="overview")

        return overview_csv, xlsx_path, export_tables

