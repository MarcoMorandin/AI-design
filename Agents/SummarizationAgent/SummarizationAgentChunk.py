from ipaddress import summarize_address_range
import os
import json
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple

from utils import extract_from_pdf, extract_from_word, extract_from_text
from prompts.prompts import SYSTEM_PROMPT

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv() 

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class GeminiDocumentSummarizer:
    """
    Advanced AI Agent built on Gemini for comprehensive document summarization.
    It extracts text from supported documents, chunks the text, analyzes each section,
    and then generates a coherent summary.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash") -> None:
        """
        Initialize the Gemini-based document summarization agent.

        Args:
            api_key: Google API key for Gemini access.
            model_name: Gemini model to use (default: gemini-2.0-flash).
        """
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)
        self.max_chunk_tokens = 4000  # Adjust based on model token limits
        self.system_prompt = SYSTEM_PROMPT

        # Create the directory for summary results if it doesn't exist.
        self.summary_dir = Path("summaryResult")
        self.summary_dir.mkdir(exist_ok=True)

    def _extract_text_from_document(self, file_path: str) -> str:
        """
        Extract text from various document formats using the appropriate parser.

        Args:
            file_path: Path to the document file.

        Returns:
            Extracted text content.

        Raises:
            ValueError: If the file format is unsupported.
            Exception: If extraction fails.
        """
        file_extension = Path(file_path).suffix.lower()
        try:
            if file_extension == ".pdf":
                return extract_from_pdf(file_path)
            elif file_extension in [".docx", ".doc"]:
                return extract_from_word(file_path)
            elif file_extension in [".txt", ".md"]:
                return extract_from_text(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        except Exception as e:
            raise Exception(f"Error extracting text from document: {str(e)}")

    def _chunk_document(self, text: str) -> List[str]:
        """
        Split the document text into manageable chunks for processing.

        Args:
            text: Full document text.

        Returns:
            A list of text chunks.
        """
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0
        chars_per_token = 4  # Approximate estimation

        for para in paragraphs:
            if not para.strip():
                continue
            para_tokens = len(para) // chars_per_token
            if current_length + para_tokens > self.max_chunk_tokens and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_length = para_tokens
            else:
                current_chunk.append(para)
                current_length += para_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        return chunks

    def _analyze_content_per_section(self, chunks: List[str]) -> List[str]:
        """
        Process each text chunk to extract key information.

        Args:
            chunks: List of document chunks.

        Returns:
            A list of analysis results for each chunk.
        """
        def process_chunk(chunk: str) -> str:
            prompt = f"{chunk}"
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt
                )
            )
            return response.text.strip()

        with ThreadPoolExecutor(max_workers=5) as executor:
            chunk_summaries = list(executor.map(process_chunk, chunks))
        return chunk_summaries

    def _generate_coherent_summary(
        self, content_analysis: List[str], file_name: str
    ) -> Tuple[str, Path]:
        """
        Generate a coherent summary based on the content analysis.

        Args:
            content_analysis: List of analysis results from document chunks.
            file_name: Original file name (used to generate a summary file name).

        Returns:
            A tuple containing the summary text and the summary file path.
        """
        # If len==1 is not necessary to call the LLM
        if len(content_analysis)==1:
            base_name = Path(file_name).stem
            summary_filename = f"{base_name}_summary.md"
            summary_path = self.summary_dir / summary_filename
            return content_analysis[0], summary_path
        
        context = {"analysis": content_analysis}
        context_json = json.dumps(context, indent=2)

        exec_prompt = f"""
Using the provided analysis of the document chunks, create a unique, reorganized summary.

Document Chunk Analysis:
{context_json}

Please provide the result in Markdown format.
"""
        exec_response = self.client.models.generate_content(
            model=self.model_name,
            contents=exec_prompt
        )
        summary = exec_response.text
        base_name = Path(file_name).stem
        summary_filename = f"{base_name}_summary.md"
        summary_path = self.summary_dir / summary_filename
        return summary, summary_path

    def _summarize_document(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single document and generate its summary.

        Args:
            file_path: Path to the document file.

        Returns:
            A dictionary containing the file path, summary text, and summary file path.
        """
        try:
            text = self._extract_text_from_document(file_path)
            chunks = self._chunk_document(text)
            logging.info(f"Number of chunks for {file_path}: {len(chunks)}")
            content_analysis = self._analyze_content_per_section(chunks)
            summary_result, summary_path = self._generate_coherent_summary(content_analysis, file_path, perform=true)
            return {
                "file_path": file_path,
                "summary": summary_result,
                "summary_path": summary_path
            }
        except Exception as e:
            logging.error(f"Error processing {file_path}: {str(e)}")
            return {
                "file_path": file_path,
                "error": str(e)
            }

    def summarize_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Process all supported documents in a folder and generate summaries.

        Args:
            folder_path: Path to the folder containing documents.

        Returns:
            A list of dictionaries with summary results for each document.
        """
        results = []
        folder = Path(folder_path)
        supported_extensions = [".pdf", ".docx", ".doc", ".txt", ".md"]
        files = [f for f in folder.glob("**/*") if f.is_file() and f.suffix.lower() in supported_extensions]

        if not files:
            logging.info(f"No supported documents found in {folder_path}")
            return results

        logging.info(f"Found {len(files)} documents to process in {folder_path}")

        for file_path in files:
            logging.info(f"Processing {file_path}...")
            result = self._summarize_document(str(file_path))
            if "summary" in result:
                try:
                    with open(result["summary_path"], "w", encoding="utf-8") as f:
                        f.write(result["summary"])
                    logging.info(f"Summary for {file_path} written to {result['summary_path']}")
                except Exception as e:
                    logging.error(f"Failed to write summary for {file_path}: {str(e)}")
            results.append(result)
        return results

    def test_caoption_extraction(self: str) -> List[Dict[str, Any]]:
        text = self._extract_text_from_document("files/HANDOUTS-12-KnowledgeRepresentation_Official.pdf")


def main():
    #print(os.environ.get("API_KEY"))
    #summarizer = GeminiDocumentSummarizer(api_key=os.environ.get("API_KEY"))
    #summarizer.test_caoption_extraction()
    
    # Replace with your actual Google API key
    folder_path = "files"  # Folder containing the documents to summarize

    summarizer = GeminiDocumentSummarizer(api_key=os.environ.get("API_KEY"))
    results = summarizer.summarize_folder(folder_path)

    for result in results:
        if "summary" in result:
            logging.info(f"Completed summarization for: {result['file_path']}")
        else:
            logging.error(f"Failed summarizing: {result['file_path']} - {result.get('error')}")
    

if __name__ == "__main__":
    main()
