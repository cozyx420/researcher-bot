from pydantic import BaseModel, Field, AnyHttpUrl
from typing import List, Optional, Literal


class Source(BaseModel):
    title: str
    url: AnyHttpUrl
    verdict: Literal["reliable", "tentative"] = "tentative"
    notes: Optional[str] = None


class ResearchPayload(BaseModel):
    query: str
    focus: Optional[str] = None
    max_sources: int = Field(default=5, ge=1, le=20)
    allow_domains: Optional[List[str]] = None


class ResearchResult(BaseModel):
    summary: str
    bullets: List[str]
    sources: List[Source]
    confidence: float = Field(ge=0.0, le=1.0)
