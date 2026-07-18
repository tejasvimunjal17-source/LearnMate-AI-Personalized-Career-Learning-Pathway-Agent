"""
utils/validators.py
----------------------
Input validation helpers for the student profile form. Returns a list of
human-readable error messages (empty list = valid).
"""

from __future__ import annotations

import re

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s.'-]{1,59}$")


def validate_profile(
    name: str,
    career_goal: str,
    current_level: str,
    study_hours_per_week: int,
    preferred_domain: str,
    learning_preference: str,
    existing_skills: list[str],
) -> list[str]:
    errors: list[str] = []

    if not name or not name.strip():
        errors.append("Please enter your full name.")
    elif not NAME_RE.match(name.strip()):
        errors.append("Name should contain only letters, spaces, and basic punctuation (2-60 chars).")

    if not career_goal or len(career_goal.strip()) < 3:
        errors.append("Please describe your career goal (at least 3 characters).")
    elif len(career_goal.strip()) > 200:
        errors.append("Career goal should be under 200 characters.")

    if current_level not in {"Beginner", "Intermediate", "Advanced"}:
        errors.append("Please select a valid current level.")

    if not isinstance(study_hours_per_week, (int, float)) or study_hours_per_week <= 0:
        errors.append("Study hours per week must be a positive number.")
    elif study_hours_per_week > 100:
        errors.append("Study hours per week seems unrealistically high (max 100).")

    if not preferred_domain or not preferred_domain.strip():
        errors.append("Please select your preferred domain.")

    if not learning_preference or not learning_preference.strip():
        errors.append("Please select your preferred learning style.")

    if existing_skills and len(existing_skills) > 30:
        errors.append("Please list 30 or fewer existing skills.")

    return errors
