from app.utils import prompts
from app.models.request import SummaryType

def generate_chunk_summary_prompt(chunk_text, summary_type: SummaryType):
   summary_type_prompt = _get_summary_type_prompt(summary_type)
   prompt = f"""You are an expert writer tasked with crafting a section of a structured summary based on the provided document chunk. Your goal is to analyze and expand on the content to contribute to a cohesive summary. 

   --- CHUNK TEXT ---- 
   {chunk_text}
   --- CHUNK TEXT ----

   Based on the section above, please generate the final output as follows:
   """ + summary_type_prompt
   return prompt

def _get_summary_type_prompt(summary_type: SummaryType) -> str:
   prompt=""""""
   if summary_type == SummaryType.STANDARD:
      prompt = """
      **Summary Type:** Standard Abstractive Summary
      **Instructions:** Write a concise, fluent paragraph summarizing the main topic, key arguments, and overall conclusion presented in the combined sections. Maintain a formal and objective tone. The summary should capture the essence of the document for a general audience.
      **Output Format:** Markdown.
      """
   elif summary_type == SummaryType.TECHNICAL:
      prompt = """
      **Summary Type:** Technical Summary
      **Instructions:** Generate a structured summary focusing on the technical aspects. Include key objectives, methodology (if applicable), main technical findings or specifications, and technical conclusions. Preserve essential technical terminology. If formulas or specific data were mentioned in the sections, describe their significance or list key values and report them.
      **Output Format:** Use clear headings if appropriate for structure. Use Markdown for formatting.
      """
   elif summary_type == SummaryType.KEY_POINTS:
      prompt= """
      **Summary Type:** Key Points Summary
      **Instructions:** Extract the most critical pieces of information, decisions, findings, or arguments from the combined sections. Present these as a clear, concise bulleted list. Each point should be self-contained and easy to understand.
      **Output Format:** A Markdown bulleted list (`- ` or `* `).
      """
   elif summary_type == SummaryType.LAYMAN:
      prompt = """
      **Summary Type:** Layman's Summary (Simplified Explanation)
      **Instructions:** Explain the core concepts and findings from the combined sections in simple, easy-to-understand language. Avoid technical jargon and complex terminology. Focus on the main message, the 'why it matters', or the practical implications for a non-expert audience.
      **Output Format:** Plain paragraphs, possibly using analogies if helpful for clarification. Markdown format
      """
   return prompt
def generate_final_summary(summary_sections_text, summary_type: SummaryType):
   summary_type_prompt = _get_summary_type_prompt(summary_type)
   prompt = f"""You are an expert writer tasked with combining multiple summaries sections into a single, cohesive, and well-structured summaries. Your goal is to create a unified document that reads as a complete academic summary"""
   +summary_type_prompt +f"""

      --- SUMMARIES SECTIONS ---
      {summary_sections_text}
      --- SUMMARIES SECTIONS ---


      Follow these guidelines:"""+summary_type_prompt
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


"""
    You are an expert writer tasked with combining multiple essay sections into a single, cohesive, and well-structured essay. Your goal is to create a unified document that reads as a complete academic essay. Follow these guidelines:

1. **Craft a Central Thesis:** Develop a clear, overarching thesis statement that ties together the arguments from the individual sections.
2. **Seamless Integration:** Blend the provided sections into a single narrative, reworking content as needed to avoid repetition and ensure smooth transitions between ideas.
3. **Structured Format**: Organize the essay with a clear introduction, body, and conclusion:
   - **Introduction**: Introduce the topic, provide context, and present the thesis statement.
   - **Body**: Divide into logical sections (based on the provided content), each exploring a distinct aspect of the thesis with clear transitions.
   - **Conclusion**: Synthesize the key arguments, reflect on their significance, and offer a final perspective or call to action.
4. **Consistent Tone and Style:** Maintain a formal, academic tone throughout, ensuring clarity and coherence across all sections.
5. **Engage and Persuade**: Write in a way that captivates the reader while building a compelling case for the thesis.
6. **Self-Contained Output:** Ensure the final essay is complete and understandable without requiring reference to the original sections.
"""