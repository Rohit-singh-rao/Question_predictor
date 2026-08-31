import json

def load_questions(filepath="parsed_questions.json"):
    """Safely loads questions from JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"\n[!] Error: Unable to read '{filepath}'. Make sure to parse raw text first.")
        return []

def run_analytics():
    """Calculates and displays summary stats for the question database."""
    questions = load_questions()
    if not questions:
        return

    total_count = len(questions)
    
    # Calculate topic breakdown
    topics = {}
    for q in questions:
        topic = q.get("topic", "Unassigned")
        topics[topic] = topics.get(topic, 0) + 1

    # Calculate average scores
    avg_importance = sum(q.get("importance", 3) for q in questions) / total_count
    avg_frequency = sum(q.get("exam_frequency", 3) for q in questions) / total_count

    # High priority count (Importance 4 or 5)
    high_priority = [q for q in questions if q.get("importance", 3) >= 4]

    print("\n=================================")
    print("    QUESTION BANK ANALYTICS      ")
    print("=================================")
    print(f"Total Questions Parsed : {total_count}")
    print(f"Average Importance     : {avg_importance:.1f} / 5.0")
    print(f"Average Exam Frequency : {avg_frequency:.1f} / 5.0")
    print(f"High-Priority Questions: {len(high_priority)}")
    
    print("\n--- TOPIC BREAKDOWN ---")
    for topic_name, count in topics.items():
        percentage = (count / total_count) * 100
        print(f"• {topic_name}: {count} question(s) ({percentage:.1f}%)")
    print("=================================")

if __name__ == "__main__":
    run_analytics()