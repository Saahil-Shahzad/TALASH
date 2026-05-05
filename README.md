# TALASH — Talent Acquisition & Learning Automation for Smart Hiring

An AI-powered recruitment support system for university hiring, built for **CS417 – Large Language Models (Spring 2026)**. TALASH automates CV screening, candidate evaluation, academic and publication analysis, experience validation, and skill alignment — helping recruiters make more informed, evidence-based decisions.

---

## Milestones at a Glance

| Milestone | Weight | Status | Scope |
|---|---|---|---|
| **Milestone 1** | 25% | ✅ Complete | Preprocessing module, architecture, LLM pipeline, DB, early prototype |
| **Milestone 2** | 25% | ✅ Complete | Educational & professional analysis, missing-info detection, email drafting, research profile (partial) |
| **Milestone 3** | 50% | ✅ Complete | Full research profile, topic variability, co-author analysis, supervision, books, patents, skills alignment, full web app |

---

## What's Included

| Area | Details |
|---|---|
| **Backend** | FastAPI application — upload, candidate management, and full analysis pipeline |
| **PDF Processing** | Extraction via `pdfplumber`; LLM-powered structured parsing via Groq with heuristic fallback |
| **LLM Integration** | Groq-compatible prompt pipeline with retry logic and JSON validation |
| **Database** | MongoDB Atlas — candidate persistence, parsed JSON, analysis results |
| **Enrichment** | THE/QS university rankings lookup, CGPA/percentage normalization, gap detection |
| **Research Verification** | External metadata verification via OpenAlex, Crossref, and optionally Semantic Scholar |
| **Books & Patents** | OpenLibrary ISBN lookups (books) and PatentsView API (US patents) |
| **Analysis Engine** | Educational, professional, research, supervision, books, patents, skills, and job-alignment analysis |
| **Email Drafting** | Personalized missing-information emails generated per candidate |
| **Frontend** | React 18 + Tailwind CSS + Recharts — four-page dashboard (Overview, Processing, Candidates, Analysis) |
| **CLI Scripts** | `run_pipeline.py`, `batch_process.py`, `split_cvs.py` for demo and batch runs |
| **Exports** | Structured candidate data as JSON and CSV/Excel |

---

## Project Structure

```
talash/
├── backend/
│   └── app/
│       ├── api/                  # Route handlers (upload, candidates, analysis)
│       ├── core/                 # Config (settings, env), LLM prompts
│       ├── db/                   # MongoDB connection and helpers
│       ├── models/               # Pydantic data models
│       ├── schemas/              # Request/response schemas
│       ├── services/             # Core business logic
│       │   ├── parser_service.py           # PDF extraction + LLM parsing
│       │   ├── llm_service.py              # Groq API wrapper with retry logic
│       │   ├── enrichment_service.py       # Rankings lookup, score normalization, gap detection
│       │   ├── analysis_service.py         # Full analysis engine (all modules)
│       │   ├── research_verification_service.py  # OpenAlex / Crossref / Semantic Scholar
│       │   ├── books_patents_verification_service.py  # OpenLibrary + PatentsView
│       │   └── email_service.py            # Missing-info email drafting
│       └── utils/                # PDF and file utilities
├── frontend/
│   └── src/
│       ├── pages/                # Overview, Processing, Candidates, Analysis
│       ├── components/           # Dashboard, CandidateTable, CandidateDetail, Upload, StatusBadge
│       ├── charts/               # CandidateMetricsChart (Recharts)
│       └── services/             # API client
├── scripts/
│   ├── run_pipeline.py           # Single-run CV ingestion pipeline
│   ├── batch_process.py          # Batch processing across multiple folders
│   └── split_cvs.py              # CV pre-splitting utility
└── docs/
    └── supabase_schema.sql       # Reference DB schema (Supabase/PostgreSQL)
```

---

## Quick Start

### Prerequisites

- Python 3.12 or 3.13 (Python 3.14 may hit native build failures for `pydantic-core`)
- Node.js 18+
- A MongoDB Atlas cluster (see [MongoDB Setup](#mongodb-atlas-setup))
- A Groq API key (optional — a heuristic parser fallback is available for demos)

---

### 1. Backend

```bash
# Create a virtualenv with Python 3.12 (delete any existing 3.14 venv first)
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Run the test suite:

```bash
pytest
```

---

### 2. CV Pipeline (CLI)

Run the preprocessing pipeline against a folder of raw CVs:

```bash
python scripts/run_pipeline.py backend/data/raw_cvs --overwrite
```

**Outputs:**

- Parsed JSON → `backend/data/parsed_json/`
- Exports (CSV / Excel) → `backend/data/exports/`
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

Copy `.env.example` to `.env` and fill in the values.

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes* | API key for LLM extraction. *Without this, the app falls back to a heuristic parser. |
| `GROQ_MODEL` | No | Override the default Groq model (see supported models below) |
| `LLM_MAX_JSON_RETRIES` | No | Number of retries when the LLM returns invalid JSON (default: `3`) |
| `MONGODB_URL` | Yes | MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | No | Database name if not embedded in `MONGODB_URL` (default: `talash`) |

### Research Verification (External Sources)

The full analysis report can optionally verify publication metadata (title / venue / year / DOI / citations) against external sources. When enabled, the report also attempts best-effort verification for **books** (via OpenLibrary ISBN lookups) and **patents** (via PatentsView for US patents).

| Variable | Description |
|---|---|
| `RESEARCH_VERIFY_ENABLED` | Set to `1` to enable external verification (default: `0`) |
| `OPENALEX_MAILTO` | Recommended — your email for polite OpenAlex requests |
| `SEMANTIC_SCHOLAR_API_KEY` | Optional — include Semantic Scholar in publication matching |
| `SCOPUS_API_KEY` | Optional — Scopus indexing lookups (requires licensed access) |
| `CLARIVATE_API_KEY` | Optional — Web of Science indexing lookups (requires licensed access) |
| `CORE_CONF_RANKINGS_CSV` | Optional — path to a local CORE conference rankings CSV you provide |
| `SJR_JOURNAL_RANKS_CSV` | Optional — path to a local SJR journal quartile rankings CSV you provide |

**Implementation status vs. TALASH research requirements:**

- ✅ External metadata verification via OpenAlex + Crossref (+ Semantic Scholar if configured)
- ✅ Book verification via OpenLibrary ISBN lookups
- ✅ Patent verification via PatentsView (US patents)
- ✅ Conference ranking via CORE CSV (when `CORE_CONF_RANKINGS_CSV` is provided)
- ✅ Journal quartile ranking via SJR CSV (when `SJR_JOURNAL_RANKS_CSV` is provided)
- ⚠️ WoS and Scopus indexing status — not fully implemented yet (requires paid/closed APIs). Set `CLARIVATE_API_KEY` / `SCOPUS_API_KEY` to wire official endpoints.

**Supported Groq models:**

- `llama-3.3-70b-versatile` *(default)*
- `mixtral-8x7b-32768`
- `deepseek-r1-distill-llama-70b`

---

## MongoDB Atlas Setup

1. Create a project and cluster at [MongoDB Atlas](https://cloud.mongodb.com).
2. Create a database user and allowlist your IP address.
3. Copy the connection string and set it as `MONGODB_URL`.
4. Optionally set `MONGODB_DB_NAME` if your URI does not include a default database.

---

## Optional Datasets

| File | Purpose |
|---|---|
| `backend/data/the_rankings.json` | THE world university rankings — used to enrich `education[*].university_rankings.the` |
| `backend/data/qs_rankings.json` | QS world university rankings — used to enrich `education[*].university_rankings.qs` |
| `backend/data/external/core_conf_ranks.csv` | CORE conference rankings CSV (user-provided) |
| `backend/data/external/sjr_journal_ranks.csv` | SJR journal quartile CSV (user-provided) |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/upload/process-folder` | Trigger the CV ingestion pipeline on a server-side folder |
| `POST` | `/api/upload/upload-files` | Upload CV PDF files directly |
| `GET` | `/api/upload/status` | Get processing status for a folder |
| `GET` | `/api/candidates/` | List all candidates |
| `GET` | `/api/candidates/{candidate_id}` | Get a specific candidate's full parsed record |
| `GET` | `/api/analysis/summary/{candidate_id}` | Get the LLM-generated candidate summary |
| `GET` | `/api/analysis/email-draft/{candidate_id}` | Generate a personalized missing-info outreach email |
| `GET` | `/api/analysis/report/{candidate_id}` | Full analysis report (education, professional, research, supervision, books, patents, skills) |
| `POST` | `/api/analysis/role-alignment/{candidate_id}` | Score the candidate's evidenced skills against a provided job description |

---

## Functional Modules

### Preprocessing Module (Milestone 1)
Parses candidate CVs in PDF format using `pdfplumber`. The extracted raw text is passed to the Groq LLM using a structured prompt to produce a clean JSON record with fields for personal information, education, experience, skills, publications, supervision, patents, and books. A heuristic fallback parser is available when no API key is configured. Parsed records are stored in MongoDB and exported as JSON and CSV/Excel.

---

### Educational Profile Analysis (Milestone 2 & 3)
Evaluates the candidate's academic background in a structured, evidence-based manner.

- **Degree extraction** — SSC / HSSC / UG (BS/BSc) / PG (MS/MSc/MPhil) / PhD, preserving degree title, institution, specialization, and year range
- **Score normalization** — converts percentage, CGPA (4.0 / 5.0 / 10.0 scales), grades, and divisions into a normalized percentage for fair comparison, while preserving original values
- **Institutional quality** — matches institution names against THE and QS world university rankings using fuzzy matching; records rank or notes absence transparently
- **Progression analysis** — detects academic path (direct BS→MS→PhD or 14+16-year BSc→MSc routes), checks for consistency of specialization, and assesses improvement or decline in academic performance
- **Gap detection** — calculates gaps between educational stages (SSC→HSSC, HSSC→UG, UG→PG, PG→PhD)
- **Gap justification** — cross-references educational gaps against documented professional activities (employment, research assistantships, internships, freelancing) to determine whether gaps are explained or unexplained
- **Overall educational strength** — generates a structured assessment summarizing highest qualification, institutional quality, academic consistency, and gap analysis

---

### Professional Experience & Employment History (Milestone 2 & 3)
Evaluates professional continuity, career progression, and employment consistency.

- **Timeline consistency** — extracts job titles, organizations, start/end dates, and employment types; detects overlaps between education and employment, and between concurrent jobs
- **Professional gap detection** — identifies periods of no recorded employment after education or between jobs; calculates gap durations and flags them for review
- **Gap justification** — matches professional gaps to productive activities (higher education, research, freelancing, training, entrepreneurship) where available
- **Career progression analysis** — examines movement from junior to senior roles, from research assistantship to faculty, or from execution to management; determines whether the career trajectory is consistent and progressive

---

### Research Profile Analysis (Milestone 3)

#### Journal Publications
For each journal paper in the candidate's CV:
- Extracts journal name, ISSN, paper title, publication year, and author list
- Identifies ISSN and matches against recognized journal databases
- Retrieves WoS indexing status and impact factor (requires `CLARIVATE_API_KEY` for live lookups)
- Retrieves Scopus indexing status (requires `SCOPUS_API_KEY` for live lookups)
- Determines quartile ranking (Q1–Q4) from local SJR CSV if provided
- Determines authorship role — first author, corresponding author, both, or co-author

#### Conference Papers
For each conference paper:
- Identifies conference name, paper title, year, authors, and proceedings details
- Looks up CORE ranking (A*, A, B, C) from local CORE CSV if provided
- Detects conference maturity from ordinal markers (e.g., "5th International Conference")
- Infers proceedings publisher and indexing platform (IEEE Xplore, Springer, ACM, Scopus)
- Determines authorship role

#### External Metadata Verification
When `RESEARCH_VERIFY_ENABLED=1`, the system queries OpenAlex, Crossref, and optionally Semantic Scholar to verify title, venue, year, DOI, and citation counts for each listed publication. Match confidence and source are recorded alongside each paper's analysis.

---

### Topic Variability Analysis (Milestone 3)
Measures breadth vs. focus of the candidate's research portfolio.

- Tokenizes publication titles and classifies them into thematic clusters (e.g., machine learning, computer vision, networks, cybersecurity, NLP, software engineering)
- Computes a normalized entropy-based diversity score across clusters
- Identifies the candidate's dominant research area and secondary themes
- Outputs: major themes, percentage of publications per theme, dominant topic, diversity score, and topic-shift trends over time

---

### Co-Author Analysis (Milestone 3)
Analyzes publication co-authorship to identify collaboration patterns.

- Extracts and de-duplicates co-author lists across all publications
- Identifies recurring collaborators and one-time collaborators
- Computes: total unique co-authors, most frequent collaborators, average team size, proportion of papers with recurring collaborators
- Infers possible student–supervisor collaboration patterns based on authorship position and frequency
- Estimates collaboration diversity (internal vs. external, national vs. international where inferable)

---

### Student Supervision (Milestone 3)
Evaluates the candidate's academic mentoring contribution.

- Identifies and counts MS and PhD students supervised as main supervisor vs. co-supervisor
- Analyzes co-authored papers with supervised students
- Determines the candidate's authorship position and corresponding-author status in student publications
- Notes that supervision data is often absent from CVs — the email drafting module can request this from candidates

---

### Books Authored / Co-Authored (Milestone 3)
Evaluates scholarly writing and long-form knowledge dissemination.

- Extracts book name, authors, ISBN, publisher, publishing year, and online link
- Determines authorship role (sole, lead, co-author, contributing)
- Verifies book existence and metadata via **OpenLibrary** ISBN lookups
- Records publisher credibility and provides verification links for evaluators

---

### Patents (Milestone 3)
Evaluates applied research and intellectual property output.

- Extracts patent number, title, date, inventors, country of filing, and verification link
- Determines the candidate's inventor role (lead, co-inventor, contributing)
- Verifies US patents via the **PatentsView** API
- Provides online verification links for transparency

---

### Skill Alignment with Job Roles and Research Publications (Milestone 3)
Verifies whether claimed skills are genuinely supported by the candidate's record.

- **Skill-to-experience alignment** — checks whether job titles and responsibilities provide evidence for claimed skills (e.g., project management, machine learning, curriculum design)
- **Skill-to-publication alignment** — checks whether technical and research-oriented skills are reflected in the candidate's publication topics and domains
- **Skill consistency** — assesses whether skills appear consistently across education, work history, research, and certifications, or only once without support
- **Job relevance** — when a target job description is provided (via the `/role-alignment` endpoint), compares evidenced skills against job requirements and produces a structured alignment score
- **Evidence strength** — classifies each skill as strongly evidenced, partially evidenced, weakly evidenced, or unsupported

---

### Missing Information Detection & Email Drafting (Milestone 2 & 3)
Detects absent, incomplete, or unclear information in a candidate's CV.

- Flags missing academic scores, incomplete dates, absent publication details, unclear authorship roles, and missing supervision records
- Generates a **personalized, individualized email draft** for each candidate with missing data, requesting specific missing fields
- For batch runs with multiple candidates, generates separate drafts per candidate

---

## Frontend — Web Application

The React frontend provides a full-featured dashboard across four pages:

| Page | Route | Description |
|---|---|---|
| **Overview** | `/` | Summary dashboard with candidate count, pipeline status, and recent activity |
| **Processing** | `/processing` | Trigger CV ingestion (folder-based or direct file upload), monitor pipeline status |
| **Candidates** | `/candidates` | Tabular list of all candidates with search, sort, and status filtering |
| **Analysis** | `/analysis` | Per-candidate analysis workspace — educational, professional, research, and missing-info views |

**Tech stack:** React 18, React Router v6, Tailwind CSS v3, Recharts, Axios, Vite.

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Backend API | FastAPI, Uvicorn |
| LLM | Groq (llama-3.3-70b-versatile / mixtral-8x7b-32768 / deepseek-r1-distill-llama-70b) |
| PDF Extraction | pdfplumber |
| Database | MongoDB Atlas (pymongo) |
| Data Validation | Pydantic v2 |
| External APIs | OpenAlex, Crossref, Semantic Scholar, OpenLibrary, PatentsView |
| Fuzzy Matching | rapidfuzz |
| HTTP Client | httpx |
| Data Exports | pandas, openpyxl |
| Frontend | React 18, Vite, Tailwind CSS, Recharts, Axios |
| Testing | pytest |

---

## Running Tests

```bash
pytest
```

Tests cover:
- `test_health.py` — API health check endpoint
- `test_analysis_service.py` — Unit tests for the core analysis engine
- `test_research_verification_service.py` — Unit tests for the research verification pipeline
