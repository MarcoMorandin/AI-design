from huggingface_hub import hf_hub_download
import re
from PIL import Image
import requests
from nougat.dataset.rasterize import rasterize_paper
from transformers import NougatProcessor, VisionEncoderDecoderModel
import torch
import gradio as gr
import uuid
import os
import spaces

processor = NougatProcessor.from_pretrained("facebook/nougat-small")
model = VisionEncoderDecoderModel.from_pretrained("facebook/nougat-small")

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)


def get_pdf(pdf_link):
    unique_filename = f"{os.getcwd()}/downloaded_paper_{uuid.uuid4().hex}.pdf"

    response = requests.get(pdf_link)

    if response.status_code == 200:
        with open(unique_filename, "wb") as pdf_file:
            pdf_file.write(response.content)
        print("PDF downloaded successfully.")
    else:
        print("Failed to download the PDF.")
    return unique_filename


@spaces.GPU
def predict(image):
    # prepare PDF image for the model
    image = Image.open(image)
    pixel_values = processor(image, return_tensors="pt").pixel_values

    # generate transcription (here we only generate 30 tokens)
    outputs = model.generate(
        pixel_values.to(device),
        min_length=1,
        max_new_tokens=1500,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
    )

    page_sequence = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    page_sequence = processor.post_process_generation(page_sequence, fix_markdown=False)
    return page_sequence


def inference(pdf_file, pdf_link):
    if pdf_file is None:
        if pdf_link == "":
            print("No file is uploaded and No link is provided")
            return "No data provided. Upload a pdf file or provide a pdf link and try again!"
        else:
            file_name = get_pdf(pdf_link)
    else:
        file_name = pdf_file.name
        pdf_name = pdf_file.name.split("/")[-1].split(".")[0]

    images = rasterize_paper(file_name, return_pil=True)
    sequence = ""
    # infer for every page and concat
    for image in images:
        sequence += predict(image)

    content = (
        sequence.replace(r"\(", "$")
        .replace(r"\)", "$")
        .replace(r"\[", "$$")
        .replace(r"\]", "$$")
    )
    with open(f"{os.getcwd()}/output.md", "w+") as f:
        f.write(content)
        f.close()

    return content, f"{os.getcwd()}/output.md"


css = """
  #mkd {
    height: 500px; 
    overflow: auto; 
    border: 1px solid #ccc; 
  }
"""

with gr.Blocks(css=css) as demo:
    gr.HTML(
        "<h1><center>Nougat: Neural Optical Understanding for Academic Documents 🍫<center><h1>"
    )
    gr.HTML(
        "<h3><center>Lukas Blecher et al. <a href='https://arxiv.org/pdf/2308.13418.pdf' target='_blank'>Paper</a>, <a href='https://facebookresearch.github.io/nougat/'>Project</a><center></h3>"
    )
    gr.HTML(
        "<h3><center>This demo is based on transformers implementation of Nougat 🤗<center><h3>"
    )

    with gr.Row():
        mkd = gr.Markdown("<h4><center>Upload a PDF</center></h4>")
        mkd = gr.Markdown("<h4><center><i>OR</i></center></h4>")
        mkd = gr.Markdown("<h4><center>Provide a PDF link</center></h4>")

    with gr.Row(equal_height=True):
        pdf_file = gr.File(label="PDF 📑", file_count="single")
        pdf_link = gr.Textbox(
            placeholder="Enter an arxiv link here", label="Link to Paper🔗"
        )
    with gr.Row():
        btn = gr.Button("Run Nougat 🍫")
    with gr.Row():
        clr = gr.Button("Clear Inputs & Outputs 🧼")

    output_headline = gr.Markdown(
        "## PDF converted to markup language through Nougat-OCR👇"
    )
    with gr.Row():
        parsed_output = gr.Markdown(elem_id="mkd", value="Output Text 📝")
        output_file = gr.File(file_types=["txt"], label="Output File 📑")

    btn.click(inference, [pdf_file, pdf_link], [parsed_output, output_file])
    clr.click(
        lambda: (
            gr.update(value=None),
            gr.update(value=None),
            gr.update(value=None),
            gr.update(value=None),
        ),
        [],
        [pdf_file, pdf_link, parsed_output, output_file],
    )
    gr.Examples(
        [["nougat.pdf", ""], [None, "https://arxiv.org/pdf/2308.08316.pdf"]],
        inputs=[pdf_file, pdf_link],
        outputs=[parsed_output, output_file],
        fn=inference,
        cache_examples=True,
        label="Click on any Examples below to get Nougat OCR results quickly:",
    )


demo.queue()
demo.launch(debug=True)
