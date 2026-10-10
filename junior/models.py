from typing import Literal
from pydantic import BaseModel, Field

Category = Literal["k8s_issue", "app_issue", "unclear"]

class AskRequest(BaseModel):
    question: str = Field(min_length=15, max_length=5000)

class Diagnosis(BaseModel):
    category: Category
    pod: str
    container: str
    summary: str
    cached: bool = False

class AskResponse(BaseModel):
    question: str
    diagnosis: list[Diagnosis] | None
    error: str | None
    environment: str
    version: str
