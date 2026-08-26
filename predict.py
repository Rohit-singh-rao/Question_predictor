import json

# 1. Load database
with open("parsed_questions.json", "r", encoding="utf-8") as file:
    question_db = json.load(file)

# 2. Get user input for target topic
target_topic = input("Enter topic to predict (e.g., Environments, Git, Python Core): ").strip()

# 3. Filter questions by topic (case-insensitive)
matches = [q for q in question_db if target_topic.lower() in q["topic"].lower()]

# 4. Sort matching questions by importance score (highest first)
ranked_questions = sorted(matches, key=lambda item: item["importance"], reverse=True)

# 5. Display the Prediction Report
print(f"\n--- PREDICTION REPORT FOR TOPIC: '{target_topic}' ---")
if not ranked_questions:
    print("No questions found for that topic.")
else:
    for rank, q in enumerate(ranked_questions, start=1):
        print(f"Priority #{rank} [Importance: {q['importance']}/5] (ID {q['id']}): {q['question']}")