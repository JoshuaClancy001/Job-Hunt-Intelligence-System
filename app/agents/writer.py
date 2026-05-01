"""
Generates cover letters and resume bullet points.

Uses Ollama (llama3) if available at localhost:11434.
Falls back to deterministic templates — no external dependencies required.
Saves generated content to the applications table.
"""

import json
import sqlite3
import requests

from app.db.database import (
    get_job_by_id, get_or_create_profile,
    get_application_for_job, insert_application,
)
from app.models.models import GeneratedContent


def run(conn: sqlite3.Connection, job_id: int,
        content_type: str = "cover-letter") -> GeneratedContent:
    """
    Generate content for a job and save to applications table.
    content_type: "cover-letter" | "resume-bullets" | "both"
    """
    job = get_job_by_id(conn, job_id)
    profile = get_or_create_profile(conn)
    if not job:
        return GeneratedContent(source="error")

    result = GeneratedContent()

    if content_type in ("cover-letter", "both"):
        source, text = _cover_letter(job, profile)
        result.cover_letter = text
        result.source = source

    if content_type in ("resume-bullets", "both"):
        source, bullets = _resume_bullets(job, profile)
        result.resume_bullets = bullets
        if content_type == "resume-bullets":
            result.source = source

    # Persist to applications table
    existing = get_application_for_job(conn, job_id)
    if existing:
        conn.execute(
            "UPDATE applications SET cover_letter=?, resume_bullets=?, updated_at=datetime('now') WHERE job_id=?",
            (result.cover_letter, json.dumps(result.resume_bullets), job_id),
        )
        conn.commit()
    else:
        insert_application(conn, {
            "job_id": job_id,
            "status": "saved",
            "applied_at": None,
            "notes": "",
            "cover_letter": result.cover_letter,
            "resume_bullets": result.resume_bullets,
        })

    return result


# ---------------------------------------------------------------------------
# Cover letter
# ---------------------------------------------------------------------------

def _cover_letter(job: dict, profile: dict) -> tuple[str, str]:
    ollama = _call_ollama(_cover_letter_prompt(job, profile))
    if ollama:
        return "ollama", ollama
    return "template", _cover_letter_template(job, profile)


def _cover_letter_prompt(job: dict, profile: dict) -> str:
    return f"""Write a professional 3-paragraph cover letter for this job application.
Be specific and concise. Do not use placeholder brackets.

Candidate: {profile.get('name') or 'the applicant'}
Experience: {profile.get('experience_years', 0)} years
Skills: {', '.join((profile.get('skills') or [])[:10])}
Summary: {profile.get('summary', '')}

Role: {job.get('title', '')} at {job.get('company', '')}
Required skills: {', '.join((job.get('skills') or [])[:10])}
"""


def _cover_letter_template(job: dict, profile: dict) -> str:
    name = profile.get("name") or "I"
    skills = (profile.get("skills") or [])[:3]
    job_skills = (job.get("skills") or [])[:3]
    exp = profile.get("experience_years", 0)
    company = job.get("company", "your company")
    title = job.get("title", "this role")
    matched = [s for s in job_skills if s in (profile.get("skills") or [])]
    skill_line = (
        f"My experience with {', '.join(matched)} aligns directly with your requirements."
        if matched
        else f"I bring hands-on experience with {', '.join(skills)}."
    )

    return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {title} position at {company}. With {exp} years of professional experience, I am confident in my ability to contribute meaningfully to your team from day one.

{skill_line} Throughout my career I have delivered results in fast-paced environments and I thrive when working on challenging technical problems. I am particularly drawn to {company} because of the opportunity to work on impactful products at scale.

I would welcome the opportunity to discuss how my background aligns with your needs. Thank you for your time and consideration.

Sincerely,
{name if name != 'I' else 'Your Name'}"""


# ---------------------------------------------------------------------------
# Resume bullets
# ---------------------------------------------------------------------------

def _resume_bullets(job: dict, profile: dict) -> tuple[str, list[str]]:
    ollama = _call_ollama(_bullets_prompt(job, profile))
    if ollama:
        lines = [l.lstrip("•-* ").strip() for l in ollama.strip().splitlines() if l.strip()]
        return "ollama", lines[:5]
    return "template", _bullets_template(job, profile)


def _bullets_prompt(job: dict, profile: dict) -> str:
    return f"""Write 3 strong resume bullet points tailored for this job.
Each bullet should start with a strong action verb and include a quantified result where possible.
Output only the 3 bullets, one per line, no numbering or extra text.

Role: {job.get('title', '')} at {job.get('company', '')}
Required skills: {', '.join((job.get('skills') or [])[:8])}
Candidate skills: {', '.join((profile.get('skills') or [])[:8])}
"""


def _bullets_template(job: dict, profile: dict) -> list[str]:
    skills = (profile.get("skills") or [])
    exp = profile.get("experience_years", 0)
    s1 = skills[0] if skills else "Python"
    s2 = skills[1] if len(skills) > 1 else "REST APIs"
    s3 = skills[2] if len(skills) > 2 else "cloud infrastructure"
    return [
        f"Designed and delivered scalable {s1} services handling 10M+ requests/day, reducing latency by 40%",
        f"Built and maintained {s2} integrations across 5+ internal and external systems, improving data reliability",
        f"Led migration of legacy systems to {s3}, cutting infrastructure costs by 30% and improving uptime to 99.9%",
    ]


# ---------------------------------------------------------------------------
# Ollama helper
# ---------------------------------------------------------------------------

def _call_ollama(prompt: str) -> str | None:
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip() or None
    except Exception:
        return None
