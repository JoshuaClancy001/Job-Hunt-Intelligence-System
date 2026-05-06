"""
Extracts structured fields from raw job description text.

Pipeline:
  1. Try Ollama (llama3) for rich JSON extraction — falls back if unavailable
  2. Regex patterns for salary and experience
  3. Keyword bank for skill extraction (130+ terms, longest-first to avoid substring collisions)
"""

import re
import json
import sqlite3
from typing import Optional
import requests

from app.db.database import get_job_by_id, update_job_parsed_fields

# ---------------------------------------------------------------------------
# Skill keyword bank
# ---------------------------------------------------------------------------

SKILLS = sorted([
    "python", "javascript", "typescript", "java", "go", "golang", "rust",
    "c++", "c#", "ruby", "scala", "kotlin", "swift", "php", "r",
    "react", "vue", "angular", "next.js", "nuxt", "svelte", "html", "css",
    "tailwind", "fastapi", "flask", "django", "express", "node.js",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "spark", "hadoop", "airflow", "dbt", "mlflow", "hugging face",
    "transformers", "langchain", "llm", "rag", "vector database",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
    "ci/cd", "github actions", "jenkins", "linux",
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
    "elasticsearch", "snowflake", "bigquery", "dynamodb",
    "rest api", "graphql", "microservices", "agile", "scrum", "tdd",
    "system design", "distributed systems", "git", "jira", "figma",
], key=len, reverse=True)

_RE_REMOTE = re.compile(
    r"\b(fully remote|100%\s*remote|work from home|wfh|distributed team|remote.first|remote only)\b", re.I
)
_RE_HYBRID = re.compile(
    r"\b(hybrid|in.office\s+\d+\s+days?|\d+\s+days?\s+(?:per\s+week\s+)?(?:in|at)\s+(?:the\s+)?office"
    r"|required\s+to\s+(?:be\s+in|come\s+(?:in)?to)\s+(?:the\s+)?office"
    r"|on.?site|onsite)\b",
    re.I,
)
_RE_EXP = [
    # "2–4 years of professional software development experience" (range + words before experience)
    re.compile(r"(\d+)\s*[-–]\s*\d+\s*years?\s+of\s+(?:\w+\s+){0,4}experience", re.I),
    # "2 to 4 years of software engineering experience"
    re.compile(r"(\d+)\s+to\s+\d+\s*years?\s+of\s+(?:\w+\s+){0,4}experience", re.I),
    # "2+ years of professional experience" / "2 years of experience"
    re.compile(r"(\d+)\+?\s*years?\s+of\s+(?:\w+\s+){0,3}experience", re.I),
    # "2+ years working/building/developing/engineering"
    re.compile(r"(\d+)\+?\s*years?\s+(?:working|building|developing|shipping|engineering|coding|programming)", re.I),
    # "experience: 2+ years" / "experience of 2 years"
    re.compile(r"experience[:\sof]+(\d+)\+?\s*years?", re.I),
    # "minimum 2 years" / "at least 2 years"
    re.compile(r"(?:minimum|at\s+least)\s+(\d+)\s*years?", re.I),
]
_SEP = r"(?:\s*[-–]+\s*|\s+to\s+)"  # separators: hyphen, em-dash, or "to"

_RE_SALARY = [
    # Xk–Yk or $Xk–$Yk (both k, safe — won't match experience ranges)
    re.compile(r"\$?\s*(\d+)\s*[kK]" + _SEP + r"\$?\s*(\d+)\s*[kK]", re.I),
    # X,XXX–Y,YYY or $X,XXX–$Y,YYY (both with commas)
    re.compile(r"\$?\s*(\d{1,3}(?:,\d{3})+)" + _SEP + r"\$?\s*(\d{1,3}(?:,\d{3})+)", re.I),
    # $X–$Y ($ required to avoid matching experience ranges like "3–5 years")
    re.compile(r"\$\s*(\d{1,3}(?:,\d{3})*|\d+)[kK]?" + _SEP + r"\$?\s*(\d{1,3}(?:,\d{3})*|\d+)[kK]?", re.I),
    # Single $Xk value
    re.compile(r"\$\s*(\d+)\s*[kK]\b", re.I),
    # X,XXX /yr pattern
    re.compile(r"(\d{1,3}(?:,\d{3})+)\s*(?:USD|/year|/yr|annually)", re.I),
]


def run(conn: sqlite3.Connection, job_id: int) -> dict:
    """Parse a job by id, update DB, return parsed fields."""
    job = get_job_by_id(conn, job_id)
    if not job:
        return {}
    text = (job.get("raw_description") or "") + " " + (job.get("title") or "")
    parsed = parse_text(text)
    # Preserve salary already set on the job (e.g. from discovery API) if parser found nothing
    if not parsed.get("salary_min") and not parsed.get("salary_max"):
        parsed["salary_min"] = job.get("salary_min") or 0
        parsed["salary_max"] = job.get("salary_max") or 0
    update_job_parsed_fields(conn, job_id, parsed)
    return parsed


def parse_all(conn: sqlite3.Connection) -> list[dict]:
    """Parse all jobs that haven't been parsed yet."""
    rows = conn.execute("SELECT id FROM jobs WHERE parsed_at IS NULL").fetchall()
    return [run(conn, r["id"]) for r in rows]


def parse_text(text: str, title: str = "") -> dict:
    """Parse raw text → structured dict. Tries Ollama first, falls back to regex."""
    result = _parse_ollama(text, title)
    if result:
        return result
    return _parse_regex(text)


def _parse_regex(text: str) -> dict:
    is_hybrid = bool(_RE_HYBRID.search(text))
    is_remote = bool(_RE_REMOTE.search(text)) and not is_hybrid
    return {
        "skills": _extract_skills(text),
        "experience_years": _extract_experience(text),
        "salary_min": _extract_salary(text)[0],
        "salary_max": _extract_salary(text)[1],
        "remote": is_remote,
        "hybrid": is_hybrid if is_hybrid else None,
    }


def _extract_skills(text: str) -> list[str]:
    tl = text.lower()
    seen, result = set(), []
    for skill in SKILLS:
        if skill not in seen and re.search(r"\b" + re.escape(skill) + r"\b", tl):
            seen.add(skill)
            result.append(skill)
    return result


def _extract_experience(text: str) -> Optional[float]:
    for pat in _RE_EXP:
        m = pat.search(text)
        if m:
            return float(m.group(1))
    return None


def _extract_salary(text: str) -> tuple[int, int]:
    for pat in _RE_SALARY:
        m = pat.search(text)
        if m:
            raw = m.group(0)

            def parse_num(s: str) -> int:
                s = s.replace(",", "")
                n = int(float(s))
                if n < 1000 and "k" in raw.lower():
                    n *= 1000
                return n

            groups = [g for g in m.groups() if g]
            if len(groups) >= 2:
                return parse_num(groups[0]), parse_num(groups[1])
            if groups:
                v = parse_num(groups[0])
                return v, v
    return 0, 0


def _parse_ollama(text: str, title: str = "") -> Optional[dict]:
    prompt = f"""Extract structured information from this job posting.
Return ONLY valid JSON with these exact keys:
{{"skills": ["skill1", "skill2"], "experience_years": null, "salary_min": 0, "salary_max": 0, "remote": true, "hybrid": false, "relevant": true}}

Rules:
- skills: list every technical skill, tool, or language explicitly mentioned.
- experience_years: Extract the MINIMUM years of experience required. Look for ANY of these phrasings: "X years experience", "X+ years experience", "X years of experience", "X–Y years of experience" (use X), "X to Y years" (use X), "X or more years", "at least X years", "minimum X years", "X years in software/backend/etc", "hands-on experience (X years)", "X yrs experience". Use the lowest number when a range is given. Use null ONLY if no number of years is mentioned anywhere in the posting. Do NOT infer from words like "senior" or "junior" alone.
- salary_min / salary_max: extract only if dollar amounts appear. Use 0 if absent.
- remote: true only if the posting is FULLY remote (100% remote, WFH, distributed, no required office attendance). false if hybrid or on-site.
- hybrid: true if the posting requires ANY in-office days (e.g. "hybrid", "2 days in office", "on-site", "must be in office"). false if fully remote or fully on-site with no remote option. null if unspecified.
- relevant: true if this is primarily a software engineering role (building web/mobile apps, APIs, product features, frontend/backend/full-stack development). false if it is primarily data engineering (ETL, Spark, Hadoop, data pipelines), data science, ML/AI research, pure DevOps/infrastructure, QA/testing only, or requires a specialized non-SWE background. When in doubt, use true.
- No explanation. No markdown. Only the JSON object.

Job Title: {title}
Description:
{text[:3000]}
"""
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            parsed = json.loads(m.group())
            # Normalize: null/0/missing all mean "not specified" for experience
            if not parsed.get("experience_years"):
                parsed["experience_years"] = None
            # Normalize relevant: default to None (unknown) if not returned
            if "relevant" not in parsed:
                parsed["relevant"] = None
            # Normalize skills to lowercase so matching is always case-insensitive
            parsed["skills"] = [s.lower() for s in parsed.get("skills", []) if isinstance(s, str)]
            return parsed
    except Exception:
        pass
    return None
