from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import json


class JobPosting(BaseModel):
    id: Optional[int] = None
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    raw_description: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0.0
    salary_min: int = 0
    salary_max: int = 0
    remote: bool = False
    fit_score: Optional[float] = None
    fit_breakdown: Optional[dict] = None
    scraped_at: Optional[str] = None
    parsed_at: Optional[str] = None

    @field_validator("skills", mode="before")
    @classmethod
    def coerce_skills(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []

    @field_validator("experience_years", mode="before")
    @classmethod
    def coerce_experience(cls, v):
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0


class FitBreakdown(BaseModel):
    skill_match: float = 0.0
    experience_match: float = 0.0
    role_match: float = 0.0
    salary_match: float = 0.0
    total: float = 0.0
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    notes: str = ""


class Application(BaseModel):
    id: Optional[int] = None
    job_id: int
    status: str = "saved"
    applied_at: Optional[str] = None
    notes: str = ""
    cover_letter: str = ""
    resume_bullets: list[str] = Field(default_factory=list)
    updated_at: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    fit_score: Optional[float] = None

    @field_validator("resume_bullets", mode="before")
    @classmethod
    def coerce_bullets(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []


class CandidateProfile(BaseModel):
    id: int = 1
    name: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0.0
    preferred_roles: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    min_salary: int = 0
    summary: str = ""

    @field_validator("skills", "preferred_roles", "preferred_locations", mode="before")
    @classmethod
    def coerce_lists(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []


class InsightReport(BaseModel):
    total_applied: int = 0
    total_saved: int = 0
    phone_screens: int = 0
    onsites: int = 0
    offers: int = 0
    rejections: int = 0
    response_rate: float = 0.0
    avg_fit_responded: float = 0.0
    avg_fit_no_response: float = 0.0
    top_missing_skills: list[str] = Field(default_factory=list)
    days_in_pipeline: float = 0.0


class GeneratedContent(BaseModel):
    cover_letter: str = ""
    resume_bullets: list[str] = Field(default_factory=list)
    source: str = "template"
