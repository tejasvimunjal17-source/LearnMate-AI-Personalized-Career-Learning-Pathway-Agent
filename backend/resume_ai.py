"""
backend/resume_ai.py
------------------------
AI-powered Resume Builder features: professional summary generation,
bullet-point improvement (action-verb enhancement), grammar polish,
cover letter / LinkedIn "About" / portfolio blurb / HR email / interview
question generation, and resume import (PDF/DOCX -> auto-filled fields).

All of these are thin prompt-formatting wrappers around the existing
backend.openrouter_client.generate_chat_response() - no new API client,
no new credentials, no new dependency. Every function degrades to a
short, friendly, non-crashing string if OpenRouter isn't configured or
the request fails, exactly like generate_chat_response() itself does,
so a missing/expired API key never breaks the Resume Builder page.

This module does NOT reimplement ATS scoring or resume analysis - that
logic lives entirely in backend/resume_review.py (via backend/
resume_ats.py, which wraps it). resume_ai.py only handles generative
(LLM) features.

Reads profile.target_role / profile.experience_level / profile.summary
(the additive ResumeProfile fields) via getattr(..., default) rather
than direct attribute access, so this module stays correct even if it's
ever imported against an older ResumeProfile snapshot mid-deploy.
"""

from __future__ import annotations

import json
import re

from backend.resume_store import ResumeProfile
from backend.openrouter_client import generate_chat_response
from backend.logger_setup import get_logger

logger = get_logger(__name__)

_FAILURE_MARKERS = ("isn't fully configured", "please type a question")

_IMPORT_SCHEMA_HINT = """{
  "first_name": "", "last_name": "", "email": "",
  "target_role": "", "summary": "",
  "education": "free text, one block per qualification, oldest or newest first as in the source",
  "skills": ["skill1", "skill2"],
  "internships": [{"role": "", "company": "", "duration": "", "description": ""}],
  "projects": [{"title": "", "tech_stack": "", "description": ""}],
  "certificates": [{"name": "", "issuer": "", "year": ""}],
  "achievements": "one per line as free text",
  "hobbies": ["hobby1", "hobby2"]
}"""


def _looks_like_config_error(reply: str) -> bool:
    lower = reply.lower()
    return any(marker in lower for marker in _FAILURE_MARKERS)


def _profile_context(profile: ResumeProfile) -> str:
    parts = [f"Name: {profile.full_name}"]
    target_role = getattr(profile, "target_role", "") or ""
    experience_level = getattr(profile, "experience_level", "") or "Fresher"
    if target_role:
        parts.append(f"Target role: {target_role}")
    parts.append(f"Experience level: {experience_level}")
    if profile.education:
        parts.append(f"Education:\n{profile.education}")
    if profile.skills:
        parts.append(f"Skills: {', '.join(profile.skills)}")
    if profile.internships:
        exp = "; ".join(
            f"{i.role} at {i.company} ({i.duration}): {i.description}" for i in profile.internships
        )
        parts.append(f"Experience: {exp}")
    if profile.projects:
        proj = "; ".join(f"{p.title} ({p.tech_stack}): {p.description}" for p in profile.projects)
        parts.append(f"Projects: {proj}")
    if profile.certificates:
        cert = "; ".join(f"{c.name} - {c.issuer} ({c.year})" for c in profile.certificates)
        parts.append(f"Certificates: {cert}")
    if profile.achievements:
        parts.append(f"Achievements: {profile.achievements}")
    return "\n".join(parts)


def generate_professional_summary(profile: ResumeProfile) -> str:
    """Draft a 2-3 sentence professional summary purely from existing profile data."""
    prompt = (
        "Write a 2-3 sentence, first-person-implied (no 'I') professional resume "
        "summary based ONLY on the facts below - do not invent employers, skills, "
        "or achievements that aren't listed. Keep it under 55 words, no markdown, "
        "plain text only.\n\n" + _profile_context(profile)
    )
    return generate_chat_response(prompt).strip()


def improve_bullet_point(text: str, target_role: str = "") -> str:
    """Rewrite one bullet/description with a strong action verb and measurable impact framing."""
    if not text or not text.strip():
        return text
    role_hint = f" for a {target_role} role" if target_role else ""
    prompt = (
        f"Rewrite this single resume bullet point{role_hint} to start with a strong "
        "action verb, be concise (under 25 words), and quantify impact only if a "
        "number is already implied by the text - never invent metrics. Return ONLY "
        f"the rewritten bullet, no quotes, no explanation:\n\n{text.strip()}"
    )
    return generate_chat_response(prompt).strip().strip('"')


def polish_grammar(text: str) -> str:
    """Light grammar/clarity pass over a block of resume text."""
    if not text or not text.strip():
        return text
    prompt = (
        "Fix grammar, spelling, and clarity issues in the following resume text. "
        "Keep the meaning and facts identical - do not add new claims. Return ONLY "
        f"the corrected text:\n\n{text.strip()}"
    )
    return generate_chat_response(prompt).strip()


def generate_cover_letter(profile: ResumeProfile, company: str = "") -> str:
    company_line = f" for a role at {company}" if company else ""
    prompt = (
        f"Write a concise, professional 3-paragraph cover letter{company_line}, "
        "based only on the candidate facts below. No placeholders like [Company] "
        "left unfilled if a company name is given; otherwise use 'your company'. "
        "Plain text, no markdown.\n\n" + _profile_context(profile)
    )
    return generate_chat_response(prompt).strip()


def generate_linkedin_about(profile: ResumeProfile) -> str:
    prompt = (
        "Write a LinkedIn 'About' section (120-180 words, first-person, warm but "
        "professional tone) based only on the facts below. Plain text, no markdown, "
        "no hashtags.\n\n" + _profile_context(profile)
    )
    return generate_chat_response(prompt).strip()


def generate_interview_questions(profile: ResumeProfile, count: int = 6) -> str:
    prompt = (
        f"Based on this candidate's resume, list exactly {count} likely interview "
        "questions they should prepare for (mix of technical and behavioral, tied "
        "to their actual projects/skills/experience). Return as a plain numbered "
        "list, one question per line, no extra commentary.\n\n" + _profile_context(profile)
    )
    return generate_chat_response(prompt).strip()


def generate_portfolio_blurb(profile: ResumeProfile) -> str:
    prompt = (
        "Write a short (60-90 word) personal portfolio-website homepage "
        "introduction based only on the facts below. Confident, plain text, no "
        "markdown.\n\n" + _profile_context(profile)
    )
    return generate_chat_response(prompt).strip()


def generate_hr_email(profile: ResumeProfile, purpose: str = "job application follow-up") -> str:
    prompt = (
        f"Write a short, polite professional email to an HR recruiter for the "
        f"purpose of: {purpose}. Base it only on the facts below. Include a subject "
        f"line as 'Subject: ...' on the first line, then the email body.\n\n"
        + _profile_context(profile)
    )
    return generate_chat_response(prompt).strip()


def parse_resume_text_to_fields(raw_text: str) -> dict | None:
    """Parse extracted resume text into a dict matching the Resume Builder's
    fields, for the "Import Resume to auto-fill the form" feature.

    Returns None (rather than raising) if the AI reply isn't valid/parsable
    JSON, so the caller can show a friendly "couldn't read that file" message
    instead of crashing.
    """
    if not raw_text or not raw_text.strip():
        return None

    prompt = (
        "Extract this resume's content into STRICT JSON only - no markdown "
        "fences, no commentary, matching exactly this shape (omit nothing, "
        "use empty string/list for anything not found):\n\n"
        f"{_IMPORT_SCHEMA_HINT}\n\nResume text:\n{raw_text.strip()[:6000]}"
    )
    reply = generate_chat_response(prompt)
    if _looks_like_config_error(reply):
        return None

    # Strip ```json fences if the model added them despite instructions.
    cleaned = re.sub(r"^```(?:json)?|```$", "", reply.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except (json.JSONDecodeError, TypeError):
        logger.warning("Resume import: AI reply wasn't valid JSON.")
        return None
