# texts/main.py
# File per testare le funzionalità di estrazione e elaborazione del testo

import sys
import os
import logging
from cosine_chunker import chunk_document_cosine
from text import get_text
# Aggiungi la directory principale al path di Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test.main")

def main():
    text=get_text()
    chunks=chunk_document_cosine(text, [])
    print(type(chunks))
    with open("chunks.txt", "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk['section'])
            f.write("\n\n")
if __name__ == "__main__":
    main()