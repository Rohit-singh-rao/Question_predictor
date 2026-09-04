import re
import json

def clean_question_text(text):
    """Strips leading question numbers and section headers (e.g., Q1:, A1., Q A1, C2) for true string matching."""
    if not text:
        return ""
    return re.sub(r"^(?:Q\s*)?[A-C]?\d+[\.\:\)]?\s*", "", text, flags=re.IGNORECASE).strip()

def search_questions(filename="parsed_questions.json"):
    """Searches questions by keyword or topic with clean text deduplication."""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            questions = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"\n[!] Error: Unable to load '{filename}'. Parse raw text first using Option 1.")
        return

    if not questions:
        print("\n[!] No questions found in database.")
        return

    keyword = input("\nEnter keyword or topic to search for: ").strip().lower()
    if not keyword:
        print("Search cancelled.")
        return

    matches = [
        q for q in questions 
        if keyword in q.get("question", "").lower() or keyword in q.get("topic", "").lower()
    ]

    if not matches:
        print(f"\n[!] No matching questions found for '{keyword}'.")
        return

    unique_matches = {}
    for q in matches:
        core_text = clean_question_text(q.get("question", ""))
        if core_text not in unique_matches:
            unique_matches[core_text] = {
                "topic": q.get("topic", "General"),
                "exam_frequency": q.get("exam_frequency", 1)
            }
        else:
            unique_matches[core_text]["exam_frequency"] += q.get("exam_frequency", 1)

    print("\n" + "="*60)
    print(f"      SEARCH RESULTS FOR: '{keyword.upper()}' ({len(unique_matches)} matched)")
    print("="*60)

    for idx, (core_text, data) in enumerate(unique_matches.items(), 1):
        print(f"\n#{idx} | Topic: {data['topic']}")
        print(f"   Question: {core_text[:180]}...")
        print(f"   Frequency across papers: {data['exam_frequency']}")

if __name__ == "__main__":
    search_questions()