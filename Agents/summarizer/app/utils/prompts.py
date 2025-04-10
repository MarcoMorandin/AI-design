def generate_chunk_summary_prompt(chunk_text):
        prompt=f"""You are an expert summarizer with a keen eye for extracting essential information. Your task is to read and analyze the following document and produce a concise and accurate summary. Please adhere to the following guidelines:
                1. **Focus on Core Ideas:** Identify and capture the main arguments, key themes, and significant conclusions.
                2. **Be Concise and Clear:** Summarize the document in your own words without including unnecessary details or excessive repetition.
                3. **Maintain Logical Flow:** Organize your summary into coherent paragraphs or bullet points (whichever best suits the content) while preserving the logical progression of ideas.
                4. **Retain Essential Details:** Ensure that any critical data, technical points, or conclusions are included, but do not overwhelm the summary with minor details.
                5. **Respect the Original Tone:** Preserve the original tone and context where possible, ensuring that the summary reflects the intent of the document.
                6. **Self-Contained Output:** Craft a summary that makes sense independently, without requiring further context from the original document.

                --- CHUNK TEXT ---- 
                {chunk_text}
                --- CHUNK TEXT ----


                Please generate your summary below.
                """
        return prompt

def generate_final_summary(summaries_text):
        prompt=f"""
        Your task is to integrate multiple summaries into one unified document. Follow these guidelines:

        - **Unified Narrative:** Seamlessly weave all the provided summaries into a single narrative. Do not separate them into distinct sections. Instead, use smooth transitions to connect the ideas and themes from each summary.
        - **Clear Introduction and Conclusion:** Begin with an introduction that sets the context for the document. End with a conclusion that encapsulates the overall insights drawn from the aggregated content.
        - **Consistent Tone and Style:** Ensure that the final document maintains a consistent voice and style throughout. Edit the summaries as necessary so they read as parts of a continuous text.
        - **Logical Flow:** Organize the content so that themes, arguments, and conclusions follow logically from one another. Use transitional phrases to guide the reader through the narrative.
        - **Self-Contained Output:** The final document should be self-explanatory and complete, providing all necessary context without referencing separated, standalone summary documents.

        ---

        ## Final Document Structure

        1. **Introduction:**  
        Start with a brief overview explaining the purpose of the document and outlining the main topics covered in the aggregated summaries.

        2. **Integrated Content:**  
        Merge the content of each individual summary into a single, flowing narrative. Ensure that the transitions between different topics and summaries are smooth so that the document reads like one continuous piece.

        3. **Conclusion:**  
        End with a conclusion that synthesizes the key takeaways. Reflect on how the integrated information provides a comprehensive understanding of the subject matter.

        THE RESULT MUST BE PROVIDE IN MARKDOWN. Only the markdown, no any other sentences
        ---

        --- SUMMARIES ---
        {summaries_text}
        --- SUMMARIES ---


        """
        return prompt













SYSTEM_PROMPT = """
        You are an expert document analyst and summarizer. Your task is to create comprehensive, 
        accurate summaries that capture the essential information from documents while maintaining context.
        Focus on identifying key points, main arguments, important data, and conclusions.
        
        When summarizing:
        1. Maintain the document's original structure in your summary organization
        2. Prioritize factual accuracy and objective representation
        3. Preserve technical terminology and specialized concepts
        4. Include numerical data and statistics when significant
        5. Identify relationships between concepts and sections
        6. Note limitations, caveats or uncertainty expressed in the original
        
        Your summary should be thorough enough that a reader can understand all major points 
        without referring to the original document.
        """

SYSTEM_PROMPT_ORGANIZER = """
        You are an expert document analyst. Your task is to create comprehensive, 
        accurate reorganization of the document that capture the information from documents maintaining context.
        Focus on identifying key points, main arguments, important data, and conclusions.
        
        When summarizing:
        1. Maintain the document's original structure in your summary organization
        2. Prioritize factual accuracy and objective representation
        3. Preserve technical terminology and specialized concepts
        4. Include numerical data and statistics when significant
        5. Identify relationships between concepts and sections
        6. Note limitations, caveats or uncertainty expressed in the original
        
        Your reorganization should be thorough enough that a reader can understand all the points 
        without referring to the original document.
        """

EXTRACT_DOCUMENT_STRUCTURE_PROMPT = """
        Analyze the structure of the following document. Identify:
        1. The title or main heading
        2. Major section headings
        3. The hierarchical relationship between sections
        4. Any appendices, references, or supplementary sections
        
        Return the result as a JSON object with keys 'title', 'sections' (array of section objects with 'heading' and 'level'), 
        and 'supplementary' (array of supplementary section names).
        
        Document text (beginning): """

