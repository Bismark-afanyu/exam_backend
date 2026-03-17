# # extract_all.py
# import json
# from pathlib import Path
# from pdf_image_extractor import PDFImageExtractor, PDFStructureExtractor


# def extract_all_images():
#     """Extract images from all PDFs and create mapping file"""

#     pdf_files = [
#         "GCE A Level 2024 MeetLearn Pure Maths Mechanics 2.pdf"
#     ]

#     all_images = []

#     for pdf_file in pdf_files:
#         pdf_path = Path(pdf_file)
#         if not pdf_path.exists():
#             print(f"⚠️  Skipping {pdf_file} — file not found")
#             continue

#         print(f"📄 Processing {pdf_file}...")

#         # Extract images
#         extractor = PDFImageExtractor(pdf_file)
#         images = extractor.extract_images_and_figures()

#         # Add source PDF to each image
#         for img in images:
#             img["source_pdf"] = pdf_file

#         all_images.extend(images)

#         # Also extract structure
#         structure_extractor = PDFStructureExtractor(pdf_file)
#         structure = structure_extractor.extract_exam_structure()

#         # Save structure
#         structure_file = f"{pdf_path.stem}_structure.json"
#         with open(structure_file, "w") as f:
#             json.dump(structure, f, indent=2)
#         print(f"  📝 Structure saved to: {structure_file}")

#     # Save all images mapping
#     mapping_dir = Path("public/images")
#     mapping_dir.mkdir(parents=True, exist_ok=True)
#     mapping_file = mapping_dir / "image_mapping.json"

#     with open(mapping_file, "w") as f:
#         json.dump(all_images, f, indent=2)

#     print(f"\n✅ Extracted {len(all_images)} images total")
#     print(f"💾 Image mapping saved to: {mapping_file}")
#     return all_images


# if __name__ == "__main__":
#     extract_all_images()
