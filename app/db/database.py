import sqlite3
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "jobs.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            title            TEXT NOT NULL,
            company          TEXT NOT NULL DEFAULT '',
            location         TEXT DEFAULT '',
            url              TEXT DEFAULT '',
            raw_description  TEXT DEFAULT '',
            skills           TEXT DEFAULT '[]',
            experience_years REAL DEFAULT 0,
            salary_min       INTEGER DEFAULT 0,
            salary_max       INTEGER DEFAULT 0,
            remote           INTEGER DEFAULT 0,
            fit_score        REAL DEFAULT NULL,
            fit_breakdown    TEXT DEFAULT NULL,
            scraped_at       TEXT DEFAULT (datetime('now')),
            parsed_at        TEXT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS applications (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id           INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            status           TEXT DEFAULT 'saved',
            applied_at       TEXT DEFAULT NULL,
            notes            TEXT DEFAULT '',
            cover_letter     TEXT DEFAULT '',
            resume_bullets   TEXT DEFAULT '[]',
            updated_at       TEXT DEFAULT (datetime('now')),
            rejection_reason TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS status_history (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            status         TEXT NOT NULL,
            changed_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS candidate_profile (
            id                   INTEGER PRIMARY KEY DEFAULT 1,
            name                 TEXT DEFAULT '',
            skills               TEXT DEFAULT '[]',
            experience_years     REAL DEFAULT 0,
            preferred_roles      TEXT DEFAULT '[]',
            preferred_locations  TEXT DEFAULT '[]',
            min_salary           INTEGER DEFAULT 0,
            summary              TEXT DEFAULT ''
        );
    """)
    conn.commit()
    # Migrations — safe to re-run; ALTER TABLE fails silently if column exists
    for migration in [
        "ALTER TABLE applications ADD COLUMN rejection_reason TEXT DEFAULT ''",
    ]:
        try:
            conn.execute(migration)
            conn.commit()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Job helpers
# ---------------------------------------------------------------------------

def insert_job(conn: sqlite3.Connection, job: dict) -> int:
    job = _serialize_json_fields(job, ["skills", "fit_breakdown"])
    cur = conn.execute(
        """
        INSERT INTO jobs (title, company, location, url, raw_description,
                          skills, experience_years, salary_min, salary_max, remote)
        VALUES (:title, :company, :location, :url, :raw_description,
                :skills, :experience_years, :salary_min, :salary_max, :remote)
        """,
        {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "raw_description": job.get("raw_description", ""),
            "skills": job.get("skills", "[]"),
            "experience_years": job.get("experience_years", 0),
            "salary_min": job.get("salary_min", 0),
            "salary_max": job.get("salary_max", 0),
            "remote": 1 if job.get("remote") else 0,
        },
    )
    conn.commit()
    return cur.lastrowid


def delete_job(conn: sqlite3.Connection, job_id: int) -> None:
    conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
    conn.commit()


def update_job_scores(conn: sqlite3.Connection, job_id: int,
                      fit_score: float, fit_breakdown: dict) -> None:
    conn.execute(
        "UPDATE jobs SET fit_score=?, fit_breakdown=?, parsed_at=datetime('now') WHERE id=?",
        (fit_score, json.dumps(fit_breakdown), job_id),
    )
    conn.commit()


def update_job_parsed_fields(conn: sqlite3.Connection, job_id: int, fields: dict) -> None:
    skills = fields.get("skills", [])
    if not isinstance(skills, str):
        skills = json.dumps(skills)
    conn.execute(
        """
        UPDATE jobs
        SET skills=?, experience_years=?, salary_min=?, salary_max=?, remote=?,
            parsed_at=datetime('now')
        WHERE id=?
        """,
        (
            skills,
            fields.get("experience_years"),  # None stored as NULL = "not specified"
            fields.get("salary_min", 0),
            fields.get("salary_max", 0),
            1 if fields.get("remote") else 0,
            job_id,
        ),
    )
    conn.commit()


def update_job(conn: sqlite3.Connection, job_id: int, fields: dict) -> None:
    skills = fields.get("skills", [])
    if not isinstance(skills, str):
        skills = json.dumps(skills)
    conn.execute(
        """
        UPDATE jobs
        SET title=?, company=?, location=?, url=?, remote=?,
            salary_min=?, salary_max=?, experience_years=?, skills=?
        WHERE id=?
        """,
        (
            fields.get("title", ""),
            fields.get("company", ""),
            fields.get("location", ""),
            fields.get("url", ""),
            1 if fields.get("remote") else 0,
            fields.get("salary_min", 0),
            fields.get("salary_max", 0),
            fields.get("experience_years", 0),
            skills,
            job_id,
        ),
    )
    conn.commit()


def get_all_jobs(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM jobs ORDER BY fit_score DESC NULLS LAST, id DESC").fetchall()
    return [_deserialize_row(r) for r in rows]


def get_job_by_id(conn: sqlite3.Connection, job_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return _deserialize_row(row) if row else None


# ---------------------------------------------------------------------------
# Application helpers
# ---------------------------------------------------------------------------

def insert_application(conn: sqlite3.Connection, app: dict) -> int:
    bullets = app.get("resume_bullets", [])
    if not isinstance(bullets, str):
        bullets = json.dumps(bullets)
    status = app.get("status", "saved")
    cur = conn.execute(
        """
        INSERT INTO applications
            (job_id, status, applied_at, notes, cover_letter, resume_bullets, rejection_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            app["job_id"],
            status,
            app.get("applied_at"),
            app.get("notes", ""),
            app.get("cover_letter", ""),
            bullets,
            app.get("rejection_reason", ""),
        ),
    )
    app_id = cur.lastrowid
    conn.execute(
        "INSERT INTO status_history (application_id, status) VALUES (?, ?)",
        (app_id, status),
    )
    conn.commit()
    return app_id


def update_application_status(conn: sqlite3.Connection, app_id: int,
                               status: str, notes: str = "",
                               rejection_reason: str = "") -> None:
    conn.execute(
        """
        UPDATE applications
        SET status=?, notes=?, updated_at=datetime('now'),
            rejection_reason=?,
            applied_at=CASE WHEN ? = 'applied' AND applied_at IS NULL
                            THEN datetime('now') ELSE applied_at END
        WHERE id=?
        """,
        (status, notes, rejection_reason, status, app_id),
    )
    conn.execute(
        "INSERT INTO status_history (application_id, status) VALUES (?, ?)",
        (app_id, status),
    )
    conn.commit()


def get_status_history(conn: sqlite3.Connection, app_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT status, changed_at FROM status_history WHERE application_id=? ORDER BY id ASC",
        (app_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_application_for_job(conn: sqlite3.Connection, job_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM applications WHERE job_id=? ORDER BY id DESC LIMIT 1", (job_id,)
    ).fetchone()
    return _deserialize_row(row) if row else None


def get_all_applications(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT a.*, j.title, j.company, j.fit_score, j.salary_min, j.salary_max, j.url
        FROM applications a
        JOIN jobs j ON j.id = a.job_id
        ORDER BY a.applied_at DESC NULLS LAST, a.updated_at DESC
        """
    ).fetchall()
    return [_deserialize_row(r) for r in rows]


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

def get_or_create_profile(conn: sqlite3.Connection) -> dict:
    row = conn.execute("SELECT * FROM candidate_profile WHERE id=1").fetchone()
    if row:
        return _deserialize_row(row)
    conn.execute("INSERT INTO candidate_profile (id) VALUES (1)")
    conn.commit()
    return _deserialize_row(conn.execute("SELECT * FROM candidate_profile WHERE id=1").fetchone())


def save_profile(conn: sqlite3.Connection, profile: dict) -> None:
    def j(v):
        return json.dumps(v) if not isinstance(v, str) else v

    conn.execute(
        """
        INSERT INTO candidate_profile
            (id, name, skills, experience_years, preferred_roles,
             preferred_locations, min_salary, summary)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, skills=excluded.skills,
            experience_years=excluded.experience_years,
            preferred_roles=excluded.preferred_roles,
            preferred_locations=excluded.preferred_locations,
            min_salary=excluded.min_salary, summary=excluded.summary
        """,
        (
            profile.get("name", ""),
            j(profile.get("skills", [])),
            profile.get("experience_years", 0),
            j(profile.get("preferred_roles", [])),
            j(profile.get("preferred_locations", [])),
            profile.get("min_salary", 0),
            profile.get("summary", ""),
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _serialize_json_fields(d: dict, fields: list[str]) -> dict:
    d = dict(d)
    for f in fields:
        if f in d and not isinstance(d[f], str):
            d[f] = json.dumps(d[f]) if d[f] is not None else None
    return d


def _deserialize_row(row) -> dict:
    if row is None:
        return {}
    d = dict(row)
    for key in ["skills", "fit_breakdown", "resume_bullets", "preferred_roles", "preferred_locations"]:
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key] = []
    if "remote" in d:
        d["remote"] = bool(d["remote"])
    return d
