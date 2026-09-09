from typing import Any, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    page: str = Field(..., description="Id of the page the user is currently looking at, e.g. 'traces'")
    question: str = Field(..., min_length=1, max_length=2000)
    project_state: dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class NavigateAction(BaseModel):
    type: str = "navigate"
    page: str


class AskResponse(BaseModel):
    answer: str
    action: Optional[NavigateAction] = None
    grounded_on: list[str] = Field(default_factory=list)
    session_id: str


class PageDoc(BaseModel):
    id: str
    title: str
    purpose: str
    prerequisites: str
    next_step: str


class SessionMessage(BaseModel):
    page: str
    question: str
    answer: str
    action: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
