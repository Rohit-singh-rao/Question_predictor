import json
import re

# 1. Read file
with open("sample_questions.txt", "r", encoding="utf-8") as file:
    text = file.read()

# 2. Extract questions
pattern = r"Q\d+:\s*(.+)"
questions = re.findall(pattern, text)

# 3. Create structured_data
structured_data = []
for index, q in enumerate(questions):
    item = {"id": index + 1, "question": q}
    structured_data.append(item)

# 4. Save to JSON file
with open("parsed_questions.json", "w", encoding="utf-8") as file:
    json.dump(structured_data, file, indent=4)