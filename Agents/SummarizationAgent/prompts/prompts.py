SYSTEM_PROMPT="""
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

SYSTEM_PROMPT_ORGANIZER="""
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

EXTRACT_DOCUMENT_STRUCTURE_PROMPT="""
        Analyze the structure of the following document. Identify:
        1. The title or main heading
        2. Major section headings
        3. The hierarchical relationship between sections
        4. Any appendices, references, or supplementary sections
        
        Return the result as a JSON object with keys 'title', 'sections' (array of section objects with 'heading' and 'level'), 
        and 'supplementary' (array of supplementary section names).
        
        Document text (beginning): """

PROCESS_CHUNK_PROMPT="""Analyze the following document section. Extract:
            1. Key points and main arguments
            2. Important facts, data, and statistics
            3. Conclusions or implications
            4. Technical terminology with definitions
            5. Any limitations or caveats mentioned
            
            Return the analysis in JSON format with these categories as keys using this schema:
            Response:{
                "key_points": [],
                "important_facts": [],
                "conclusions": [],
                "terminology": [],
                "limitations": []
            }
            Document section: """
