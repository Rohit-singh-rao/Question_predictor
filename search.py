import re
import json

def clean_question_text(text):
    """Strips leading question numbers like Q1:, 1., or Q4: to allow true string matching."""
    return re.sub(r"^(?:Q)?\d+[\.\:\)]\s*", "", text, flags=re.IGNORECASE).strip()

def search_questions():
    """Searches questions by keyword/topic with clean deduplication."""
    try:
        with open("parsed_questions.json", "r", encoding="utf-8") as file:
            questions = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print("\n[!] Error: Unable to load database. Parse raw text first.")
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

    # Deduplicate by core question body
    unique_matches = {}
    for q in matches:
        core_text = clean_question_text(q["question"])
        if core_text not in unique_matches:
            unique_matches[core_text] = q
        else:
            existing = unique_matches[core_text]
            existing["exam_frequency"] = max(existing.get("exam_frequency", 1), q.get("exam_frequency", 1))

    print("\n" + "="*50)
    print(f"      SEARCH RESULTS FOR: '{keyword.upper()}'")
    print("="*50)

    for idx, (core_text, q) in enumerate(unique_matches.items(), 1):
        print(f"\n#{idx} | Topic: {q.get('topic', 'General')}")
        print(f"   Question: {core_text}")
        print(f"   Frequency across papers: {q.get('exam_frequency', 1)}")

if __name__ == "__main__":
    search_questions()