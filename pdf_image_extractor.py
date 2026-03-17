# pdf_image_extractor.py
import fitz  # PyMuPDF
import re
from PIL import Image
import io
import json
import os
from pathlib import Path


class PDFImageExtractor:
    def __init__(self, pdf_path, output_dir="public/images/exam-images"):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def extract_images_and_figures(self):
        """Extract all images and figures from PDF with their context"""
        doc = fitz.open(self.pdf_path)
        images_data = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()

            # Get images from the page
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)

                # Convert to PIL Image
                if pix.n - pix.alpha < 4:  # can be saved as PNG
                    img_data = pix.tobytes("png")
                    pil_image = Image.open(io.BytesIO(img_data))
                else:  # convert to RGB first
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                    img_data = pix.tobytes("png")
                    pil_image = Image.open(io.BytesIO(img_data))

                # Find the image's position and surrounding text
                image_blocks = self.find_image_blocks(page, xref)

                # Generate filename
                filename = f"page_{page_num+1}_img_{img_index+1}.png"
                filepath = os.path.join(self.output_dir, filename)

                # Save image
                pil_image.save(filepath, "PNG")

                # Find associated question number
                question_num = self.find_associated_question(image_blocks, page_text)

                # Find figure/caption text
                caption = self.extract_caption(page, image_blocks)

                images_data.append({
                    "filename": filename,
                    "page": page_num + 1,
                    "question_number": question_num,
                    "caption": caption,
                    "bbox": str(image_blocks),
                    "path": f"/images/exam-images/{filename}"
                })

                pix = None  # free memory

        doc.close()
        return images_data

    def find_image_blocks(self, page, xref):
        """Find the position of the image on the page"""
        try:
            blocks = page.get_image_bbox(xref)
            return [blocks] if blocks else []
        except Exception:
            return []

    def find_associated_question(self, image_blocks, page_text):
        """Find which question number this image belongs to"""
        if not image_blocks:
            return None

        # Look for question numbers near the image
        lines = page_text.split('\n')
        question_pattern = r'^(\d+)\.'

        # Simple heuristic: find the nearest question number above the image
        last_question = None
        for i, line in enumerate(lines):
            match = re.match(question_pattern, line.strip())
            if match:
                last_question = int(match.group(1))

        return last_question

    def extract_caption(self, page, image_blocks):
        """Extract caption text near the image"""
        if not image_blocks:
            return ""

        # Get text near the image (above/below)
        words = page.get_text("words")
        nearby_text = []

        for word in words:
            # Check if word is within 50 pixels of image
            if self.is_text_near_image(word, image_blocks[0]):
                nearby_text.append(word[4])

        return ' '.join(nearby_text[:10])  # First 10 words near image

    def is_text_near_image(self, word, image_bbox, threshold=50):
        """Check if text is near the image"""
        word_rect = fitz.Rect(word[:4])
        image_rect = fitz.Rect(image_bbox)

        # Check vertical proximity
        if abs(word_rect.y0 - image_rect.y1) < threshold:
            return True
        if abs(word_rect.y1 - image_rect.y0) < threshold:
            return True

        return False


# PDF Text Extractor with Structure
class PDFStructureExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)

    def extract_metadata(self):
        """Extract basic document metadata"""
        return {
            "title": self.doc.metadata.get("title", ""),
            "author": self.doc.metadata.get("author", ""),
            "subject": self.doc.metadata.get("subject", ""),
            "page_count": len(self.doc),
        }

    def extract_exam_structure(self):
        """Extract exam structure with questions and references to images"""
        structure = {
            "metadata": self.extract_metadata(),
            "questions": [],
            "images": []
        }

        current_question = None
        current_question_text = []
        last_page = 0

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            last_page = page_num

            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()

                            # Check if this is a new question
                            question_match = re.match(r'^(\d+)\.', text)
                            if question_match:
                                # Save previous question
                                if current_question:
                                    structure["questions"].append({
                                        "number": current_question,
                                        "text": ' '.join(current_question_text),
                                        "page": page_num
                                    })

                                # Start new question
                                current_question = int(question_match.group(1))
                                current_question_text = [text]
                            else:
                                if current_question:
                                    current_question_text.append(text)

        # Add last question
        if current_question:
            structure["questions"].append({
                "number": current_question,
                "text": ' '.join(current_question_text),
                "page": last_page
            })

        return structure
