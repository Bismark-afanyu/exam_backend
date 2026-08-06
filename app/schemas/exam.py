from pydantic import BaseModel, Field

# ---------------------------------------------------------
# Artificial Intelligence Parsing Schemas (Nested)
# ---------------------------------------------------------
# These schemas are used by the LLM to output a fully structured
# document in one pass. A future ingestion service will flatten
# these into the normalized relational Firestore collections.


class SubquestionData(BaseModel):
    subquestion_identifier: str = Field(
        description="Identifier like 'a', 'b', 'i', 'ii'"
    )
    text: str = Field(
        description="Full text of the subquestion. ALL mathematical formulas, fractions, matrices, and symbols MUST be formatted as compliant LaTeX strings (e.g., \\frac{a}{b}, x^2, \\int). Use SINGLE backslashes."
    )
    marks: int = Field(
        description="Marks allocated specifically for this sub-part (use 0 if not stated)"
    )


class DiagramData(BaseModel):
    description: str = Field(
        description="Short description of what the diagram shows (if present)"
    )


class FigureData(BaseModel):
    figure_type: str = Field(description="Type of figure: 'table', 'graph', or 'chart'")


class QuestionData(BaseModel):
    question_number: str = Field(
        description="The question number in the paper (e.g., '1', '2')"
    )
    question_text: str = Field(
        description="Full text of the question (excluding subquestions if they are listed separately). ALL mathematical formulas, fractions, matrices, and symbols MUST be formatted as compliant LaTeX strings (e.g., \\frac{a}{b}, x^2, \\int). Use SINGLE backslashes."
    )
    topic: str = Field(
        description="Main topic classification (e.g., 'Mechanics', 'Genetics', 'Algebra')"
    )
    subtopic: str = Field(description="A highly detailed subtopic classification")
    marks_total: int = Field(description="Total marks for the entire question")
    question_type: str = Field(
        description="e.g., 'Theory', 'Calculation', 'Multiple Choice', 'Essay'"
    )
    has_diagram: bool = Field(
        description="True if a diagram is explicitly included or referenced"
    )
    image_url: str | None = Field(
        description="URL of the question diagram if it exists"
    )
    has_figure: bool = Field(
        description="True if a figure/table is explicitly included or referenced"
    )
    has_subquestions: bool = Field(
        description="True if it contains sub-parts (a, b, c)"
    )

    subquestions: list[SubquestionData] = Field(
        description="List of specific sub-parts if the question is divided. Empty list if there are none."
    )
    diagrams: list[DiagramData] = Field(
        description="Details about diagrams referenced in this question. Empty list if there are none."
    )
    figures: list[FigureData] = Field(
        description="Details about figures/tables referenced in this question. Empty list if there are none."
    )


class ExamPaperData(BaseModel):
    subject: str = Field(
        description="Name of the subject (e.g., 'Pure Maths', 'Biology')"
    )
    level: str = Field(description="Exam level (e.g., 'A-Level', 'IGCSE', 'O-Level')")
    year: int = Field(description="Year the exam took place (e.g., 2024)")
    paper: int = Field(description="Paper number (e.g., 1, 2, or 3)")
    topics_covered: list[str] = Field(
        description="List of all main topics covered in this entire paper"
    )
    questions: list[QuestionData] = Field(
        description="List of all questions extracted from the exam paper."
    )


class ExamPamphletData(BaseModel):
    exams: list[ExamPaperData] = Field(
        description="List of all unique exam papers found in the document (grouped by subject, year, and paper number)."
    )
