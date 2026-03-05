# ExamHelp

ExamHelp is an AI-powered study assistant that reads handwritten notes and answers questions based only on those notes.

## Features

- Upload handwritten PDFs
- OCR extraction using Gemini Vision
- TF-IDF based retrieval
- Local AI generation using Llama 3.2 via Ollama
- Source references for answers
- Confidence score
- Offline operation after document upload
- Session export as PDF report

## Tech Stack

Frontend: Streamlit  
Backend: FastAPI + Uvicorn  
OCR: Google Gemini Vision API  
Search: TF-IDF + Cosine Similarity  
AI Model: Llama 3.2 (Ollama)  
Database: Local JSON  

## Setup Instructions

1 Install dependencies

pip install -r requirements.txt

2 Run Ollama model

ollama run llama3.2

3 Start backend

uvicorn main:app --reload

4 Run frontend

streamlit run app.py

## Usage

Upload a handwritten PDF and ask questions about the notes.

ExamHelp retrieves relevant sections and generates answers using a local AI model.
