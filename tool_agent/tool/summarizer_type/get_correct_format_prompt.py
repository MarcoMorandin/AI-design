from .prompts.prompt import fix_formulas_prompt

def get_correct_format_prompt() -> str:
    """Return the instruction to correct format the formulas in a text"""
    return fix_formulas_prompt()