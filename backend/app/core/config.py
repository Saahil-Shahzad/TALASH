from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Load project-level .env so CLI and API runs share the same environment values.
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    PROJECT_ROOT = PROJECT_ROOT
    BACKEND_ROOT = PROJECT_ROOT / "backend"
    DATA_DIR = BACKEND_ROOT / "data"
    RAW_CV_DIR = DATA_DIR / "raw_cvs"
    PARSED_JSON_DIR = DATA_DIR / "parsed_json"
    EXPORT_DIR = DATA_DIR / "exports"
    MONGODB_URL = os.getenv("MONGODB_URL", "")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "talash")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    LLM_MAX_JSON_RETRIES = int(os.getenv("LLM_MAX_JSON_RETRIES", "3"))
    LLM_REQUEST_PAUSE_SECONDS = float(os.getenv("LLM_REQUEST_PAUSE_SECONDS", "5.0"))

    # -------------------------
    # External research verification
    # -------------------------
    RESEARCH_VERIFY_ENABLED = _as_bool(os.getenv("RESEARCH_VERIFY_ENABLED"), default=False)
    RESEARCH_VERIFY_TIMEOUT_SECONDS = float(os.getenv("RESEARCH_VERIFY_TIMEOUT_SECONDS", "8.0"))
    RESEARCH_VERIFY_MAX_MATCHES = int(os.getenv("RESEARCH_VERIFY_MAX_MATCHES", "3"))

    # Polite identifier for OpenAlex requests (recommended). Example: "you@domain.com"
    OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "")

    # Optional API keys for additional sources
    SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY", "")
    CLARIVATE_API_KEY = os.getenv("CLARIVATE_API_KEY", "")

    # Optional local datasets (CSV) for ranks/quartiles (user-provided)
    CORE_CONF_RANKINGS_CSV = os.getenv("CORE_CONF_RANKINGS_CSV", "")
    SJR_JOURNAL_RANKS_CSV = os.getenv("SJR_JOURNAL_RANKS_CSV", "")


settings = Settings()
