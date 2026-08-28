import json

def calculate_priority_score(question):
    """Calculates a weighted priority score out of 10.0 points."""
    importance = question.get("importance", 1)
    frequency = question.get("exam_frequency", 1)
    recency = question.get("recency_score", 1)
    
    score = (importance * 1.0) + (frequency * 0.6) + (recency * 0.4)
    return round(score, 2)

# 1. Load database
with open("parsed_questions.json", "r", encoding="utf-8") as file:
    question_db = json.load(file)

# 2. Calculate priority scores
for q in question_db:
    q["priority_score"] = calculate_priority_score(q)

# 3. User input for topic filter
target_topic = input("Enter topic to predict (or press Enter for ALL topics): ").strip()

# 4. Filter by topic
if target_topic:
    matches = [q for q in question_db if target_topic.lower() in q["topic"].lower()]
else:
    matches = question_db

# 5. Sort by calculated priority score
ranked_questions = sorted(matches, key=lambda item: item["priority_score"], reverse=True)

# 6. Top-N filter
if ranked_questions:
    top_n_input = input(f"How many top predictions do you want to view? (1-{len(ranked_questions)}): ").strip()
    top_n = int(top_n_input) if top_n_input.isdigit() else len(ranked_questions)
    final_predictions = ranked_questions[:top_n]
else:
    final_predictions = []

# 7. Format and print report
report_lines = []
report_lines.append("==================================================")
report_lines.append(f"      EXAM PREDICTION REPORT: '{target_topic or 'ALL'}'")
report_lines.append("==================================================\n")

if not final_predictions:
    report_lines.append("No matching questions found.")
else:
    for rank, q in enumerate(final_predictions, start=1):
        report_lines.append(f"#{rank} [Score: {q['priority_score']}/10.0] | Topic: {q['topic']}")
        report_lines.append(f"   Question: {q['question']}")
        report_lines.append(f"   Breakdown: Imp={q['importance']} | Freq={q['exam_frequency']} | Recency={q['recency_score']}\n")

# Display in terminal
report_text = "\n".join(report_lines)
print(f"\n{report_text}")

# 8. Export Option
if final_predictions:
    save_choice = input("Do you want to save this report to a file? (y/n): ").strip().lower()
    if save_choice == 'y':
        file_name = "predicted_exam_prep.txt"
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(report_text)
        print(f"Report saved successfully to '{file_name}'!")