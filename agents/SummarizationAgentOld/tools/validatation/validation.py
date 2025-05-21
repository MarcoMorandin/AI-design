import textstat
import os
from openai import OpenAI
from dotenv import load_dotenv
from rouge import Rouge

load_dotenv()


api_key = os.getenv("GEMINI_API_KEY")
client = OpenAI(
    api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


def evaluate_summary(final_summary: str, source_document: str):
    """
    Evaluate the generated summary.
    This function calculates ROUGE scores comparing the summary to the source document,
    computes various readability metrics, and uses Gemini AI to analyze these metrics.
    
    Args:
        final_summary (str): The generated summary text to evaluate.
        source_document (str): The original document text used as reference.
        
    Returns:
        str: A detailed analysis of the summary quality based on ROUGE scores and 
             readability metrics.
    """
    # 1. Initialize ROUGE
    rouge = Rouge()

    # Calculate ROUGE scores
    # Note: ROUGE typically compares against reference summaries rather than source
    # Here we're using the source as reference, but ideally you'd have human references
    scores = rouge.get_scores(final_summary, source_document)[0]

    # 2. Readability metrics via textstat
    readability = {
        "Flesch Reading Ease": textstat.flesch_reading_ease(final_summary),
        "Flesch–Kincaid Grade Level": textstat.flesch_kincaid_grade(final_summary),
        "Gunning Fog Index": textstat.gunning_fog(final_summary),
        "SMOG Index": textstat.smog_index(final_summary),
        "Average Sentence Length": textstat.avg_sentence_length(final_summary),
        "Average Syllables per Word": textstat.avg_syllables_per_word(final_summary),
        "Type–Token Ratio": len(set(final_summary.split()))
        / len(final_summary.split()),
    }

    # Convert the scores dictionary to a string with proper formatting
    scores_str = "\n".join([f"{k}: {v}" for k, v in scores.items()])
    readability_str = "\n".join([f"{k}: {v}" for k, v in readability.items()])

    prompt = f"""Analyze these summary quality metrics and provide a concise evaluation:

    --- ROUGE SCORES ---
    {scores_str}
    --- ROUGE SCORES ---

    --- READABILITY METRICS ---
    {readability_str}
    --- READABILITY METRICS ---
    
    Guidelines for analysis:
    - ROUGE scores: Higher values (closer to 1.0) indicate better content overlap with source
    - Flesch Reading Ease: 60-70 is ideal (higher = more readable)
    - Grade levels: Lower values indicate more accessible text
    - Balance content preservation with readability
    
    Provide a brief, actionable assessment focusing on strengths and areas for improvement.
    """

    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "You are a math syntax expert."},
            {"role": "user", "content": prompt},
        ],
    )

    # Return the actual text with properly formatted formulas, not just the prompt
    return response.choices[0].message.content


if __name__ == "__main__":
    # Example usage
    final_summary = "This is a sample summary."
    source_document = "This is the original document text."

    print(evaluate_summary(final_summary, source_document))
