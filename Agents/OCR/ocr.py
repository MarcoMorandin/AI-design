from nougat import NougatModel
from pathlib import Path
#albumentations==1.3.0

from texify import Texify
import fitz  # PyMuPDF

def texify_extrect(pdf_path):
    # Apri il PDF
    doc = fitz.open(pdf_path)
    num_pages = len(doc)

    # Elabora in blocchi di 10 pagine
    block_size = 10
    results = []

    for start_page in range(0, num_pages, block_size):
        end_page = min(start_page + block_size, num_pages)
        pages = list(range(start_page + 1, end_page + 1))  # +1 perché Texify usa indici basati su 1
        
        block_result = texify.extract_pdf(pdf_path, pages=pages)
        results.append(block_result)

    # Combina i risultati
    full_result = "\n".join(results)

    # Salva il risultato
    with open("texify.tex", "w", encoding="utf-8") as f:
        f.write(full_result)


def nougat_extrect(path):

    # Extract text
    markdown_text = model.predict(path)

    # Print or save the extracted text
    #print(markdown_text)

    # Save to a file
    with open("nougat.md", "w", encoding="utf-8") as f:
        f.write(markdown_text)

if __name__ == "__main__":
    # Load the model
    model = NougatModel.from_pretrained("facebook/nougat-base")
    texify = Texify()

    nougat_extrect("test.pdf")

    texify_extrect("test.pdf")