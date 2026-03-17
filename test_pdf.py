import sys
import json
from pathlib import Path
from app.services.pdf.processor import ExamPaperProcessor

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_pdf.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)

    print(f"📄 Processing: {pdf_path.name}...")
    
    try:
        processor = ExamPaperProcessor()
        result = processor.process_exam_paper(pdf_path)
        
        # Print a nice summary instead of dumping raw text
        print("\n✅ Extraction Successful!")
        print("-" * 40)
        print(f"Pages         : {result['text_content']['pages_count']}")
        print(f"Text length   : {len(result['text_content']['text']['pymupdf'])} characters")
        print(f"Tables found  : {len(result['tables']['pdfplumber'])}")
        print("-" * 40)
        
        # Save output to a file so it's easy to read
        output_file = "extraction_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        print(f"💾 Full results saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
