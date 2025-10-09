from PyPDF2 import PdfReader
import os
import json

def extract_chunks(pdf_path, chunk_size=500):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    
    sentences = text.split(". ")
    chunks = []
    current = ""
    for sent in sentences:
        if len(current.split()) + len(sent.split()) > chunk_size:
            if len(current) > 50:
                chunks.append(current.strip())
            current = sent + ". "
        else:
            current += sent + ". "
    if current and len(current) > 50:
        chunks.append(current.strip())
    return chunks

all_chunks = []
for filename in ["kniga-1.pdf", "kniga-2.pdf", ..., "kniga-5.pdf"]:
    chunks = extract_chunks(filename)
    all_chunks.extend(chunks)

# Сохрани в компактном формате
with open("knowledge_chunks.json", "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, ensure_ascii=False)
