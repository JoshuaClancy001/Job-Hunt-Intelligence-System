"""
Loads sample data for demo mode.

Inserts 5 diverse fake job postings, a candidate profile, and 2 sample
applications. Guards against duplicate loads by checking the job count first.
"""

import sqlite3
from app.db.database import insert_job, insert_application, save_profile

SAMPLE_JOBS = [
    {
        "title": "Senior Python Engineer",
        "company": "Streamline AI",
        "location": "San Francisco, CA",
        "url": "https://example.com/jobs/1",
        "raw_description": (
            "We are looking for a Senior Python Engineer with 5+ years of experience. "
            "You will build scalable REST APIs using FastAPI and PostgreSQL. "
            "Experience with AWS, Docker, and Redis required. "
            "Remote friendly. Salary: $140,000 - $175,000."
        ),
        "skills": ["python", "fastapi", "postgresql", "aws", "docker", "redis", "rest api"],
        "experience_years": 5,
        "salary_min": 140000,
        "salary_max": 175000,
        "remote": True,
    },
    {
        "title": "Data Engineer",
        "company": "DataFlow Corp",
        "location": "New York, NY",
        "url": "https://example.com/jobs/2",
        "raw_description": (
            "Seeking a Data Engineer to build and maintain our data pipelines. "
            "3+ years experience with Python, Airflow, dbt, and Spark. "
            "BigQuery and Snowflake experience a plus. Hybrid role. "
            "Compensation: $120,000 - $150,000."
        ),
        "skills": ["python", "airflow", "dbt", "spark", "bigquery", "snowflake", "sql"],
        "experience_years": 3,
        "salary_min": 120000,
        "salary_max": 150000,
        "remote": False,
    },
    {
        "title": "ML Engineer",
        "company": "NeuralWorks",
        "location": "Remote",
        "url": "https://example.com/jobs/3",
        "raw_description": (
            "Join our ML team to deploy and scale machine learning models. "
            "4+ years experience required. Skills: Python, PyTorch, MLflow, Kubernetes. "
            "Experience with LLMs and RAG pipelines preferred. "
            "Fully remote. $150,000 - $190,000."
        ),
        "skills": ["python", "pytorch", "mlflow", "kubernetes", "llm", "rag", "docker"],
        "experience_years": 4,
        "salary_min": 150000,
        "salary_max": 190000,
        "remote": True,
    },
    {
        "title": "Backend Software Engineer",
        "company": "FinTech Solutions",
        "location": "Austin, TX",
        "url": "https://example.com/jobs/4",
        "raw_description": (
            "Backend engineer to work on our financial platform. "
            "2+ years with Python or Go, PostgreSQL, Redis. "
            "Experience with microservices and distributed systems helpful. "
            "On-site preferred. $110,000 - $140,000."
        ),
        "skills": ["python", "golang", "postgresql", "redis", "microservices", "distributed systems"],
        "experience_years": 2,
        "salary_min": 110000,
        "salary_max": 140000,
        "remote": False,
    },
    {
        "title": "Full Stack Engineer",
        "company": "ProductLab",
        "location": "Remote",
        "url": "https://example.com/jobs/5",
        "raw_description": (
            "Full stack engineer to build our SaaS product. "
            "3+ years experience. Must know React, TypeScript, Python, and PostgreSQL. "
            "Familiarity with AWS and CI/CD pipelines required. "
            "Remote-first company. Salary: $125,000 - $160,000."
        ),
        "skills": ["react", "typescript", "python", "postgresql", "aws", "ci/cd", "rest api"],
        "experience_years": 3,
        "salary_min": 125000,
        "salary_max": 160000,
        "remote": True,
    },
]

SAMPLE_PROFILE = {
    "name": "Alex Johnson",
    "skills": [
        "python", "fastapi", "postgresql", "redis", "aws",
        "docker", "rest api", "react", "typescript", "git", "linux", "system design",
    ],
    "experience_years": 5,
    "preferred_roles": ["backend engineer", "software engineer", "python engineer"],
    "preferred_locations": ["Remote", "San Francisco", "New York"],
    "min_salary": 130000,
    "summary": (
        "Backend engineer with 5 years building scalable APIs and data services. "
        "Seeking senior IC or tech lead roles at product-focused companies."
    ),
}


def run(conn: sqlite3.Connection) -> dict:
    """Load demo data. Returns a status dict."""
    count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    if count > 0:
        return {"status": "already_loaded", "jobs_inserted": 0, "profile": ""}

    job_ids = [insert_job(conn, job) for job in SAMPLE_JOBS]
    save_profile(conn, SAMPLE_PROFILE)

    # Two sample applications: one applied, one rejected
    insert_application(conn, {
        "job_id": job_ids[0],
        "status": "applied",
        "applied_at": "2026-04-15T10:00:00",
        "notes": "Referred by a contact at Streamline AI.",
        "cover_letter": "",
        "resume_bullets": [],
    })
    insert_application(conn, {
        "job_id": job_ids[1],
        "status": "rejected",
        "applied_at": "2026-04-10T09:00:00",
        "notes": "Applied cold. No response after 2 weeks, then rejected.",
        "cover_letter": "",
        "resume_bullets": [],
    })

    return {
        "status": "loaded",
        "jobs_inserted": len(job_ids),
        "profile": SAMPLE_PROFILE["name"],
    }
