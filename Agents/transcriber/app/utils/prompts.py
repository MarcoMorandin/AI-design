# app/utils/prompts.py

def generate_chunk_summary_prompt(chunk_text):
    """Constructs the prompt for summarizing a single chunk."""
    prompt = f"""
Summarize the key points, topics, arguments, and any conclusions presented in the following section of a larger transcript. Be concise but comprehensive for this section.

--- TRANSCRIPT SECTION ---
{chunk_text}
--- END TRANSCRIPT SECTION ---

Summary of this section:
"""
    return prompt

def generate_final_essay_prompt(summaries_text):
    """Constructs the prompt for generating the final essay from summaries with sectioning and bold keywords."""
    prompt = f"""
You are an expert analyst tasked with creating a final, coherent, and detailed explanatory essay based on a series of summaries derived from a long video transcript.
Your goal is to synthesize these summaries into a single, well-structured essay covering the core topics, key arguments, evidence, and main conclusions discussed in the original full transcript.
The purpose of this essay is to allow someone to fully understand the video's content without watching it.

**Output Requirements:**
1.  **Structure:** Organize the final essay into logical sections using Markdown headings (e.g., `## Introduction`, `## [Meaningful Topic Title 1]`, `## [Meaningful Topic Title 2]`, ..., `## Conclusion`). Determine appropriate, descriptive titles for the main body sections based on the content from the summaries.
2.  **Content:** Each section should clearly explain its topic, drawing details from the provided summaries. Ensure a logical flow between sections and synthesize information coherently.
3.  **Keywords:** Identify and **bold** the most **important keywords**, **concepts**, **names**, or **technical terms** within the essay text using Markdown (e.g., `The discussion centered on **quantum computing** principles.` ). Use bolding selectively for emphasis on truly key terms.
4.  **Tone:** Maintain an objective and informative tone.
5.  **Synthesis:** Focus on weaving the information from the summaries into a cohesive narrative.

Here are the summaries from different parts of the transcript:
--- SUMMARIES ---
{summaries_text}
--- END SUMMARIES ---

Now, write the final detailed essay explanation using Markdown for headings and bold keywords:
"""
    return prompt
    

def generate_essay_prompt(transcript_text):
    """Constructs the prompt for the LLM with sectioning and bold keywords."""
    prompt = f"""
You are an AI assistant transforming a raw video transcript into a comprehensive and well-structured explanatory essay.
The purpose of this essay is to allow someone to fully understand the content, key points, flow of discussion, and conclusions of the original video without needing to watch it.

Analyze the provided transcript carefully. Identify the main subject, the key themes or arguments explored, any significant examples or evidence mentioned, and the overall conclusion or outcome.

**Output Requirements:**
1.  **Structure:** Organize the essay into logical sections using Markdown headings (e.g., `## Introduction`, `## [Meaningful Topic Title 1]`, `## [Meaningful Topic Title 2]`, ..., `## Conclusion`). The LLM should determine appropriate, descriptive titles for the main body sections based on the content.
2.  **Content:** Each section should clearly explain its topic, drawing details and examples from the transcript. Ensure a logical flow between sections.
3.  **Keywords:** Identify and **bold** the most **important keywords**, **concepts**, **names**, or **technical terms** within the essay text using Markdown (e.g., `This concept is about **machine learning**.` ). Use bolding selectively for emphasis on truly key terms, do not overdo it.
4.  **Tone:** Maintain an objective and informative tone.
5.  **Synthesis:** Synthesize the information rather than just listing points in the order they appeared.
6.  **Clarity:** Ignore conversational disfluencies (like 'um', 'uh', repeated words) unless crucial to the meaning.

Here is the transcript:
--- TRANSCRIPT ---
{transcript_text}
--- END TRANSCRIPT ---

Begin your structured essay below using Markdown for headings and bold keywords:
"""
    return prompt