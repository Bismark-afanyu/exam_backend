import json

from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.exam import ExamPaperData


class ExamAIParser:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Gemini LLM for structured parsing."""
        if not hasattr(settings, "GEMINI_API_KEY") or not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured in .env")

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name

    def parse_images(self, images_bytes: list[bytes]) -> ExamPaperData:
        """
        Sends sequential images of a single exam paper
        to Gemini's Multimodal Vision API.
        """
        prompt = r"""
        You are an expert educational AI designed to structure raw exam paper images into a strict relational database schema.

        IMPORTANT: The provided images represent ONE single exam paper (e.g., Physics A-Level 2024 Paper 1).
        Treat the entire document as a single exam paper.

        CRITICAL INSTRUCTIONS:
        1. Classify the 'subject', 'level', 'year', and 'paper' number for this exam paper.
        2. Identify ALL individual questions across all pages. Do NOT skip any questions.
        3. Determine if it has subquestions (e.g., '1(a)', '1(b)'). If so, separate them into the 'subquestions' array.
        4. PRESERVE NESTING: Many papers divide a sub-question further into sub-sub-parts, e.g., '1(a)(i)', '1(a)(ii)', '1(a)(iii)'. Keep these in the 'sub_subquestions' array of the correct parent sub-question ('a'). Do NOT flatten sub-sub-parts into the top-level 'subquestions' list.
        5. LINK IMAGES TO THE EXACT PART: When a figure, table, graph, or diagram accompanies a specific question, sub-question, or sub-sub-question, set that part's 'image_url' to a non-empty placeholder string (e.g., 'PENDING_UPLOAD') so the image can be attached to the correct part during ingestion. A table shown for '1(a)(iii)' must be recorded on that sub-sub-question, not on question '1'.
        6. Provide highly accurate 'topic' and 'subtopic' classification.
        7. Provide the 'marks_total' for questions, subquestions, and sub-sub-questions.
        8. Note any figures (tables, graphs) or diagrams referenced.
        9. EXTREMELY IMPORTANT - SUBJECT SENSITIVITY:
           - For non-scientific subjects where no math is present, return plain text only.
        10. EXTREMELY IMPORTANT - LATEX MATH FORMATTING (For Math/Science):
           - You MUST convert all mathematical formulas, fractions, limits, integrals, vectors, and special characters into pure LaTeX strings.
           - For INLINE math, wrap it in: \( ... \)
           - For BLOCK math, wrap it in: \[ ... \]
           - Use \text{} for words inside math.
           - Use SINGLE backslashes for commands.
        """

        # Build the multimodal contents using types.Part
        contents: list[types.ContentUnion] = [
            types.UserContent(parts=[types.Part.from_text(text=prompt)])
        ]

        for img_bytes in images_bytes:
            contents.append(
                types.UserContent(
                    parts=[types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")]
                )
            )

        try:
            # Use Gemini's Native Structured Output (JSON Schema)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExamPaperData,
                    temperature=0.1,  # Low temp for factual data extraction
                    max_output_tokens=65536,
                ),
            )
        except Exception as e:
            print(f"❌ Gemini AI Error: {str(e)}")
            raise e

        # Validate and return the Pydantic object
        extracted_data = json.loads(response.text)

        from app.utils.latex_formatter import format_exam_paper_latex

        formatted_data = format_exam_paper_latex(extracted_data)

        return ExamPaperData(**formatted_data)