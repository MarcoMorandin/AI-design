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
        "Flesch Reading Ease":        textstat.flesch_reading_ease(final_summary),
        "Flesch–Kincaid Grade Level": textstat.flesch_kincaid_grade(final_summary),
        "Gunning Fog Index":          textstat.gunning_fog(final_summary),
        "SMOG Index":                 textstat.smog_index(final_summary),
        "Average Sentence Length":    textstat.avg_sentence_length(final_summary),
        "Average Syllables per Word": textstat.avg_syllables_per_word(final_summary),
        "Type–Token Ratio":           len(set(final_summary.split())) / len(final_summary.split()),
    }

    prompt=f"""I provide you some metrics about the valuation of the summary about a general document. I wanto you to analyze the metrics and return the analysis of the metrics
        --- QEVAL SCORE ---
        {scores}
        --- QEVAL SCORE ---

        --- REDABILITY SCORE ---
        {readability}
        --- REDABILITY SCORE ---
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
    # Example usage—replace with your actual document and summary
    source_document = (
        "OpenAI’s GPT-4 is a state-of-the-art large language model that achieves strong "
        "performance across various benchmarks and can be used for tasks like summarization."
    )
    final_summary = (
        "GPT-4, developed by OpenAI, is a powerful language model excelling at many tasks, "
        "including summarization, and outperforms previous models on several benchmarks."
    )

    score, read_stats = evaluate_summary(final_summary, source_document)

    print("=== QuestEval Score ===")
    print(f"{score:.4f}\n")

    print("=== Readability Metrics ===")
    for metric, value in read_stats.items():
        print(f"{metric}: {value:.2f}")
