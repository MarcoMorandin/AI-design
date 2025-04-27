import os
import tempfile
from pdf2image import convert_from_path
import requests
import base64
import fitz  # PyMuPDF
from collections import defaultdict

def extract_images(pdf_path, output_dir):
    """
    Extract images from a PDF and save them to the specified directory.
    Returns a dictionary mapping page numbers to lists of image paths.
    """
    doc = fitz.open(pdf_path)
    image_dict = defaultdict(list)

    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)  # Get all images on the page

        for img_index, img in enumerate(images):
            xref = img[0]  # Image reference
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]  # e.g., 'png', 'jpeg'
            
            # Unique filename based on page and image index
            image_filename = f"page{page_num+1}_image{img_index+1}.{image_ext}"
            image_path = os.path.join(output_dir, image_filename)
            
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            
            image_dict[page_num + 1].append(image_path)
    
    return image_dict

def chunk_list(lst, chunk_size):
    """Split a list into chunks of specified size."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def pdf_to_images(pdf_path):
    """Convert a PDF to a list of image file paths."""
    # with tempfile.TemporaryDirectory() as temp_dir:
    temp_dir = './temp'
    images = convert_from_path(pdf_path, output_folder=temp_dir)
    image_paths = [os.path.join(temp_dir, f"page_{i}.png") for i in range(len(images))]
    for i, image in enumerate(images):
        image.save(image_paths[i], 'PNG')
    return image_paths

def process_images_with_nougat_http(image_paths, batch_size=128):
    """
    Process images with the Nougat model using HTTP requests.
    
    Args:
        image_paths (list): List of paths to image files.
        batch_size (int): Number of images to process per request (max 128).
    
    Returns:
        list: List of markdown text strings extracted from images.
    """
    # Get PAT from environment variable
    pat = os.environ.get('CLARIFAI_PAT')
    if not pat:
        raise ValueError("CLARIFAI_PAT environment variable not set.")

    # Clarifai API endpoint for Nougat model
    url = "https://api.clarifai.com/v2/users/facebook/apps/nougat/models/nougat-base/outputs"
    headers = {
        "Authorization": f"Key {pat}",
        "Content-Type": "application/json"
    }

    markdown_contents = []
    # Process images in batches
    for batch_paths in chunk_list(image_paths, min(batch_size, 128)):
        inputs = []
        # Prepare inputs for the batch
        for path in batch_paths:
            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            inputs.append({
                "data": {
                    "image": {
                        "base64": image_data
                    }
                }
            })

        # Construct the request payload
        data = {"inputs": inputs}
        
        # Send POST request to Clarifai API
        response = requests.post(url, headers=headers, json=data)
        
        # Handle the response
        if response.status_code == 200:
            outputs = response.json().get("outputs", [])
            for output in outputs:
                markdown_text = output["data"]["text"]["raw"]
                markdown_contents.append(markdown_text)
        else:
            print(f"Error: {response.status_code}, {response.text}")
            raise Exception(f"API request failed: {response.text}")
    
    return markdown_contents

def convert_pdf_to_markdown(pdf_path, output_md_path, batch_size=128):
    """
    Convert a PDF to Markdown using Nougat, including images from the original document.
    """

    # Determine output directory and create images subdirectory
    output_dir = os.path.dirname(output_md_path)
    if not output_dir:  # If no directory specified, use current directory
        output_dir = '.'
    images_dir = os.path.join(output_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)  # Create directory if it doesn’t exist

    # Extract images from PDF
    image_dict = extract_images(pdf_path, images_dir)

    # Convert PDF to images for Nougat processing (existing function)
    image_paths = pdf_to_images(pdf_path)

    # Process images with Nougat via Clarifai API (existing function)
    markdown_contents = process_images_with_nougat_http(image_paths, batch_size)

    # Write Markdown file with text and images
    with open(output_md_path, 'w', encoding='utf-8') as md_file:
        for page_num, md_text in enumerate(markdown_contents, start=1):
            # Write page header and Nougat-extracted Markdown text
            md_file.write(f"# Page {page_num}\n\n")
            md_file.write(md_text + "\n\n")

            # Add images for this page, if any
            if page_num in image_dict:
                md_file.write("## Images from this page\n\n")
                for image_path in image_dict[page_num]:
                    # Calculate relative path from Markdown file location
                    rel_path = os.path.relpath(image_path, output_dir)
                    md_file.write(f"![Image]({rel_path})\n\n")

    print(f"Markdown file successfully saved to {output_md_path}")
    
# Example usage
if __name__ == "__main__":
    # Set your PAT in the environment (replace with your actual PAT)
    os.environ['CLARIFAI_PAT'] = '1fae97c40f0740fbaf0797473157c877'
    
    # Specify input and output paths
    pdf_path = 'test.pdf'  # Path to your PDF file
    output_md_path = 'test.md'
    
    # Convert PDF to markdown
    convert_pdf_to_markdown(pdf_path, output_md_path, batch_size=128)