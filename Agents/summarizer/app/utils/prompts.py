def generate_chunk_essay_prompt(chunk_text):
    prompt = f"""You are an expert writer tasked with crafting a section of a structured essay based on the provided document chunk. Your goal is to analyze and expand on the content to contribute to a cohesive essay. 

--- CHUNK TEXT ---- 
{chunk_text}
--- CHUNK TEXT ----
"""
    return prompt

def generate_final_essay(essay_sections_text):
    prompt = f"""You are an expert writer tasked with combining multiple essay sections into a single, cohesive, and well-structured essay. Your goal is to create a unified document that reads as a complete academic essay. Follow these guidelines:

1. **Craft a Central Thesis:** Develop a clear, overarching thesis statement that ties together the arguments from the individual sections.
2. **Seamless Integration:** Blend the provided sections into a single narrative, reworking content as needed to avoid repetition and ensure smooth transitions between ideas.
3. **Structured Format**: Organize the essay with a clear introduction, body, and conclusion:
   - **Introduction**: Introduce the topic, provide context, and present the thesis statement.
   - **Body**: Divide into logical sections (based on the provided content), each exploring a distinct aspect of the thesis with clear transitions.
   - **Conclusion**: Synthesize the key arguments, reflect on their significance, and offer a final perspective or call to action.
4. **Consistent Tone and Style:** Maintain a formal, academic tone throughout, ensuring clarity and coherence across all sections.
5. **Engage and Persuade**: Write in a way that captivates the reader while building a compelling case for the thesis.
6. **Self-Contained Output:** Ensure the final essay is complete and understandable without requiring reference to the original sections.


**Provide the result using the Markdown.**

--- ESSAY SECTIONS ---
{essay_sections_text}
--- ESSAY SECTIONS ---
"""
    return prompt

"""

1. **Correct Syntax Errors**:
   - Fix incorrect or unbalanced headers (e.g., `#Header` instead of `# Header`, or mismatched `#` counts).
   - Repair improper list formatting (e.g., `-item` to `- item`, or inconsistent indentation).
   - Correct emphasis issues (e.g., `_italic_` to `*italic*`, or unmatched `*`/`_` symbols).
   - Fix broken links or images (e.g., `[text](url` to `[text](url)`).
   - Ensure proper spacing around Markdown elements (e.g., `##Header` to `## Header`).

2. **Standardize Formatting**:
   - Use consistent header levels (e.g., `#` for main headings, `##` for subheadings).
   - Prefer `*` for emphasis (italics `*text*`, bold `**text**`) unless the original intent clearly uses `_`.
   - Ensure lists use consistent markers (e.g., `-` for unordered lists, `1.` for ordered lists) and proper indentation.
   - Add blank lines between different Markdown elements (e.g., between paragraphs and lists) for clarity.

3. **Preserve Content**:
   - Do not alter the meaning, wording, or intent of the text unless it’s necessary to resolve ambiguity caused by formatting errors.
   - Retain the original structure (e.g., paragraph breaks, list hierarchy) unless it’s malformed and needs correction.

4. **Handle Common Issues**:
   - Remove stray Markdown symbols (e.g., random `#`, `*`, or `_` not used correctly).
   - Fix code blocks (e.g., ensure triple backticks ``` are properly closed).
   - Correct tables by aligning columns and ensuring proper separators (e.g., `| text | text |` with `-` for headers).

5. **Output Only Markdown**:
   - The result must be valid Markdown that renders correctly in standard Markdown parsers.
   - Do not include explanations, comments, or any text outside the corrected Markdown.
"""
def clean_markdown_prompt(markdown_text):
    prompt = f"""You are an expert in Markdown formatting tasked with cleaning and standardizing a provided Markdown text. 
    Your goal is to identify and fix any errors or inconsistencies in the Markdown syntax while PRESERVING the original content and structure. Just fix the error in markdown and return the correct markdown with nothing else.




   --- MARKDOWN TEXT ---
   {markdown_text}
   --- MARKDOWN TEXT ---
   """
    return prompt