import fitz  # PyMuPDF
from docx import Document  # Changed import statement
from typing import List, Dict, Any, Optional, Tuple


def extract_from_pdf(file_path: str) -> str:
    """Extract text from PDF documents."""
    try:
              
        doc = fitz.open(file_path)
        text_blocks = []
        images = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Estrazione del testo
            text_blocks.append(page.get_text())

            # Estrazione immagini
            for img_index, img in enumerate(page.get_images()):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                #with open(f"page{page_num+1}_img{img_index}.{image_ext}", "wb") as img_file:
                #    img_file.write(image_bytes)
                #    images.append(f"page{page_num+1}_img{img_index}.{image_ext}")

        
        return "\n\n".join(text_blocks)
    except ImportError:
        raise ImportError("PyMuPDF (fitz) library is required for PDF extraction. Install with 'pip install pymupdf'")

def extract_from_word(file_path: str) -> str:
    """Extract text from Word documents."""
    try:
        # Updated to use the correct Document class     
        doc = Document(file_path)
        return "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except ImportError:
        raise ImportError("python-docx library is required for Word extraction. Install with 'pip install python-docx'")

def extract_from_text(file_path: str) -> str:
    """Extract text from plain text files."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def generate_formatted_output(summary_result: Dict[str, Any], format_type: str = "markdown") -> str:
    """
    Generate a formatted version of the summary
    
    Args:
        summary_result: The summary result dictionary
        format_type: Format type (markdown, json, html)
        
    Returns:
        Formatted summary string
    """
    if format_type == "json":
        return json.dumps(summary_result, indent=2)
    
    elif format_type == "html":
        # Generate HTML version of the summary
        template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Document Summary: {summary_result["document_info"]["filename"]}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 2em; }}
                h1, h2, h3 {{ color: #333; }}
                .summary-section {{ margin-bottom: 2em; }}
                .key-metrics {{ display: flex; flex-wrap: wrap; }}
                .metric {{ background: #f5f5f5; padding: 1em; margin: 0.5em; border-radius: 5px; }}
                .terminology dt {{ font-weight: bold; }}
                .terminology dd {{ margin-bottom: 0.5em; }}
            </style>
        </head>
        <body>
            <h1>Document Summary: {summary_result["document_info"]["filename"]}</h1>
            <div class="summary-section">
                <h2>Executive Summary</h2>
                <div>{summary_result["summaries"]["executive_summary"].replace('\n', '<br>')}</div>
            </div>
            
            <div class="summary-section">
                <h2>Comprehensive Summary</h2>
                <div>{summary_result["summaries"]["comprehensive_summary"].replace('\n', '<br>')}</div>
            </div>
            
            <div class="summary-section">
                <h2>Topic Analysis</h2>
                <div>{summary_result["summaries"]["topic_summary"].replace('\n', '<br>')}</div>
            </div>
        </body>
        </html>
        """
        return template
    
    else:  # Default to markdown
        md_template = f"""
        # Document Summary: {summary_result["document_info"]["filename"]}
        
        ## Document Information
        - **Filename**: {summary_result["document_info"]["filename"]}
        - **File Type**: {summary_result["document_info"]["file_type"]}
        - **Size**: {summary_result["document_info"]["file_size"] // 1024} KB
        
        ## Executive Summary
        
        {summary_result["summaries"]["executive_summary"]}
        
        ## Comprehensive Summary
        
        {summary_result["summaries"]["comprehensive_summary"]}
        
        ## Topic Analysis
        
        {summary_result["summaries"]["topic_summary"]}
        
        ## Key Terminology
        
        """
        
        # Add terminology
        for term, definition in summary_result["content_analysis"]["key_terminology"].items():
            md_template += f"- **{term}**: {definition}\n"
            
        # Add limitations if any
        if summary_result["content_analysis"]["limitations"]:
            md_template += "\n## Limitations and Caveats\n\n"
            for limitation in summary_result["content_analysis"]["limitations"]:
                md_template += f"- {limitation}\n"
        
        return md_template