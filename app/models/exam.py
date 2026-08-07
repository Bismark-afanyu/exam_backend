from datetime import UTC, datetime

from pydantic import BaseModel, Field


# Base Domain Model
class BaseDomainModel(BaseModel):
    id: str | None = Field(None, description="Firestore document ID")
    created_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True


# ---------------------------------------------------------
# Exam Domain Entities (Normalized)
# ---------------------------------------------------------


class Year(BaseDomainModel):
    year: int
    name: list[str] = Field(
        default_factory=list, description="Subjects available that year"
    )


class Subject(BaseDomainModel):
    name: str
    level: str


class Topic(BaseDomainModel):
    name: str
    subtopics: list[str] = Field(default_factory=list)


class Question(BaseDomainModel):
    subject: str
    year: int
    paper: int
    question_number: str
    has_subquestions: bool
    question_text: str
    topic: str
    subtopic: str
    marks_total: int
    question_type: str
    has_diagram: bool
    has_figure: bool


class Subquestion(BaseDomainModel):
    question_id: str = Field(description="Reference to the parent Question ID")
    identifier: str = Field(description="Subpart identifier (e.g., 'a', 'b')")
    text: str
    marks: int | None = None
    image_url: str | None = None


class SubSubquestion(BaseDomainModel):
    subquestion_id: str = Field(description="Reference to the parent Subquestion ID")
    identifier: str = Field(description="Sub-subpart identifier (e.g., 'i', 'ii')")
    text: str
    marks: int | None = None
    image_url: str | None = None


class Diagram(BaseDomainModel):
    question_id: str = Field(description="Reference to the parent Question ID")
    diagram_url: str = Field(description="Firebase Storage URL")
    description: str


class Figure(BaseDomainModel):
    question_id: str = Field(description="Reference to the parent Question ID")
    figure_type: str = Field(description="table, graph, or chart")
    data_source: str = Field(description="URL/Path in Firebase Storage")
