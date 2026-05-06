"""
Optional FastAPI web server.

The CLI (cli.py) is the primary interface. This server is provided for
the React frontend and any integrations.

Run with:  python main.py
Or:        uvicorn main:app --reload --port 8080

Docs at:   http://localhost:8080/docs
"""

from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from app.db.database import (
    get_connection, get_all_jobs, get_job_by_id, get_or_create_profile,
    save_profile, get_all_applications, insert_application,
    update_application_status, get_application_for_job, delete_job, dismiss_job,
    get_status_history, update_job,
)

app = FastAPI(
    title="Job Hunt Intelligence System",
    description="Local-first job tracking and AI scoring API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_last_discovery: dict = {"at": None, "result": None}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ScrapeRequest(BaseModel):
    url: str

class ManualJobRequest(BaseModel):
    title: str
    company: str
    description: str
    location: str = ""
    url: str = ""

class ApplicationCreate(BaseModel):
    job_id: int
    status: str = "saved"
    notes: str = ""

class ApplicationUpdate(BaseModel):
    status: str
    notes: str = ""
    rejection_reason: str = ""

class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    remote: Optional[bool] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_years: Optional[float] = None
    skills: Optional[list[str]] = None


class GenerateRequest(BaseModel):
    content_type: str = "cover-letter"

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    skills: Optional[list[str]] = None
    experience_years: Optional[float] = None
    preferred_roles: Optional[list[str]] = None
    preferred_locations: Optional[list[str]] = None
    min_salary: Optional[int] = None
    summary: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def health():
    return {"status": "ok", "service": "Job Hunt Intelligence System"}


@app.get("/jobs")
def list_jobs():
    return get_all_jobs(get_connection())


@app.get("/jobs/{job_id}")
def get_job(job_id: int):
    job = get_job_by_id(get_connection(), job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.post("/jobs/scrape")
def scrape_job(req: ScrapeRequest):
    from app.scraper.scraper import scrape_url
    from app.agents.parser import run as parse_job
    from app.agents.fit_scorer import run as score_job
    from app.db.database import insert_job

    conn = get_connection()
    job_data = scrape_url(req.url)
    job_id = insert_job(conn, job_data)
    parse_job(conn, job_id)
    score_job(conn, job_id)
    return get_job_by_id(conn, job_id)


@app.post("/jobs/add")
def add_job_manually(req: ManualJobRequest):
    from app.agents.parser import parse_text
    from app.agents.fit_scorer import run as score_job
    from app.db.database import insert_job

    conn = get_connection()
    parsed = parse_text(req.description, req.title)

    job_id = insert_job(conn, {
        "title": req.title,
        "company": req.company,
        "location": req.location,
        "url": req.url,
        "raw_description": req.description,
        "skills": parsed.get("skills", []),
        "experience_years": parsed.get("experience_years", 0),
        "salary_min": parsed.get("salary_min", 0),
        "salary_max": parsed.get("salary_max", 0),
        "remote": parsed.get("remote", False),
    })
    conn.execute("UPDATE jobs SET parsed_at=datetime('now') WHERE id=?", (job_id,))
    conn.commit()
    score_job(conn, job_id)
    return get_job_by_id(conn, job_id)


@app.put("/jobs/{job_id}")
def update_job_endpoint(job_id: int, req: JobUpdate):
    conn = get_connection()
    existing = get_job_by_id(conn, job_id)
    if not existing:
        raise HTTPException(404, "Job not found")
    merged = {**existing, **{k: v for k, v in req.model_dump().items() if v is not None}}
    update_job(conn, job_id, merged)
    return get_job_by_id(conn, job_id)


@app.delete("/jobs/{job_id}")
def delete_job_endpoint(job_id: int):
    conn = get_connection()
    if not get_job_by_id(conn, job_id):
        raise HTTPException(404, "Job not found")
    dismiss_job(conn, job_id)
    return {"deleted": job_id}


@app.post("/jobs/{job_id}/score")
def score_job_endpoint(job_id: int):
    from app.agents.fit_scorer import run as score_job
    conn = get_connection()
    if not get_job_by_id(conn, job_id):
        raise HTTPException(404, "Job not found")
    score, breakdown = score_job(conn, job_id)
    return {"job_id": job_id, "fit_score": score, "breakdown": breakdown}


@app.post("/jobs/{job_id}/generate")
def generate_content(job_id: int, req: GenerateRequest):
    from app.agents.writer import run as generate
    conn = get_connection()
    if not get_job_by_id(conn, job_id):
        raise HTTPException(404, "Job not found")
    return generate(conn, job_id, req.content_type).model_dump()


@app.get("/applications")
def list_applications():
    return get_all_applications(get_connection())


@app.post("/applications")
def create_application(req: ApplicationCreate):
    conn = get_connection()
    if not get_job_by_id(conn, req.job_id):
        raise HTTPException(404, "Job not found")
    app_id = insert_application(conn, {
        "job_id": req.job_id, "status": req.status,
        "applied_at": None, "notes": req.notes,
        "cover_letter": "", "resume_bullets": [],
    })
    return {"id": app_id, "job_id": req.job_id, "status": req.status}


@app.put("/applications/{app_id}")
def update_application(app_id: int, req: ApplicationUpdate):
    update_application_status(get_connection(), app_id, req.status, req.notes, req.rejection_reason)
    return {"id": app_id, "status": req.status}


@app.get("/applications/{app_id}/history")
def get_application_history(app_id: int):
    return get_status_history(get_connection(), app_id)


@app.post("/jobs/discover")
def discover_jobs(source: str | None = None):
    """Manually trigger job discovery. Pass ?source=linkedin to limit to one source."""
    from app.agents.discovery import run as discover, ALL_SOURCES
    sources = [source] if source else None
    result = discover(get_connection(), sources=sources)
    _last_discovery["at"] = datetime.now(timezone.utc).isoformat()
    _last_discovery["result"] = result
    return result

@app.get("/jobs/discovery-status")
def discovery_status():
    return {
        "last_run_at": _last_discovery["at"],
        "last_result": _last_discovery["result"],
        "next_run_at": None,
    }


@app.get("/insights")
def get_insights():
    from app.agents.insights import run as compute_insights
    return compute_insights(get_connection()).model_dump()


@app.post("/profile/reload")
def reload_profile_from_file():
    """Load profile.json from disk into the database."""
    import json
    from pathlib import Path
    profile_path = Path(__file__).parent / "profile.json"
    if not profile_path.exists():
        raise HTTPException(404, "profile.json not found")
    with open(profile_path) as f:
        data = json.load(f)
    conn = get_connection()
    save_profile(conn, data)
    return get_or_create_profile(conn)


@app.get("/profile")
def get_profile():
    return get_or_create_profile(get_connection())


@app.put("/profile")
def update_profile(req: ProfileUpdate):
    conn = get_connection()
    existing = get_or_create_profile(conn)
    updates = req.model_dump(exclude_none=True)
    existing.update(updates)
    save_profile(conn, existing)
    return get_or_create_profile(conn)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
