import re
import json
from collections import Counter

def load_data(filepath="parsed_questions.json"):
    """Loads question data from JSON database."""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"\n[!] Error: Unable to read '{filepath}'. Parse raw text first.")
        return []

def clean_question_text(text):
    """Strips question labels like Q1:, 1. to unify duplicate questions."""
    return re.sub(r"^(?:Q)?\d+[\.\:\)]\s*", "", text, flags=re.IGNORECASE).strip()

def run_analytics():
    """Calculates and displays deduplicated summary stats for the question database."""
    questions = load_data()
    if not questions:
        return

    # Consolidate questions to calculate true frequencies
    unique_questions = {}
    for q in questions:
        core_text = clean_question_text(q.get("question", ""))
        if core_text not in unique_questions:
            unique_questions[core_text] = {
                "topic": q.get("topic", "General"),
                "count": 1
            }
        else:
            unique_questions[core_text]["count"] += 1

    total_unique_questions = len(unique_questions)
    total_raw_occurrences = sum(q["count"] for q in unique_questions.values())

    # Topic frequency counter
    topic_counts = Counter()
    for q_data in unique_questions.values():
        topic_counts[q_data["topic"]] += q_data["count"]

    # Calculate average scores
    avg_frequency = total_raw_occurrences / total_unique_questions if total_unique_questions else 0
    high_priority = [q for q in unique_questions.values() if q["count"] >= 2]

    print("\n=================================")
    print("    QUESTION BANK ANALYTICS      ")
    print("=================================")
    print(f"Unique Questions Parsed: {total_unique_questions}")
    print(f"Total Exam Occurrences : {total_raw_occurrences}")
    print(f"Avg Repetition Rate    : {avg_frequency:.1f}x per question")
    print(f"High-Priority Questions: {len(high_priority)} (Asked 2+ times)")

    print("\n--- TOPIC BREAKDOWN ---")
    for topic_name, count in topic_counts.most_common():
        percentage = (count / total_raw_occurrences) * 100
        print(f"• {topic_name}: {count} question(s) ({percentage:.1f}%)")
    print("=================================")

if __name__ == "__main__":
    run_analytics()