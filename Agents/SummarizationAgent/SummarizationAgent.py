import os
import base64
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path
import textwrap
import re
import json
from concurrent.futures import ThreadPoolExecutor
from utils import *
from prompts.prompts import *

# Import Gemini SDK
#import google.generativeai as genai
from google import genai
from google.genai import types

class GeminiDocumentSummarizer:
    """
    Advanced AI Agent built on Gemini for comprehensive document summarization
    with tools for enhanced context processing, content extraction, and intelligent summary generation.
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the Gemini-based document summarization agent.
        
        Args:
            api_key: Google API key for Gemini access
            model_name: Gemini model to use (default: gemini-1.5-pro)
        """
        self.api_key = api_key
        self.model_name = model_name
        # Configure the API
        self.client = genai.Client(api_key=api_key)
        # Initialize the model
        #self.model = genai.Clie(model_name=self.model_name)
        self.max_chunk_tokens = 30000  # Adjust based on model token limits
        self.system_prompt = SYSTEM_PROMPT
        

    def _extract_text_from_document(self, file_path: str) -> str:
        """
        Extract text from various document formats using appropriate parser
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content
        """
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension == '.pdf':
                return extract_from_pdf(file_path)
            elif file_extension in ['.docx', '.doc']:
                return extract_from_word(file_path)
            elif file_extension in ['.txt', '.md']:
                return extract_from_text(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        except Exception as e:
            raise Exception(f"Error extracting text from document: {str(e)}")


    def _chunk_document(self, text: str) -> List[str]:
        """
        Split document into manageable chunks for processing
        
        Args:
            text: Full document text
            
        Returns:
            List of text chunks
        """
        # Simple splitting by paragraphs and then combining to stay within token limits
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Estimated tokens per character (approximation)
        chars_per_token = 4
        
        for para in paragraphs:
            # Skip empty paragraphs
            if not para.strip():
                continue
            
            # Estimation
            para_tokens = len(para) // chars_per_token
            
            if current_length + para_tokens > self.max_chunk_tokens and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_tokens
            else:
                current_chunk.append(para)
                current_length += para_tokens
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        return chunks

    def _extract_document_structure(self, text: str) -> Dict[str, Any]:
        """
        Analyze document structure to identify headings, sections, etc.
        
        Args:
            text: Document text
            
        Returns:
            Dictionary representing document structure
        """
        prompt = f""" {EXTRACT_DOCUMENT_STRUCTURE_PROMPT}
        {text[:10000]}...
        """
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt
            )
        )
        
        try:
            # Extract JSON from response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.text
                
            # Clean up potential non-JSON parts
            json_str = re.sub(r'[\s\S]*?(\{[\s\S]*\})[\s\S]*', r'\1', json_str)
            
            structure = json.loads(json_str)
            return structure
        except Exception as e:
            # Fallback structure if parsing fails
            return {
                "title": "Document Summary",
                "sections": [],
                "supplementary": []
            }

    def _analyze_content_per_section(self, chunks: List[str]) -> Dict[str, Any]:
        """
        Process each chunk to extract key information and analyze content
        
        Args:
            chunks: List of document chunks
            
        Returns:
            Dictionary with content analysis
        """
        # Function to process a single chunk
        def process_chunk(chunk, index):
            prompt = f"""
            {PROCESS_CHUNK_PROMPT}
            {chunk}
            """
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt
                )
            )
            
            try:
                # Extract JSON from response
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.text)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response.text
                    
                # Clean up potential non-JSON parts
                json_str = re.sub(r'[\s\S]*?(\{[\s\S]*\})[\s\S]*', r'\1', json_str)
                
                return json.loads(json_str)
            except Exception as e:
                # Fallback if JSON parsing fails
                return {
                    "key_points": [f"Content from section {index+1}"],
                    "important_facts": [],
                    "conclusions": [],
                    "terminology": {},
                    "limitations": []
                }
        
        # Process chunks in parallel
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_chunk, chunks, range(len(chunks))))
            
        # Combine results
        combined = {
            "key_points": [],
            "important_facts": [],
            "conclusions": [],
            "terminology": {},
            "limitations": []
        }
        
        for result in results:
            combined["key_points"].extend(result.get("key_points", []))
            combined["important_facts"].extend(result.get("important_facts", []))
            combined["conclusions"].extend(result.get("conclusions", []))
            combined["terminology"].update(result.get("terminology", {}))
            combined["limitations"].extend(result.get("limitations", []))
        
        return combined

    def _generate_coherent_summary(self, structure: Dict[str, Any], content_analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a comprehensive, coherent summary using document structure and content analysis
        
        Args:
            structure: Document structure information
            content_analysis: Content analysis by section
            
        Returns:
            Dictionary with different summary formats
        """
        # Prepare context for summary generation
        context = {
            "structure": structure,
            "analysis": content_analysis
        }
        
        context_json = json.dumps(context, indent=2)
        
        # Generate executive summary (brief)
        exec_prompt = f"""
        Using the following document analysis, create a concise executive summary (250-500 words) that captures 
        the most essential information from the document. Focus on main findings, key arguments, and conclusions.
        
        Document analysis:
        {context_json}


        PROVIDE THE RESULT IN MARCKDOWN
        """
        
        exec_response = self.client.models.generate_content(
            model=self.model_name,
            contents=exec_prompt
        )
        executive_summary = exec_response.text
        
        with open("executive_summary.md", "w") as f:
            f.write(executive_summary)

        # Generate comprehensive summary (detailed)
        comp_prompt = f"""
        Using the following document analysis, create a comprehensive summary that thoroughly captures 
        the document's content while maintaining its original structure. Include all key points, important data,
        main arguments and conclusions. Organize the summary according to the document's sections.
        
        This summary should be detailed enough that someone could understand all the aspects of the document
        without reading the original.
        
        Document analysis:
        {context_json}
        """
        
        comp_response = self.client.models.generate_content(
                model=self.model_name,
                contents=comp_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt
                )
            )
        comprehensive_summary = comp_response.text
        
        # Generate topic-based summary (analytical)
        topic_prompt = f"""
        Using the following document analysis, create a topic-based analytical summary that reorganizes 
        the document's content by themes and concepts rather than following the original structure.
        Identify cross-cutting themes and show relationships between different parts of the document.
        
        Document analysis:
        {context_json}
        """

        topic_response = self.client.models.generate_content(
                model=self.model_name,
                contents=topic_prompt,
            )
        topic_summary = topic_response.text
        
        return {
            "executive_summary": executive_summary,
            "comprehensive_summary": comprehensive_summary,
            "topic_summary": topic_summary
        }

    def _extract_key_metrics(self, content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and organize key metrics, statistics, and quantitative data
        
        Args:
            content_analysis: Content analysis information
            
        Returns:
            Dictionary of key metrics
        """
        prompt = f"""
        From the following content analysis, extract all numerical data, statistics, metrics, and quantitative 
        information. Organize them by category and include context for each metric.
        
        Present the result as a JSON object where keys are categories and values are arrays of metric objects,
        each with 'value', 'context', and 'location' fields.
        
        Content analysis:
        {json.dumps(content_analysis, indent=2)}
        """
        
        response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
        
        try:
            # Extract JSON from response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.text)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.text
                
            # Clean up potential non-JSON parts
            json_str = re.sub(r'[\s\S]*?(\{[\s\S]*\})[\s\S]*', r'\1', json_str)
            
            metrics = json.loads(json_str)
            return metrics
        except Exception as e:
            # Return empty structure if parsing fails
            return {"metrics": []}
    
    def _refine_summaries(self, initial_summaries: Dict[str, str], document_structure: Dict[str, Any], 
                        content_analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Refine the initially generated summaries to improve coherence and flow
        
        Args:
            initial_summaries: The summaries generated from the map-reduce phase
            document_structure: Document structure information
            content_analysis: Content analysis from map phase
            
        Returns:
            Dictionary with refined summary formats
        """
        refined_summaries = {}
        
        # Refine each summary type
        for summary_type, content in initial_summaries.items():
            refinement_prompt = f"""
            Review and refine the following document summary. Improve the coherence, 
            flow, and readability while maintaining accuracy and completeness.
            Ensure consistent transitions between sections and eliminate any repetition.
            
            Summary type: {summary_type}
            
            Original summary:
            {content}
            
            Document structure information:
            {json.dumps(document_structure, indent=2)}
            
            Key content elements to preserve:
            - Key points: {json.dumps(content_analysis["key_points"][:5], indent=2)}
            - Important facts: {json.dumps(content_analysis["important_facts"][:5], indent=2)}
            - Main conclusions: {json.dumps(content_analysis["conclusions"][:5], indent=2)}
            
            Return only the refined summary text without explanations or meta-commentary.
            """
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=refinement_prompt
            )
            refined_summaries[summary_type] = response.text
        
        return refined_summaries

    def summarize_document(self, file_path: str) -> Dict[str, Any]:
        """
        Generate a comprehensive document summary
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary containing various summary formats and analysis
        """
        print("Extract text")
        # Extract text from document
        document_text = self._extract_text_from_document(file_path)

        print("Chunk docs")
        # Split document into chunks
        chunks = self._chunk_document(document_text)
        
        print("Extract structure")
        # Extract document structure
        document_structure = self._extract_document_structure(document_text)
        
        print("Analyze content per section")
        # Analyze content by chunks
        content_analysis = self._analyze_content_per_section(chunks)
        
        print("Extract key metrics")
        # Extract key metrics
        key_metrics = self._extract_key_metrics(content_analysis)
        
        #rint("Generate summaries")
        # Generate summaries
        summaries = self._generate_coherent_summary(document_structure, content_analysis)
        
        print("Refine summarize")
        # combine map-reduce and refine
        #summaries = self._refine_summaries(inter_summaries, document_structure, content_analysis)

        # Compile final result
        result = {
            "document_info": {
                "filename": Path(file_path).name,
                "file_size": Path(file_path).stat().st_size,
                "file_type": Path(file_path).suffix,
            },
            "structure": document_structure,
            "summaries": summaries,
            "key_metrics": key_metrics,
            "content_analysis": {
                "key_terminology": content_analysis["terminology"],
                "limitations": content_analysis["limitations"],
            }
        }
        
        return result


# Example usage
def main():
    # Replace with your actual API key
    API_KEY = "AIzaSyBSrT4FjRJB9l7Itgk1DqyJeyQ3Gm4eNNE"
    # Initialize the summarizer
    summarizer = GeminiDocumentSummarizer(api_key=API_KEY)
    # Example document path
    document_path = "test.pdf"
    # Generate summary
    summary_result = summarizer.summarize_document(document_path)
    # Get formatted output
    markdown_summary = generate_formatted_output(summary_result, "markdown")
    # Save the summary
    with open("document_summary.md", "w") as f:
        f.write(markdown_summary)

if __name__ == "__main__":
    main()