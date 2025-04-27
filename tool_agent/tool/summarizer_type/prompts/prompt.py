def summary_prompt(summary_type: str):
   summary_type_prompt = _get_summary_type_prompt(summary_type)
   prompt = f"""You are an expert writer tasked with crafting a section of a structured summary based on the provided document chunk. Your goal is to create a summary. 

   Please generate the final output as follows:
   """ + summary_type_prompt
   return prompt

def _get_summary_type_prompt(summary_type: str) -> str:
   prompt=""""""
   if summary_type == "standard":
      prompt = """
      **Summary Type:** Standard Abstractive Summary
      **Instructions:** Write a concise, fluent paragraph summarizing the main topic, key arguments, and overall conclusion presented in the combined sections. Maintain a formal and objective tone. The summary should capture the essence of the document for a general audience.
      **Output Format:** Markdown.
      """
   elif summary_type =="technical":
      prompt = """
      **Summary Type:** Technical Summary
      **Instructions:** Generate a structured summary focusing on the technical aspects. Include key objectives, methodology (if applicable), main technical findings or specifications, and technical conclusions. Preserve essential technical terminology. If formulas or specific data were mentioned in the sections, you MUST report them, describe their significance or list key values.
      **Output Format:** Use clear headings if appropriate for structure. Use Markdown for formatting.
      """
   elif summary_type == "key_points":
      prompt= """
      **Summary Type:** Key Points Summary
      **Instructions:** Extract the most critical pieces of information, decisions, findings, or arguments from the combined sections. Present these as a clear, concise bulleted list. Each point should be self-contained and easy to understand.
      **Output Format:** A Markdown bulleted list (`- ` or `* `).
      """
   elif summary_type == "layman":
      prompt = """
      **Summary Type:** Layman's Summary (Simplified Explanation)
      **Instructions:** Explain the core concepts and findings from the combined sections in simple, easy-to-understand language. Avoid technical jargon and complex terminology. Focus on the main message, the 'why it matters', or the practical implications for a non-expert audience.
      **Output Format:** Plain paragraphs, possibly using analogies if helpful for clarification. Markdown format
      """
   return prompt


def generate_final_summary(summary_type: str, text_was_splitted:bool):
   summary_type_prompt = _get_summary_type_prompt(summary_type)
   prompt=""
   if text_was_splitted:
      prompt = f"""You are an expert writer tasked with combining multiple summaries sections into a single, cohesive, and well-structured summaries. Your goal is to create a unified document that reads as a complete academic summary.

         Follow these guidelines:
         """+summary_type_prompt
   else:
      prompt = f"""You are an expert writer tasked with crafting a section of a structured summary based on the provided document text. Your goal is to create a summary. 

      Please generate the final output as follows:
      """ + summary_type_prompt
   return prompt


def fix_formulas_prompt(text):
    prompt=f"""You must ensure that all the formulas (if present) are writtein in a correct latex format. If there is no latex format, you must convert the formulas to latex format. Just fix the error in latex format and return the correct latex with nothing else."""
    
    return prompt


def clean_markdown_prompt(markdown_text):
    prompt = f"""You are an expert in Markdown formatting tasked with cleaning and standardizing a provided Markdown text. 
    Your goal is to identify and fix any errors or inconsistencies in the Markdown syntax while PRESERVING the original content and structure. Just fix the error in markdown and return the correct markdown with nothing else.


   --- MARKDOWN TEXT ---
   {markdown_text}
   --- MARKDOWN TEXT ---
   """
    return prompt

