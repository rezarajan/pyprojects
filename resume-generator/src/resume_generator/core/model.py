"""
Minimal dataclasses for Resume and Entry objects. Expand as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


@dataclass
class Entry:
    title: str
    organization: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Entry":
        return Entry(
            title=d.get("title", ""),
            organization=d.get("organization"),
            location=d.get("location"),
            start_date=d.get("start_date"),
            end_date=d.get("end_date"),
            bullets=d.get("bullets", []) or [],
        )


@dataclass
class Resume:
    name: str
    contact: Dict[str, str] = field(default_factory=dict)
    education: List[Entry] = field(default_factory=list)
    experience: List[Entry] = field(default_factory=list)
    projects: List[Entry] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Resume":
        name = d.get("name") or d.get("personal", {}).get("name")
        if not name:
            raise ValueError("Missing required field: name")

        contact = d.get("contact", {})

        def build_entries(key: str) -> List[Entry]:
            items = d.get(key, []) or []
            return [Entry.from_dict(i) for i in items]

        education = build_entries("education")
        experience = build_entries("experience")
        projects = build_entries("projects")
        skills = d.get("skills", []) or []

        return Resume(
            name=name,
            contact=contact,
            education=education,
            experience=experience,
            projects=projects,
            skills=skills,
        )
