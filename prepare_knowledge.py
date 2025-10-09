from PyPDF2 import PdfReader
import json
import os

def extract_chunks(pdf_path, chunk_size=500):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + " "
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
for filename in ["kniga-1.pdf", "kniga-2.pdf", "kniga-3.pdf", "kniga-4.pdf", "kniga-5.pdf"]:
    if os.path.exists(filename):
        print(f"Обрабатываю {filename}...")
        chunks = extract_chunks(filename)
        all_chunks.extend(chunks)

with open("knowledge_chunks.json", "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, ensure_ascii=False, indent=2)

print(f"Сохранено {len(all_chunks)} фрагментов.")
