import google.generativeai as genai
from app.schemas.exam import ExamPaperData
from app.core.config import settings
import json

class ExamAIParser:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Initialize the Gemini LLM for structured parsing."""
        if not hasattr(settings, "GEMINI_API_KEY") or not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured in .env")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(model_name)
    
    def parse_images(self, images_bytes: list[bytes]) -> ExamPaperData:
        """
        Sends sequential images of a scanned exam to Gemini's Multimodal Vision API.
        """
        prompt = r"""
        You are an expert educational AI designed to structure raw exam paper images into a strict relational database schema.
        
        Please read the text from these sequential images of an exam paper and return the data EXACTLY matching the provided JSON schema.
        
        CRITICAL INSTRUCTIONS:
        1. Classify the main 'subject', 'level', 'year', and 'paper' number from the headers (usually on the first page).
        2. Identify ALL individual questions across all pages correctly.
        3. Determine if it has subquestions (e.g., '1(a)', '1(b)'). If so, separate them into the 'subquestions' array. Do not leave them in the main question text.
        4. Provide highly accurate 'topic' and 'subtopic' classification based on the concepts being tested.
        5. Provide the 'marks_total' for questions and subquestions.
        6. Note any figures (tables, graphs) or diagrams referenced or shown near the questions.
        7. EXTREMELY IMPORTANT - SUBJECT SENSITIVITY:
           - For non-scientific subjects where no math is present (e.g., History, Geography, Literature), return plain text only. Do NOT add any LaTeX delimiters.
        8. EXTREMELY IMPORTANT - LATEX MATH FORMATTING (For Math/Science):
           - You MUST convert all mathematical formulas, fractions, limits, integrals, vectors, and special characters into pure LaTeX strings.
           - For INLINE math (math within a sentence), wrap it in: \( ... \)
           - For BLOCK math (formulas on their own line or complex expressions), wrap it in: \[ ... \]
           - Use \text{} for normal words when they appear inside a mathematical context.
           - EXAMPLES:
             * "Express \(\frac{3x^2 + x - 1}{(x+1)(x+2)}\) in partial fractions."
             * "If the roots of the quadratic equation \[x^2 + kx + 2 = 0\] are real, find the values of the constant \(k\)."
             * "(a) \text{ the values of the constants } a \text{ and } b"
             * "(b) \text{ the values of } x \text{ for which } f(x)=0"
             * "\mathbf{r} = 3\mathbf{i} + 6\mathbf{j} + \mathbf{k} + \lambda(2\mathbf{i} - \mathbf{k})"
           - Ensure you use SINGLE backslashes for commands (e.g., \frac, \int, \mathbf).
           - Do not use plain English text formatting for math parameters.
        """
        
        # Build the multimodal payload
        payload: list = [prompt]
        for img_bytes in images_bytes:
            payload.append(
                {"mime_type": "image/png", "data": img_bytes}
            )
        
        try:
            # Use Gemini's Native Structured Output (JSON Schema)
            response = self.model.generate_content(
                payload,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=ExamPaperData,
                    temperature=0.1 # Low temp for factual data extraction
                )
            )
        except Exception as e:
            print(f"❌ Gemini AI Error: {str(e)}")
            raise e
        
        # Validate and return the Pydantic object
        extracted_data = json.loads(response.text)
        
        from app.utils.latex_formatter import format_exam_paper_latex
        formatted_data = format_exam_paper_latex(extracted_data)
        
        return ExamPaperData(**formatted_data)
