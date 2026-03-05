import os
import shutil
import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fpdf import FPDF

from ocr import ocr_pdf
from chunker import chunk_text
from database import store_chunks, search_chunks, load_existing
from answerer import generate_answer, conversation_history

app = FastAPI(title="Note Assistant — Hackathon 2026")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

uploaded_pdfs = []

print("Starting Note Assistant...")
load_existing()
print("System ready.\n")


@app.get("/health")
def health():
    return {
        "status":      "running",
        "pdfs_loaded": len(uploaded_pdfs),
        "pdf_names":   uploaded_pdfs,
        "total_qa":    len(conversation_history)
    }


@app.get("/status")
def status():
    return {
        "status":      "running",
        "pdfs_loaded": len(uploaded_pdfs)
    }


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    print(f"Uploading: {file.filename}")

    path = f"./uploads/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    print("Running OCR...")
    pages = ocr_pdf(path)

    print("Chunking...")
    chunks = chunk_text(pages)

    print("Storing in DB...")
    store_chunks(chunks)

    uploaded_pdfs.append(file.filename)
    print(f"Done — {len(pages)} pages, {len(chunks)} chunks\n")

    return {
        "message":         "PDF processed successfully",
        "filename":        file.filename,
        "pages":           len(pages),
        "pages_processed": len(pages),
        "chunks":          len(chunks),
        "chunks_created":  len(chunks),
        "ocr_mode":        "gemini_vision"
    }


class AskRequest(BaseModel):
    question: str
    k: int = 4


@app.post("/ask")
def ask(req: AskRequest):
    print(f"Question: {req.question}")

    chunks = search_chunks(req.question, top_k=req.k)

    if not chunks:
        return {
            "answer":     "I don't have enough information in the notes to answer this.",
            "sources":    [],
            "confidence": 0.0
        }

    answer = generate_answer(req.question, chunks)

    sources = [
        {
            "source":     c["source"],
            "page":       c["page"],
            "section":    c["source"].split(", ")[-1] if ", " in c["source"] else "Section 1",
            "excerpt":    c["text"][:150] + "...",
            "confidence": round(c.get("score", 0) * 100, 1)
        }
        for c in chunks
    ]

    top_score = sources[0]["confidence"] if sources else 0

    print(f"Answer: {answer[:100]}...")
    print(f"Sources: {[s['source'] for s in sources]}\n")

    return {
        "answer":     answer,
        "sources":    sources,
        "confidence": round(top_score / 100, 2)
    }


@app.get("/history")
def get_history():
    return {
        "total_questions": len(conversation_history),
        "history": [
            {"q": item["q"], "a": item["a"][:100] + "..."}
            for item in conversation_history
        ]
    }


@app.post("/clear")
def clear_conversation():
    from answerer import clear_history
    clear_history()
    return {"message": "Conversation history cleared successfully"}


@app.get("/report")
def report():
    if not conversation_history:
        raise HTTPException(status_code=400, detail="No questions asked yet")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Note Assistant - Session Report", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(0, 8, f"PDFs: {', '.join(uploaded_pdfs) if uploaded_pdfs else 'None'}", ln=True)
    pdf.ln(5)

    for i, item in enumerate(conversation_history):
        pdf.set_font("Arial", "B", 11)
        pdf.multi_cell(0, 8, f"Q{i+1}: {item['q']}")
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, f"A: {item['a']}")
        pdf.ln(4)

    out = "./outputs/report.pdf"
    pdf.output(out)
    return FileResponse(out, filename="session_report.pdf")
