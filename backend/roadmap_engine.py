"""
backend/roadmap_engine.py
---------------------------
Turns a validated StudentProfile into a personalized learning roadmap by
prompting the IBM Granite / watsonx.ai foundation model, using the
customizable instructions from `agent_instructions.py`.

Includes:
- Robust JSON extraction/parsing (models sometimes wrap JSON in prose).
- A deterministic offline fallback generator so the UI remains fully
  demonstrable even without valid watsonx.ai credentials.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from agent_instructions import build_system_prompt
from backend.watsonx_client import watsonx_client, WatsonxError
from backend.logger_setup import get_logger

logger = get_logger(__name__)


@dataclass
class StudentProfile:
    name: str
    career_goal: str
    current_level: str          # Beginner / Intermediate / Advanced
    study_hours_per_week: int
    preferred_domain: str
    learning_preference: str    # e.g. Videos, Reading, Hands-on projects, Mixed
    existing_skills: list[str] = field(default_factory=list)

    def as_prompt_block(self) -> str:
        skills = ", ".join(self.existing_skills) if self.existing_skills else "None specified"
        return f"""STUDENT PROFILE:
- Name: {self.name}
- Career Goal: {self.career_goal}
- Current Level: {self.current_level}
- Study Hours Per Week: {self.study_hours_per_week}
- Preferred Domain: {self.preferred_domain}
- Preferred Learning Style: {self.learning_preference}
- Existing Skills: {skills}

Generate a complete personalized learning roadmap for this student now, in
the exact JSON schema specified. Tailor pacing to {self.study_hours_per_week}
study hours/week and their "{self.current_level}" level."""


def _extract_json(raw_text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from model output."""
    text = raw_text.strip()

    # Strip common markdown code fences
    text = re.sub(r"^```(?:json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to grabbing the outermost {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse extracted JSON block: %s", exc)

    raise ValueError("Model response did not contain valid JSON.")


def generate_roadmap(profile: StudentProfile) -> dict[str, Any]:
    """
    Generate a roadmap for the given profile.
    Tries watsonx.ai first; falls back to a rule-based offline roadmap if
    the API is not configured or fails, so the app always stays usable.
    """
    system_prompt = build_system_prompt(profile.preferred_domain)
    user_prompt = profile.as_prompt_block()

    try:
        raw = watsonx_client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_new_tokens=3000,
            temperature=0.5,
        )
        roadmap = _extract_json(raw)
        roadmap["_source"] = "watsonx.ai (IBM Granite)"
        logger.info("Roadmap generated via watsonx.ai for '%s'", profile.name)
        return roadmap
    except (WatsonxError, ValueError) as exc:
        logger.warning(
            "Falling back to offline roadmap generator (%s). Reason: %s",
            profile.name, exc,
        )
        roadmap = _offline_fallback_roadmap(profile)
        roadmap["_source"] = "offline fallback (watsonx.ai unavailable)"
        roadmap["_fallback_reason"] = str(exc)
        return roadmap
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        # Anything unexpected (network layer edge cases, malformed
        # responses, etc.) must still degrade gracefully rather than
        # crash the UI - requirement is "never crash, always fall back."
        logger.exception(
            "Unexpected error generating roadmap via watsonx.ai for '%s'; "
            "falling back to offline roadmap.", profile.name,
        )
        roadmap = _offline_fallback_roadmap(profile)
        roadmap["_source"] = "offline fallback (watsonx.ai unavailable)"
        roadmap["_fallback_reason"] = f"Unexpected error: {exc}"
        return roadmap


def _duration_for_level(level: str) -> int:
    return {"Beginner": 14, "Intermediate": 10, "Advanced": 6}.get(level, 10)


def _offline_fallback_roadmap(profile: StudentProfile) -> dict[str, Any]:
    """Deterministic, template-based roadmap used when the LLM is unreachable."""
    weeks = _duration_for_level(profile.current_level)
    domain = profile.preferred_domain

    themes = [
        "Foundations & Environment Setup",
        "Core Concepts I",
        "Core Concepts II",
        "Hands-on Tooling",
        "Applied Practice I",
        "Applied Practice II",
        "Intermediate Techniques",
        "Real-world Datasets/Projects",
        "Portfolio Project I",
        "Portfolio Project II",
        "Advanced Topics",
        "Interview Preparation",
        "Capstone Build",
        "Capstone Polish & Review",
    ]

    milestones = []
    for i in range(weeks):
        theme = themes[i % len(themes)]
        milestones.append({
            "week": i + 1,
            "title": f"{theme} - {domain}",
            "key_skills": [f"{domain} fundamental #{i + 1}a", f"{domain} fundamental #{i + 1}b"],
            "recommended_courses": [f"Intro to {domain} - Week {i + 1} topic (Coursera/edX)"],
            "mini_project": f"Build a small {domain.lower()} exercise applying week {i + 1} concepts.",
            "practice_tasks": ["Complete 3 practice exercises", "Review and summarize key notes"],
        })

    return {
        "summary": (
            f"This is a starter roadmap for {profile.name}, targeting "
            f"'{profile.career_goal}' in {domain}, paced for "
            f"{profile.study_hours_per_week} hrs/week at a "
            f"{profile.current_level.lower()} level. "
            f"(Generated offline - connect watsonx.ai for a fully "
            f"personalized, AI-generated roadmap.)"
        ),
        "estimated_duration_weeks": weeks,
        "weekly_milestones": milestones,
        "capstone_project": f"Build and deploy an end-to-end {domain.lower()} project "
                             f"that demonstrates your target role's core competencies.",
        "certifications": [
            "IBM SkillsBuild (free, domain-relevant badges)",
            f"Professional Certificate in {domain} (Coursera/edX)",
            "Relevant industry certification for your target role",
        ],
        "skill_gap_analysis": [
            {
                "skill": skill or "Core skill",
                "current_level": "Basic" if skill in profile.existing_skills else "None",
                "required_level": "Intermediate",
                "priority": "High",
            }
            for skill in (profile.existing_skills or [f"{domain} fundamentals"])
        ],
    }
