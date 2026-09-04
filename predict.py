import re
import json

def load_data(filename="parsed_questions.json"):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def clean_question_text(text):
    """Strips leading question prefixes like Q1:, A1, Q A1, or C2 for deduplication."""
    return re.sub(r"^(?:Q\s*)?[A-C]?\d+[\.\:\)]?\s*", "", text, flags=re.IGNORECASE).strip()

def run_predictor():
    """Aggregates and displays topic frequencies across all past exam papers."""
    questions = load_data()
    if not questions:
        print("\n[!] No questions available to analyze. Parse data first.")
        return

    filter_topic = input("\nEnter topic to inspect (or press Enter for ALL topics): ").strip()

    # Apply filter if user specified a topic
    if filter_topic:
        target_questions = [q for q in questions if filter_topic.lower() in q.get("topic", "").lower()]
    else:
        target_questions = questions

    if not target_questions:
        print(f"\n[!] No questions found for topic '{filter_topic}'.")
        return

    # Aggregate question counts and occurrences per topic
    topic_summary = {}

    for q in target_questions:
        topic = q.get("topic", "General")
        q_text = clean_question_text(q.get("question", ""))
        freq = q.get("exam_frequency", 1)

        if topic not in topic_summary:
            topic_summary[topic] = {
                "total_occurrences": 0,
                "questions": {}
            }

        topic_summary[topic]["total_occurrences"] += freq
        
        # Deduplicate question entries within the topic
        if q_text not in topic_summary[topic]["questions"]:
            topic_summary[topic]["questions"][q_text] = {
                "display_text": q.get("question", ""),
                "count": freq
            }
        else:
            topic_summary[topic]["questions"][q_text]["count"] += freq

    total_exam_questions = sum(t["total_occurrences"] for t in topic_summary.values())

    # Sort topics by total occurrence frequency descending
    sorted_topics = sorted(
        topic_summary.items(),
        key=lambda item: item[1]["total_occurrences"],
        reverse=True
    )

    print("\n" + "="*65)
    print("      PAST EXAM PAPERS: TOPIC FREQUENCY ANALYSIS      ")
    print("="*65)
    print(f"{'Topic Name':<35} | {'Questions':<10} | {'Weightage':<10}")
    print("-" * 65)

    for topic, data in sorted_topics:
        weightage = (data["total_occurrences"] / total_exam_questions * 100) if total_exam_questions > 0 else 0
        print(f"{topic[:34]:<35} | {data['total_occurrences']:<10} | {weightage:>8.1f}%")

    print("="*65)
    print(f"Total Questions Analyzed: {total_exam_questions}")
    print("="*65)

    # Detailed breakdown per topic
    show_details = input("\nDo you want to see the questions under each topic? (y/N): ").strip().lower()
    if show_details == 'y':
        for idx, (topic, data) in enumerate(sorted_topics, 1):
            print(f"\n\n[{idx}] TOPIC: {topic.upper()} ({data['total_occurrences']} question(s) asked)")
            print("-" * 60)
            for q_idx, q_data in enumerate(data["questions"].values(), 1):
                print(f"  {q_idx}. [Asked {q_data['count']} time(s)]")
                print(f"     {q_data['display_text'][:150]}...\n")

if __name__ == "__main__":
    run_predictor()