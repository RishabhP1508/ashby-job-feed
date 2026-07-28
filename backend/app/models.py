"""Response models. The API returns a trimmed, normalized shape, not Ashby's raw payload."""
from __future__ import annotations

from pydantic import BaseModel


class Job(BaseModel):
    company: str
    title: str
    team: str = ""
    department: str = ""
    location: str = ""
    secondaryCount: int = 0
    workplaceType: str = ""
    employmentType: str = ""
    isRemote: bool = False
    countries: list[str] = []
    applyUrl: str = ""
    publishedAt: str | None = None


class BoardResponse(BaseModel):
    slug: str
    fetchedAt: str
    cached: bool
    count: int
    jobs: list[Job]
