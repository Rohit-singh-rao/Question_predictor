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

def calculate_score(imp, freq, recency=3):
    """Calculates priority score based on frequency, importance, and recency."""
    return round((imp * 0.4) + (freq * 0.4) + (recency * 0.2), 1)

def run_predictor():
    """Ranks and displays unique question predictions based on consolidated frequency."""
    questions = load_data()
    if not questions:
        print("\n[!] No questions available to predict. Parse data first.")
        return

    filter_topic = input("\nEnter topic to predict (or press Enter for ALL topics): ").strip()
    
    if filter_topic:
        filtered_questions = [q for q in questions if filter_topic.lower() in q.get("topic", "").lower()]
    else:
        filtered_questions = questions

    if not filtered_questions:
        print(f"\n[!] No questions found for topic '{filter_topic}'.")
        return

    # Group duplicate questions by stripping question prefixes while retaining full text for display
    unique_questions = {}
    for q in filtered_questions:
        core_text = clean_question_text(q["question"])
        if core_text not in unique_questions:
            unique_questions[core_text] = {
                "display_question": q["question"],
                "topic": q.get("topic", "General"),
                "count": 1,
                "recency": q.get("recency_score", 3)
            }
        else:
            unique_questions[core_text]["count"] += 1

    # Calculate real frequency & score for ranked output
    ranked = []
    for q_data in unique_questions.values():
        freq = q_data["count"]
        imp = min(5, freq)  # Importance scales directly with frequency
        score = calculate_score(imp, freq, q_data["recency"])
        
        ranked.append({
            "question": q_data["display_question"],
            "topic": q_data["topic"],
            "importance": imp,
            "frequency": freq,
            "recency": q_data["recency"],
            "score": score
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    total_avail = len(ranked)
    print("\n" + "="*50)
    print(f"      EXAM PREDICTION REPORT: '{filter_topic.upper() if filter_topic else 'ALL'}'")
    print("="*50)

    top_n_input = input(f"\nHow many top predictions do you want to view? (1-{total_avail}) [default: ALL ({total_avail})]: ").strip()

    if top_n_input.isdigit() and int(top_n_input) > 0:
        limit = min(int(top_n_input), total_avail)
    else:
        limit = total_avail  # Shows ALL questions if Enter is pressed

    for idx, q in enumerate(ranked[:limit], 1):
        print(f"\n#{idx} [Score: {q['score']}/10.0] | Topic: {q['topic']}")
        print(f"   Question: {q['question']}")
        print(f"   Breakdown: Imp={q['importance']} | Freq={q['frequency']} | Recency={q['recency']}")

if __name__ == "__main__":
    run_predictor()