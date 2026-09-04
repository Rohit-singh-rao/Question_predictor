import os
import re
import json

def load_data(filename="parsed_questions.json"):
    """Loads parsed question database."""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def clean_question_text(text):
    """Strips leading question numbers and section headers for clean text matching."""
    if not text:
        return ""
    return re.sub(r"^(?:Q\s*)?[A-C]?\d+[\.\:\)]?\s*", "", text, flags=re.IGNORECASE).strip()

def export_prediction_report():
    """Generates a topic frequency summary report and exports it to .txt or .md."""
    questions = load_data()
    if not questions:
        print("\n[!] No questions available to export. Parse data first using Option 1.")
        return

    filter_topic = input("\nEnter topic to export (or press Enter for ALL topics): ").strip()
    
    if filter_topic:
        target_questions = [q for q in questions if filter_topic.lower() in q.get("topic", "").lower()]
    else:
        target_questions = questions

    if not target_questions:
        print(f"\n[!] No questions found for topic '{filter_topic}'.")
        return

    # Aggregate topic statistics
    topic_summary = {}
    for q in target_questions:
        topic = q.get("topic", "General")
        q_text = clean_question_text(q.get("question", ""))
        freq = q.get("exam_frequency", 1)

        if topic not in topic_summary:
            topic_summary[topic] = {"total_occurrences": 0, "questions": {}}

        topic_summary[topic]["total_occurrences"] += freq
        
        if q_text not in topic_summary[topic]["questions"]:
            topic_summary[topic]["questions"][q_text] = {"display_text": q.get("question", ""), "count": freq}
        else:
            topic_summary[topic]["questions"][q_text]["count"] += freq

    total_exam_questions = sum(t["total_occurrences"] for t in topic_summary.values())
    sorted_topics = sorted(topic_summary.items(), key=lambda item: item[1]["total_occurrences"], reverse=True)

    # Export format selection
    print("\nSelect export format:")
    print("1. Text File (.txt)")
    print("2. Markdown File (.md)")
    fmt_choice = input("Choice (1-2) [default: 1]: ").strip()
    ext = ".md" if fmt_choice == "2" else ".txt"

    topic_label = filter_topic.replace(" ", "_").lower() if filter_topic else "all_topics"
    default_filename = f"topic_report_{topic_label}{ext}"
    filename = input(f"Enter output filename [default: {default_filename}]: ").strip() or default_filename

    lines = []
    report_title = f"EXAM TOPIC FREQUENCY REPORT: '{filter_topic.upper() if filter_topic else 'ALL TOPICS'}'"

    if ext == ".md":
        lines.append(f"# {report_title}\n")
        lines.append(f"**Total Questions Analyzed:** {total_exam_questions}\n")
        lines.append("| Topic Name | Unique Questions | Weightage (%) |")
        lines.append("| :--- | :---: | :---: |")
        for topic, data in sorted_topics:
            weightage = (data["total_occurrences"] / total_exam_questions * 100) if total_exam_questions > 0 else 0
            lines.append(f"| {topic} | {data['total_occurrences']} | {weightage:.1f}% |")
        lines.append("\n## Detailed Question Breakdown\n")
        for topic, data in sorted_topics:
            lines.append(f"### {topic} ({data['total_occurrences']} Qs)")
            for q_data in data["questions"].values():
                lines.append(f"- **[Asked {q_data['count']}x]:** {q_data['display_text']}")
            lines.append("")
    else:
        lines.append("=" * 65)
        lines.append(f"      {report_title}")
        lines.append("=" * 65)
        lines.append(f"{'Topic Name':<35} | {'Questions':<10} | {'Weightage':<10}")
        lines.append("-" * 65)
        for topic, data in sorted_topics:
            weightage = (data["total_occurrences"] / total_exam_questions * 100) if total_exam_questions > 0 else 0
            lines.append(f"{topic[:34]:<35} | {data['total_occurrences']:<10} | {weightage:>8.1f}%")
        lines.append("=" * 65)
        lines.append(f"Total Questions Analyzed: {total_exam_questions}\n")
        lines.append("\n--- DETAILED QUESTION BREAKDOWN ---")
        for topic, data in sorted_topics:
            lines.append(f"\nTOPIC: {topic.upper()} ({data['total_occurrences']} Qs)")
            for q_idx, q_data in enumerate(data["questions"].values(), 1):
                lines.append(f"  {q_idx}. [Asked {q_data['count']}x] {q_data['display_text']}")

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n[+] Success! Report exported to '{filename}'.")
    except IOError as e:
        print(f"\n[!] Error saving report: {e}")

if __name__ == "__main__":
    export_prediction_report()