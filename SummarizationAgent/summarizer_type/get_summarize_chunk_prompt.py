from typing import List
from .prompts.prompt import summary_prompt


def get_prompt_to_summarize_chunk(summary_type: str="technical") -> str:
    """Return the instruction to summarize a text
    available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        text (str): The text to be summarized.
        summary_type (SummaryType): The type of summary to generate.


    Returns:
        str: Prompt to summarize a text
    """
    return summary_prompt(summary_type)
    