CV_EXTRACTION_PROMPT = """
You are an expert academic and professional CV parser.

Task:
Extract the candidate data from the provided CV text and return STRICT JSON only.

Output JSON schema:
{
  "personal_info": {
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "google_scholar": ""
  },
  "education": [
    {
      "degree": "",
      "specialization": "",
      "institution": "",
      "board_or_institution": "",
      "start_year": "",
      "end_year": "",
      "passing_year": "",
      "cgpa_or_score": "",
      "cgpa_scale": "",
      "percentage": ""
    }
  ],
  "experience": [
    {
      "role": "",
      "organization": "",
      "location": "",
      "employment_type": "",
      "start_date": "",
      "end_date": "",
      "duration_of_employment": "",
    }
  ],
  "skills": [""],
  "publications": [
    {
      "title": "",
      "author": "",
      "co-author": "",
      "published_in": "",
      "doi": "",
      "issn": "",
      "impact_factor": "",
      "volume": "",
      "pp": "",
      "date": ""
    }
  ],
  "supervision": {
    "main_supervisor_students": [
      {"student_name": "", "level": "MS|PhD", "year": "", "topic": "", "institution": ""}
    ],
    "co_supervisor_students": [
      {"student_name": "", "level": "MS|PhD", "year": "", "topic": "", "institution": ""}
    ]
  },
  "patents": [
    {
      "title": "",
      "patent_number": "",
      "date": "",
      "year": "",
      "status": "",
      "country": "",
      "inventors": "",
      "link": ""
    }
  ],
  "books": [
    {
      "title": "",
      "year": "",
      "publisher": "",
      "authors": "",
      "isbn": "",
      "link": ""
    }
  ],
  "references": [
    {
      "name": "",
      "contact type": "",
      "designation": "",
      "address": "",
      "phone": "",
      "email": ""
    }
  ]
}

Rules:
1) Return valid JSON only. No markdown, no comments.
2) Use empty string, empty list, or null-like omission behavior conservatively when unknown.
3) Keep extracted facts faithful to the source CV text.
4) If SSE/SSC/HSSC/Matric/FSc/O-Level/A-Level are mentioned, include them as education entries with the right degree label.
""".strip()


SKILLS_ENRICHMENT_PROMPT = """
You are an expert CV skill extractor.

Task:
You will receive structured candidate JSON that was extracted earlier from a CV.
If the skills list is empty, infer and populate only relevant professional/technical/academic skills
using the provided structured data and source CV text snippet.

Output JSON schema:
{
  "skills": [""]
}

Rules:
1) Return valid JSON only. No markdown, no comments.
2) Include only relevant skills strongly supported by the input.
3) Deduplicate skills and keep concise canonical names.
4) If no reliable skills can be inferred, return an empty list.
""".strip()
