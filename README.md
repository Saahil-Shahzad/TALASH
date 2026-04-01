# TALASH — Milestone 1

An end-to-end CV ingestion and candidate management system, featuring LLM-powered extraction, a FastAPI backend, MongoDB Atlas persistence, and a React frontend prototype.

---

## What's Included

| Area | Details |
|---|---|
| **Backend** | FastAPI application for CV ingestion and candidate management |
| **PDF Processing** | Extraction via `pdfplumber` with structured parsing |
| **LLM Integration** | Groq-compatible prompt pipeline with retry logic and fallback heuristics |
| **Database** | Candidate persistence via MongoDB Atlas |
| **Exports** | Structured candidate data as JSON and CSV/Excel |
| **Frontend** | React + Tailwind CSS + Recharts dashboard prototype |
| **CLI Scripts** | Pipeline and batch processing for milestone demos |
| **Documentation** | Architecture diagrams, wireframes, prompt design, and milestone checklist |

---

## Project Structure

```
talash/
├── backend/
│   ├── app/          # API routes, services, DB, models, schemas, utilities
│   └── data/         # Raw CVs, parsed JSON, exports
├── frontend/
│   └── src/          # Components, services, pages, charts
├── scripts/          # Pipeline and batch scripts
└── docs/             # Architecture, prompts, wireframes, milestone checklist
```

---

## Quick Start

### Prerequisites

- Python 3.12 or 3.13
- Node.js 18+
- A MongoDB Atlas cluster (see [MongoDB Setup](#mongodb-atlas-setup))
- A Groq API key (optional — fallback parser is available for demos)

Note: on Python 3.14 you may hit native build failures for `pydantic-core`.

---

### 1. Backend

```bash
# If you already have a `.venv` created with Python 3.14, delete it first.
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Run tests:

```bash
pytest
```

The API will be available at `http://localhost:8000`.

---

### 2. CV Pipeline (CLI)

Run the preprocessing pipeline against a folder of raw CVs:

```bash
python scripts/run_pipeline.py backend/data/raw_cvs --overwrite
```

**Outputs:**

- Parsed JSON → `backend/data/parsed_json/`
- Exports → `backend/data/exports/`
- Candidate records inserted into MongoDB Atlas

---

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Environment Variables

Copy `.env.example` into your environment and fill in the values below.

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes* | API key for LLM extraction. *Without this, the app falls back to a heuristic parser. |
| `GROQ_MODEL` | No | Override the default Groq model |
| `LLM_MAX_JSON_RETRIES` | No | Number of retries when the LLM returns invalid JSON |
| `MONGODB_URL` | Yes | MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | No | Database name, if not included in `MONGODB_URL` |

### Research verification (external sources)

The full analysis report can optionally verify publication metadata (title/venue/year/DOI/citations) against external sources.
When enabled, the report also attempts best-effort verification for **books** (via OpenLibrary ISBN lookups) and **patents** (via PatentsView for US patents).

- Enable it: set `RESEARCH_VERIFY_ENABLED=1`
- Optional (recommended): set `OPENALEX_MAILTO` to your email for OpenAlex requests
- Optional: set `SEMANTIC_SCHOLAR_API_KEY` to include Semantic Scholar in matching

Current status vs Talash research requirements:

- Implemented now: external metadata verification via OpenAlex + Crossref (+ Semantic Scholar if configured)
- Implemented when datasets are provided: CORE conference ranks (`CORE_CONF_RANKINGS_CSV`), journal quartiles via SJR CSV (`SJR_JOURNAL_RANKS_CSV`)
- Not fully implemented yet (requires paid/closed APIs): WoS indexing and Scopus indexing

If you have licensed access, set `CLARIVATE_API_KEY` / `SCOPUS_API_KEY` and we can wire their official endpoints.
If you have exported ranking datasets (CSV), point `CORE_CONF_RANKINGS_CSV` / `SJR_JOURNAL_RANKS_CSV` at them.

**Supported Groq models:**

- `llama-3.3-70b-versatile`
- `mixtral-8x7b-32768`
- `deepseek-r1-distill-llama-70b`

---

## MongoDB Atlas Setup

1. Create a project and cluster in [MongoDB Atlas](https://cloud.mongodb.com).
2. Create a database user and allowlist your IP address.
3. Copy the connection string and set it as `MONGODB_URL`.
4. Optionally set `MONGODB_DB_NAME` if your URI does not include a default database.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/upload/process-folder` | Trigger pipeline on a server-side folder |
| `POST` | `/api/upload/upload-files` | Upload CV files directly |
| `GET` | `/api/candidates/` | List all candidates |
| `GET` | `/api/candidates/{candidate_id}` | Get a specific candidate |
| `GET` | `/api/analysis/summary/{candidate_id}` | Get analysis summary for a candidate |
| `GET` | `/api/analysis/email-draft/{candidate_id}` | Generate an outreach email draft |
| `GET` | `/api/analysis/report/{candidate_id}` | Full analysis report (education, professional, research, skills) |
| `POST` | `/api/analysis/role-alignment/{candidate_id}` | Score extracted skills against a provided job description |

### Optional datasets

- `backend/data/the_rankings.json` (optional): used to enrich university education entries.
- `backend/data/qs_rankings.json` (optional): if present, QS ranks are included in `education[*].university_rankings.qs`.
