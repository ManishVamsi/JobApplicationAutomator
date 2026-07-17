"""Groq LLM matching service — production implementation.

Uses Groq API via httpx (not the groq SDK, to keep deps minimal).
Batch-scores 5 jobs per LLM call with structured JSON output.
"""

import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.matching_service import (
    JobData,
    JobScore,
    MatchingService,
    PostData,
    PostScore,
    ResumeData,
)

logger = get_logger(__name__)
settings = get_settings()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

RESUME_PARSE_SYSTEM = """You are a resume parsing expert. Extract structured data from the resume text.
Output valid JSON with this exact schema:
{
  "skills": ["skill1", "skill2"],
  "experience": [{"title": "", "company": "", "duration": "", "description": ""}],
  "education": [{"degree": "", "institution": "", "year": ""}],
  "roles": ["target role 1", "target role 2"],
  "years_of_experience": 0
}"""

JOB_SCORE_SYSTEM = """You are a job matching expert. Given a candidate's resume data and a batch of job postings,
score each job 0-100 for match quality based on skills, experience, and role alignment.
Output valid JSON array with this exact schema:
[{"job_index": 0, "score": 85, "rationale": "Strong match because...", "sponsorship": "yes|no|unknown", "country": "US"}]"""

POST_SCORE_SYSTEM = """You are a recruiter post analyst. Given a candidate's resume and LinkedIn posts about hiring,
score each post 0-100 for relevance to the candidate.
Output valid JSON array with this exact schema:
[{"post_index": 0, "score": 75, "rationale": "Relevant because...", "sponsorship": "unknown", "country": "US"}]"""


class GroqMatchingService(MatchingService):
    """Groq API implementation of the matching service."""

    def __init__(self) -> None:
        self._api_key = settings.GROQ_API_KEY
        self._model = settings.LLM_MODEL
        self._batch_size = settings.LLM_BATCH_SIZE

    async def _call_groq(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Make a single Groq API call."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )

            if response.status_code == 429:
                logger.warning("Groq rate limit hit, will retry")
                raise httpx.HTTPStatusError(
                    "Rate limited", request=response.request, response=response
                )

            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _parse_json_response(self, text: str) -> Any:
        """Parse JSON from LLM response, handling markdown code blocks."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        return json.loads(cleaned)

    async def parse_resume(self, text: str) -> ResumeData:
        """Extract structured data from resume text via Groq."""
        result = await self._call_groq(
            RESUME_PARSE_SYSTEM,
            f"Parse this resume:\n\n{text[:8000]}",
        )
        data = self._parse_json_response(result)
        return ResumeData(
            skills=data.get("skills", []),
            experience=data.get("experience", []),
            education=data.get("education", []),
            roles=data.get("roles", []),
            years_of_experience=data.get("years_of_experience", 0),
            raw_text=text,
        )

    async def score_jobs(
        self, resume: ResumeData, jobs: list[JobData]
    ) -> list[JobScore]:
        """Score jobs in batches of LLM_BATCH_SIZE (default 5)."""
        all_scores: list[JobScore] = []
        resume_json = json.dumps({
            "skills": resume.skills,
            "experience": resume.experience,
            "roles": resume.roles,
            "years_of_experience": resume.years_of_experience,
        })

        for i in range(0, len(jobs), self._batch_size):
            batch = jobs[i : i + self._batch_size]
            jobs_json = json.dumps([
                {
                    "job_index": j.job_index,
                    "title": j.title,
                    "company": j.company,
                    "description": j.description[:2000],
                    "requirements": j.requirements[:1000],
                    "location": j.location,
                }
                for j in batch
            ])

            result = await self._call_groq(
                JOB_SCORE_SYSTEM,
                f"Resume: {resume_json}\n\nJobs: {jobs_json}",
            )
            parsed = self._parse_json_response(result)

            # Handle both {"results": [...]} and [...] formats
            scores_list = parsed if isinstance(parsed, list) else parsed.get("results", [])

            for s in scores_list:
                all_scores.append(JobScore(
                    job_index=s["job_index"],
                    score=float(s["score"]),
                    rationale=s.get("rationale", ""),
                    sponsorship=s.get("sponsorship", "unknown"),
                    country=s.get("country", "unknown"),
                ))

        return all_scores

    async def score_linkedin_posts(
        self, resume: ResumeData, posts: list[PostData]
    ) -> list[PostScore]:
        """Score LinkedIn posts in batches."""
        all_scores: list[PostScore] = []
        resume_json = json.dumps({
            "skills": resume.skills,
            "roles": resume.roles,
            "years_of_experience": resume.years_of_experience,
        })

        for i in range(0, len(posts), self._batch_size):
            batch = posts[i : i + self._batch_size]
            posts_json = json.dumps([
                {
                    "post_index": p.post_index,
                    "raw_text": p.raw_text[:2000],
                    "poster_name": p.poster_name,
                }
                for p in batch
            ])

            result = await self._call_groq(
                POST_SCORE_SYSTEM,
                f"Resume: {resume_json}\n\nPosts: {posts_json}",
            )
            parsed = self._parse_json_response(result)
            scores_list = parsed if isinstance(parsed, list) else parsed.get("results", [])

            for s in scores_list:
                all_scores.append(PostScore(
                    post_index=s["post_index"],
                    score=float(s["score"]),
                    rationale=s.get("rationale", ""),
                    sponsorship=s.get("sponsorship", "unknown"),
                    country=s.get("country", "unknown"),
                ))

        return all_scores

    async def classify_sponsorship(self, text: str) -> str:
        """Classify sponsorship status from job/post text."""
        result = await self._call_groq(
            "Classify if this job offers visa sponsorship. Respond with JSON: {\"sponsorship\": \"yes|no|unknown\"}",
            text[:2000],
        )
        data = self._parse_json_response(result)
        return data.get("sponsorship", "unknown")

    async def classify_country(self, text: str) -> str:
        """Extract country from job/post text."""
        result = await self._call_groq(
            "Extract the country of this job. Respond with JSON: {\"country\": \"XX\"}",
            text[:2000],
        )
        data = self._parse_json_response(result)
        return data.get("country", "unknown")
