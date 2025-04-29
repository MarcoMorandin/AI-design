import re
import urllib.parse
import requests
import io
import json
import base64
from urllib.parse import urlparse, parse_qs

from app.core.config import settings

def extract_formulas(text):
    """Extract LaTeX formulas from Markdown text and replace with placeholders."""
    formula_patterns = [
        (r'\\\[(.*?)\\\]', 'DISPLAY_FORMULA'),  # Display math: \[...\]
        (r'\\\((.*?)\\\)', 'INLINE_FORMULA'),  # Inline math: \(...\)
        (r'\$\$(.*?)\$\$', 'DISPLAY_FORMULA'),  # Display math: $$...$$
        (r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', 'INLINE_FORMULA')  # Inline math: $...$
    ]
    matches = []
    formula_urls = {}

    # Collect all formula 
    for pattern, formula_type in formula_patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            formula = match.group(1).strip()
            start, end = match.span()
            placeholder = f'[{formula_type}_{len(matches)}]'
            # Generate CodeCogs URL
            encoded_formula = urllib.parse.quote(formula)
            url = f'https://latex.codecogs.com/png.latex?{encoded_formula}'
            matches.append((start, end, formula, placeholder, formula_type))
            formula_urls[placeholder] = url

    # Sort matches by start position (in reverse to avoid position shifts)
    matches.sort(key=lambda x: x[0], reverse=True)

    # Replace formulas with placeholders
    modified_text = text
    for start, end, _, placeholder, formula_type in matches:
        if formula_type == 'DISPLAY_FORMULA':
            replacement = f'\n{placeholder}\n'
        else:
            replacement = placeholder
        modified_text = modified_text[:start] + replacement + modified_text[end:]

    return modified_text, formula_urls, matches

def download_formula_images(formula_urls):
    """Download images from formula URLs."""
    image_data = {}
    print("formula_urls: ", formula_urls)
    for placeholder, url in formula_urls.items():
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise exception for HTTP errors
            # Store the binary image data
            image_data[placeholder] = response.content
        except requests.RequestException as e:
            print(f"Error downloading image for {placeholder}: {e}")
            image_data[placeholder] = None
    return image_data

def prepare_document_data(text, doc_title="Document with LaTeX Formulas"):
    """Extract formulas, download images, and prepare data for endpoint."""
    # Extract formulas and download images
    modified_text, formula_urls,matches = extract_formulas(text)
    print("Ciao")
    image_data = download_formula_images(formula_urls)
    
    # Prepare document structure
    doc_data = {
        "title": doc_title,
        "text": modified_text,
        "formulas": []
    }
    
    # Sort matches by start position
    matches.sort(key=lambda x: x[0])
    
    # Process each formula and prepare formula data
    print("matches: ", matches)
    for _, _, formula, placeholder, formula_type in matches:
        if placeholder in image_data and image_data[placeholder]:
            # Base64 encode the image data
            base64_image = base64.b64encode(image_data[placeholder]).decode('utf-8')
            
            # Add to formulas list
            doc_data["formulas"].append({
                "placeholder": placeholder,
                "type": formula_type,
                "original_formula": formula,
                "image_data": base64_image,
                "is_display": formula_type == 'DISPLAY_FORMULA'
            })
    
    return doc_data

def send_to_endpoint(data, endpoint_url, jwt_token):
    """Send document data to the specified endpoint."""
    try:
        headers = {
            'Authorization': f'Bearer {jwt_token}',
        }
        
        response = requests.post(endpoint_url, json=data, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending data to endpoint: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None

def process_document_with_formulas(text, endpoint_url, jwt_token, doc_title="Document with LaTeX Formulas"):
    """Process document with LaTeX formulas and send to endpoint."""
    # Prepare the document data
    doc_data = prepare_document_data(text, doc_title)
    
    endpoint_url = settings.UPLOAD_DOCUMENTS_URL
    # Send to endpoint
    result = send_to_endpoint(doc_data, endpoint_url, jwt_token)
    
    if result:
        print(f"Document processed successfully. Response: {result}")
        return result
    else:
        print("Failed to process document.")
        return None

