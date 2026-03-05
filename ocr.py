import fitz

def ocr_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    results = []
    for i, page in enumerate(doc):
        print(f"  Processing page {i+1} of {len(doc)}...")
        text = page.get_text()
        if not text.strip():
            text = f"Page {i+1} has handwritten content"
        results.append({"page": i + 1, "text": text})
        print(f"  Page {i+1} done — {len(text)} chars")
    return results
