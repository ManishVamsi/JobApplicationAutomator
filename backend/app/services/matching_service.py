"""Abstract matching service interface and data types.

Allows swapping between Groq (production) and Ollama (local dev)
without changing business logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ResumeData:
    """Structured resume data extracted by LLM."""

    skills: list[str] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    years_of_experience: int = 0
    raw_text: str = ""


@dataclass
class JobData:
    """Job posting data for scoring."""

    job_index: int
    title: str
    company: str
    description: str
    requirements: str = ""
    location: str = ""


@dataclass
class JobScore:
    """LLM scoring result for a job posting."""

    job_index: int
    score: float  # 0-100
    rationale: str
    sponsorship: str = "unknown"  # yes | no | unknown
    country: str = "unknown"


@dataclass
class PostData:
    """LinkedIn post data for scoring."""

    post_index: int
    raw_text: str
    poster_name: str = ""


@dataclass
class PostScore:
    """LLM scoring result for a LinkedIn post."""

    post_index: int
    score: float  # 0-100
    rationale: str
    sponsorship: str = "unknown"
    country: str = "unknown"


class MatchingService(ABC):
    """Abstract interface for LLM-based resume matching.

    Implementations: GroqMatchingService (production), OllamaMatchingService (local).
    """

    @abstractmethod
    async def parse_resume(self, text: str) -> ResumeData:
        """Extract structured data from resume text."""
        ...

    @abstractmethod
    async def score_jobs(
        self, resume: ResumeData, jobs: list[JobData]
    ) -> list[JobScore]:
        """Score a batch of jobs against a resume (0-100)."""
        ...

    @abstractmethod
    async def score_linkedin_posts(
        self, resume: ResumeData, posts: list[PostData]
    ) -> list[PostScore]:
        """Score a batch of LinkedIn posts against a resume (0-100)."""
        ...

    @abstractmethod
    async def classify_sponsorship(self, text: str) -> str:
        """Classify sponsorship status from text: yes | no | unknown."""
        ...

    @abstractmethod
    async def classify_country(self, text: str) -> str:
        """Extract country from job/post text."""
        ...
