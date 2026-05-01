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
    r"\b(remote|work from home|wfh|fully remote|distributed team)\b", re.I
)
_RE_EXP = [
    re.compile(r"(\d+)\+?\s*years?\s+of\s+(?:professional\s+)?experience", re.I),
    re.compile(r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:relevant\s+)?experience", re.I),
    re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*years?\s+(?:of\s+)?experience", re.I),
    re.compile(r"experience[:\s]+(\d+)\+?\s*years?", re.I),
    re.compile(r"minimum\s+(\d+)\s+years?", re.I),
]
_RE_SALARY = [
    re.compile(
        r"\$\s*(\d{1,3}(?:,\d{3})*|\d+)[kK]?\s*[-–to]+\s*\$?\s*(\d{1,3}(?:,\d{3})*|\d+)[kK]?",
        re.I,
    ),
    re.compile(r"(\d{1,3}(?:,\d{3})+)\s*(?:USD|usd|/year|/yr|annually)", re.I),
]


def run(conn: sqlite3.Connection, job_id: int) -> dict:
    """Parse a job by id, update DB, return parsed fields."""
    job = get_job_by_id(conn, job_id)
    if not job:
        return {}
    text = (job.get("raw_description") or "") + " " + (job.get("title") or "")
    parsed = parse_text(text)
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
    return {
        "skills": _extract_skills(text),
        "experience_years": _extract_experience(text),
        "salary_min": _extract_salary(text)[0],
        "salary_max": _extract_salary(text)[1],
        "remote": bool(_RE_REMOTE.search(text)),
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
{{"skills": ["list", "of", "required", "skills"], "experience_years": 3, "salary_min": 120000, "salary_max": 160000, "remote": true}}

Rules:
- skills: list every technical skill, tool, or language explicitly mentioned.
- experience_years: ONLY include a number if the posting EXPLICITLY states a required number of years (e.g. "3+ years", "minimum 5 years"). Do NOT infer from words like "senior" or "junior". Use null if no specific number is stated.
- salary_min / salary_max: extract only if dollar amounts appear. Use 0 if absent.
- remote: true only if the posting says remote, WFH, or distributed. false otherwise.
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
            return parsed
    except Exception:
        pass
    return None
