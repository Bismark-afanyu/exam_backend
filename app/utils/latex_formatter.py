import re


def sanitize_latex(text: str) -> str:
    r"""
    Cleans up LLM-generated LaTeX strings to guarantee compatibility with the frontend.
    Ensures that mathematical content is wrapped in \( ... \) for inline math,
    and \[ ... \] for block math.
    """
    if not text:
        return text

    # 1. Convert any legacy double dollar signs $$ to \[ \] (block math)
    # We do a greedy match for pairs of $$...$$
    text = re.sub(r"\$\$(.*?)\$\$", r"\[\1\]", text, flags=re.DOTALL)

    # 2. Convert any single dollar signs $ to \( \) (inline math)
    # Be careful not to match literal dollar signs if any (unlikely in exams)
    text = re.sub(r"\$(.*?)\$", r"\(\1\)", text, flags=re.DOTALL)

    # 3. Fix Escaping. Ensure we have single backslashes in the string.
    # We replace literal '\\' with '\'
    return text.replace("\\\\", "\\")


def format_exam_paper_latex(data: dict) -> dict:
    """Recursively traverses the structured dict and sanitizes text fields."""
    _format_single_exam_latex(data)
    return data


def _format_single_exam_latex(exam_data: dict):
    """Helper to format a single exam's questions and subquestions."""
    if "questions" in exam_data:
        for q in exam_data["questions"]:
            if "question_text" in q:
                q["question_text"] = sanitize_latex(q["question_text"])

            if "subquestions" in q:
                for sq in q["subquestions"]:
                    if "text" in sq:
                        sq["text"] = sanitize_latex(sq["text"])
