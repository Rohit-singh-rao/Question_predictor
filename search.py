import json

# 1. Load the question database
with open("parsed_questions.json", "r", encoding="utf-8") as file:
    question_db = json.load(file)

# 2. Get search keyword from the user
search_term = input("Enter a keyword to search: ").lower()

# 3. Filter and display matching questions
matches = []
for item in question_db:
    if search_term in item["question"].lower():
        matches.append(item)

print(f"\nFound {len(matches)} matching question(s):")
for q in matches:
    print(f"- [ID {q['id']}] {q['question']}")