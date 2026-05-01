"""
Scores how well a job matches the candidate profile (0–100).

Breakdown:
  skill_match      40 pts  — fraction of required skills the candidate has
  experience_match 30 pts  — candidate years vs. required years (linear)
  role_match       20 pts  — job title contains a preferred-role keyword
  salary_match     10 pts  — job salary_min >= candidate min_salary

Neutral half-points are awarded when data is absent so missing info
doesn't unfairly penalise either party.
"""

import sqlite3
from app.db.database import get_job_by_id, get_or_create_profile, update_job_scores
from app.models.models import FitBreakdown


def run(conn: sqlite3.Connection, job_id: int) -> tuple[float, dict]:
    """Score a single job. Updates DB and returns (score, breakdown_dict)."""
    job = get_job_by_id(conn, job_id)
    profile = get_or_create_profile(conn)
    if not job or not profile:
        return 0.0, {}

    b = FitBreakdown()
    b.skill_match = _score_skills(job, profile)
    b.experience_match = _score_experience(job, profile)
    b.role_match = _score_role(job, profile)
    b.salary_match = _score_salary(job, profile)
    b.total = b.skill_match + b.experience_match + b.role_match + b.salary_match

    candidate_skills = {s.lower() for s in profile.get("skills", [])}
    job_skills = {s.lower() for s in job.get("skills", [])}
    b.matched_skills = sorted(candidate_skills & job_skills)
    b.missing_skills = sorted(job_skills - candidate_skills)
    b.notes = _notes(b)

    score = round(b.total, 1)
    breakdown = b.model_dump()
    update_job_scores(conn, job_id, score, breakdown)
    return score, breakdown


def score_all(conn: sqlite3.Connection) -> list[tuple[int, float, dict]]:
    """Score every job in the database."""
    rows = conn.execute("SELECT id FROM jobs").fetchall()
    return [(r["id"], *run(conn, r["id"])) for r in rows]


# ---------------------------------------------------------------------------
# Scoring components
# ---------------------------------------------------------------------------

def _score_skills(job: dict, profile: dict) -> float:
    job_skills = [s.lower() for s in job.get("skills", [])]
    if not job_skills:
        return 20.0  # neutral — no data to penalise on

    candidate_skills = {s.lower() for s in profile.get("skills", [])}
    matched = sum(
        1 for js in job_skills
        if any(cs in js or js in cs for cs in candidate_skills)
    )
    return round(matched / len(job_skills) * 40, 1)


def _score_experience(job: dict, profile: dict) -> float:
    required = float(job.get("experience_years") or 0)
    candidate = float(profile.get("experience_years") or 0)
    if required == 0:
        return 15.0  # neutral
    if candidate >= required:
        return 30.0
    return round(max(0.0, candidate / required * 30), 1)


def _score_role(job: dict, profile: dict) -> float:
    preferred = [r.lower() for r in profile.get("preferred_roles", [])]
    if not preferred:
        return 10.0  # neutral
    title = job.get("title", "").lower()
    for role in preferred:
        words = role.split()
        if all(w in title for w in words):
            return 20.0
        if any(w in title for w in words):
            return 12.0
    return 0.0


def _score_salary(job: dict, profile: dict) -> float:
    min_want = int(profile.get("min_salary") or 0)
    if min_want == 0:
        return 5.0  # neutral
    job_min = int(job.get("salary_min") or 0)
    job_max = int(job.get("salary_max") or 0)
    if job_min == 0 and job_max == 0:
        return 5.0  # no salary listed — neutral
    effective = job_min or job_max
    if effective >= min_want:
        return 10.0
    if effective >= min_want * 0.80:
        return 5.0
    return 0.0


def _notes(b: FitBreakdown) -> str:
    label = (
        "Strong match." if b.total >= 80
        else "Good match." if b.total >= 60
        else "Moderate match." if b.total >= 40
        else "Weak match."
    )
    if b.missing_skills:
        label += f" Missing: {', '.join(b.missing_skills[:3])}."
    return label
