import os
import re
import json

def load_data(filename="parsed_questions.json"):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def clean_question_text(text):
    """Strips leading question numbers like Q1:, 1., or Q4: for true matching."""
    return re.sub(r"^(?:Q)?\d+[\.\:\)]\s*", "", text, flags=re.IGNORECASE).strip()

def calculate_score(imp, freq, recency=3):
    """Calculates priority score based on frequency, importance, and recency."""
    return round((imp * 0.4) + (freq * 0.4) + (recency * 0.2), 1)

def export_prediction_report():
    """Generates a formatted prediction report and exports it to a TXT or MD file."""
    questions = load_data()
    if not questions:
        print("\n[!] No questions available to export. Parse data first.")
        return

    filter_topic = input("\nEnter topic to export (or press Enter for ALL topics): ").strip()
    
    if filter_topic:
        filtered = [q for q in questions if filter_topic.lower() in q.get("topic", "").lower()]
    else:
        filtered = questions

    if not filtered:
        print(f"\n[!] No questions found for topic '{filter_topic}'.")
        return

    # Deduplicate questions
    unique_questions = {}
    for q in filtered:
        core_text = clean_question_text(q["question"])
        if core_text not in unique_questions:
            unique_questions[core_text] = {
                "question": core_text,
                "topic": q.get("topic", "General"),
                "count": 1,
                "recency": q.get("recency_score", 3)
            }
        else:
            unique_questions[core_text]["count"] += 1

    # Score and rank
    ranked = []
    for q_data in unique_questions.values():
        freq = q_data["count"]
        imp = min(5, freq)
        score = calculate_score(imp, freq, q_data["recency"])
        
        ranked.append({
            "question": q_data["question"],
            "topic": q_data["topic"],
            "importance": imp,
            "frequency": freq,
            "recency": q_data["recency"],
            "score": score
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    # File format selection
    print("\nSelect export format:")
    print("1. Text File (.txt)")
    print("2. Markdown File (.md)")
    fmt_choice = input("Choice (1-2) [default: 1]: ").strip()
    ext = ".md" if fmt_choice == "2" else ".txt"

    topic_label = filter_topic.replace(" ", "_").lower() if filter_topic else "all_topics"
    default_filename = f"prediction_report_{topic_label}{ext}"
    filename = input(f"Enter output filename [default: {default_filename}]: ").strip()
    if not filename:
        filename = default_filename

    # Build report content
    header_title = f"EXAM PREDICTION REPORT: '{filter_topic.upper() if filter_topic else 'ALL TOPICS'}'"
    lines = []

    if ext == ".md":
        lines.append(f"# {header_title}\n")
        lines.append(f"**Total High-Probability Questions:** {len(ranked)}\n")
        lines.append("---\n")
        for idx, q in enumerate(ranked, 1):
            lines.append(f"### {idx}. {q['question']}")
            lines.append(f"- **Topic:** {q['topic']}")
            lines.append(f"- **Prediction Score:** {q['score']} / 10.0")
            lines.append(f"- **Stats:** Frequency={q['frequency']} | Importance={q['importance']} | Recency={q['recency']}\n")
    else:
        lines.append("=" * 60)
        lines.append(f"      {header_title}")
        lines.append("=" * 60 + "\n")
        lines.append(f"Total High-Probability Questions: {len(ranked)}\n")
        for idx, q in enumerate(ranked, 1):
            lines.append(f"#{idx} [Score: {q['score']}/10.0] | Topic: {q['topic']}")
            lines.append(f"   Question: {q['question']}")
            lines.append(f"   Breakdown: Imp={q['importance']} | Freq={q['frequency']} | Recency={q['recency']}\n")

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n[+] Success! Report saved to '{filename}'.")
    except IOError as e:
        print(f"\n[!] Error saving report: {e}")

if __name__ == "__main__":
    export_prediction_report()