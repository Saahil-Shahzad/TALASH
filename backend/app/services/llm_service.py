import json
import re
import threading
import time

from backend.app.core.config import settings
from backend.app.core.prompts import CV_EXTRACTION_PROMPT, SKILLS_ENRICHMENT_PROMPT


class LLMService:
    _throttle_lock = threading.Lock()
    _last_request_monotonic = 0.0

    def __init__(self) -> None:
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.max_json_retries = max(1, settings.LLM_MAX_JSON_RETRIES)
        self.request_pause_seconds = max(0.0, settings.LLM_REQUEST_PAUSE_SECONDS)

    def parse_cv_text(self, cv_text: str) -> dict:
        if not cv_text.strip():
            return self._empty_payload()

        if self.api_key:
            try:
                parsed = self._call_groq_with_retries(
                    system_prompt=CV_EXTRACTION_PROMPT,
                    user_content=cv_text[:120000],
                )
                # return self._enrich_skills_if_missing(parsed, cv_text)
                return parsed
            except Exception as exc:
                return self._heuristic_parse(
                    cv_text,
                    note=(
                        "LLM extraction failed; used heuristic fallback. "
                        f"Reason: {type(exc).__name__}."
                    ),
                )

        return self._heuristic_parse(
            cv_text,
            note="GROQ_API_KEY not found in runtime environment; used heuristic fallback.",
        )

    def _call_groq_with_retries(self, system_prompt: str, user_content: str) -> dict:
        from groq import Groq

        client = Groq(api_key=self.api_key)
        parse_error = ""
        last_raw = ""

        for attempt in range(1, self.max_json_retries + 1):
            if attempt == 1:
                prompt = user_content
            else:
                prompt = (
                    "Your previous response was not valid JSON. "
                    "Return STRICT JSON only and ensure it matches the schema.\n\n"
                    f"Previous parse error: {parse_error}\n\n"
                    f"Previous response:\n{last_raw}\n\n"
                    "Now regenerate only valid JSON for this CV:\n"
                    f"{user_content}"
                )

            self._wait_before_groq_call()

            response = client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = response.choices[0].message.content or ""
            last_raw = raw

            try:
                return self._load_json(raw)
            except Exception as exc:
                parse_error = str(exc)

        # Raise after retries so caller can gracefully use fallback parser.
        raise ValueError(f"Invalid JSON after {self.max_json_retries} attempts. Last error: {parse_error}")

    def _enrich_skills_if_missing(self, parsed: dict, cv_text: str) -> dict:
        if not isinstance(parsed, dict):
            return parsed
        if not self._is_skills_empty(parsed):
            return parsed

        cv_snippet = cv_text[:120000]
        structured_json = json.dumps(parsed, ensure_ascii=False)
        user_content = (
            "Populate only the skills field from this extracted candidate JSON.\n\n"
            f"Extracted candidate JSON:\n{structured_json}\n\n"
            "Source CV text:\n"
            f"{cv_snippet}"
        )

        try:
            skills_payload = self._call_groq_with_retries(
                system_prompt=SKILLS_ENRICHMENT_PROMPT,
                user_content=user_content,
            )
        except Exception:
            return parsed

        skills = skills_payload.get("skills", []) if isinstance(skills_payload, dict) else []
        if isinstance(skills, list):
            parsed["skills"] = [str(s).strip() for s in skills if str(s).strip()]
        return parsed

    def _is_skills_empty(self, payload: dict) -> bool:
        if not isinstance(payload, dict):
            return True
        skills = payload.get("skills")
        if skills is None:
            return True
        if isinstance(skills, list):
            cleaned = [str(s).strip() for s in skills if str(s).strip()]
            return len(cleaned) == 0
        return not str(skills).strip()

    def _wait_before_groq_call(self) -> None:
        if self.request_pause_seconds <= 0:
            return

        with self._throttle_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_monotonic
            remaining = self.request_pause_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_request_monotonic = time.monotonic()

    def _load_json(self, raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw).strip()
            raw = raw[:-3].strip() if raw.endswith("```") else raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                raise
            return json.loads(match.group(0))

    def _heuristic_parse(self, cv_text: str, note: str) -> dict:
        lines = [line.strip() for line in cv_text.splitlines() if line.strip()]
        first = lines[0] if lines else ""

        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cv_text)
        phone_match = re.search(r"(\+?\d[\d\s\-]{7,}\d)", cv_text)

        return {
            "personal_info": {
                "full_name": first if len(first.split()) <= 6 else "",
                "email": email_match.group(0) if email_match else "",
                "phone": phone_match.group(0) if phone_match else "",
                "location": "",
                "linkedin": "",
                "google_scholar": "",
            },
            "education": [],
            "experience": [],
            "skills": self._extract_skills_heuristic(cv_text),
            "publications": [],
            "supervision": {"main_supervisor_students": [], "co_supervisor_students": []},
            "patents": [],
            "books": [],
            "meta": {
                "parser": "heuristic_fallback",
                "note": note,
            },
        }

    def _extract_skills_heuristic(self, cv_text: str) -> list[str]:
        skill_candidates = [
            "Python",
            "Java",
            "C++",
            "SQL",
            "Machine Learning",
            "Deep Learning",
            "NLP",
            "TensorFlow",
            "PyTorch",
            "FastAPI",
            "React",
        ]
        lower = cv_text.lower()
        return [s for s in skill_candidates if s.lower() in lower]

    def _empty_payload(self) -> dict:
        return {
            "personal_info": {
                "full_name": "",
                "email": "",
                "phone": "",
                "location": "",
                "linkedin": "",
                "google_scholar": "",
            },
            "education": [],
            "experience": [],
            "skills": [],
            "publications": [],
            "supervision": {"main_supervisor_students": [], "co_supervisor_students": []},
            "patents": [],
            "books": [],
        }

