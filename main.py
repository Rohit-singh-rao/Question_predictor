import re
import json

import re
import json
from pypdf import PdfReader

def extract_text_from_file(filepath):
    """Reads raw text from either a .txt or .pdf file."""
    if filepath.lower().endswith(".pdf"):
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    else:
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()

def run_parser(output_file="parsed_questions.json"):
    """Parses raw question text from a user-specified .txt or .pdf file into structured JSON."""
    user_input = input("\nEnter file path to parse [default: sample_questions.txt]: ").strip()
    input_file = user_input if user_input else "sample_questions.txt"

    try:
        content = extract_text_from_file(input_file)
    except FileNotFoundError:
        print(f"\n[!] Error: Source file '{input_file}' not found.")
        return
    except Exception as e:
        print(f"\n[!] Error reading file '{input_file}': {e}")
        return

    # Matches questions formatted like Q1: Text or 1. Text
    raw_matches = re.findall(r"(?:Q)?(\d+)[\.\)]?\s*(.+)", content)
    
    parsed_data = []
    for item in raw_matches:
        q_id = int(item[0])
        q_text = item[1].strip()
        
        parsed_data.append({
            "id": q_id,
            "question": q_text,
            "topic": "General",
            "importance": 3,
            "exam_frequency": 3,
            "recency_score": 3
        })

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(parsed_data, file, indent=4)
        print(f"\n[+] Success! Parsed {len(parsed_data)} questions from '{input_file}' into '{output_file}'.")
    except IOError as e:
        print(f"\n[!] Error saving JSON file: {e}")

def update_metadata():
    """Allows user to update metadata (topic, importance, frequency, recency) for a question."""
    try:
        with open("parsed_questions.json", "r", encoding="utf-8") as file:
            questions = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print("\n[!] Error loading database. Parse raw text first.")
        return

    if not questions:
        print("\n[!] No questions found in database.")
        return

    print("\n--- AVAILABLE QUESTIONS ---")
    for q in questions:
        print(f"ID {q['id']}: {q['question']} [{q.get('topic', 'General')}]")

    q_id_input = input("\nEnter Question ID to edit (or press Enter to cancel): ").strip()
    if not q_id_input.isdigit():
        print("Cancelled.")
        return

    q_id = int(q_id_input)
    target_q = next((q for q in questions if q["id"] == q_id), None)

    if not target_q:
        print(f"[!] Question with ID {q_id} not found.")
        return

    print(f"\nEditing Question #{q_id}: '{target_q['question']}'")
    
    new_topic = input(f"Enter Topic [{target_q.get('topic', 'General')}]: ").strip()
    if new_topic:
        target_q["topic"] = new_topic

    for key in ["importance", "exam_frequency", "recency_score"]:
        current_val = target_q.get(key, 3)
        val_input = input(f"Enter {key.replace('_', ' ').title()} (1-5) [{current_val}]: ").strip()
        if val_input.isdigit() and 1 <= int(val_input) <= 5:
            target_q[key] = int(val_input)

    try:
        with open("parsed_questions.json", "w", encoding="utf-8") as file:
            json.dump(questions, file, indent=4)
        print(f"\n[+] Success! Updated metadata for Question #{q_id}.")
    except IOError as e:
        print(f"\n[!] Error saving updates: {e}")

if __name__ == "__main__":
    run_parser()