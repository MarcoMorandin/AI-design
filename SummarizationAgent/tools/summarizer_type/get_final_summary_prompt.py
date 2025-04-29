from .prompts.prompt import generate_final_summary

def get_final_summary_prompt(summary_type: str, text_was_splitted:bool) -> str:
    """Return the instruction to summarize a text
    available summary types:
    - "standard": Standard Summary
    - "technical": Technical Summary
    - "key_points": Key Points Summary
    - "layman": Simplified Summary

    Args:
        summary_type (str): The type of summary to generate.
        text_was_splitted (bool): Whether the orignal text was splitted or not.

    Returns:
        str: Prompt to summarize a text
    """
    return generate_final_summary(summary_type, text_was_splitted)