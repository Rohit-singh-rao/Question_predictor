import os
import re
import json
import ollama
from pypdf import PdfReader

def extract_text_from_file(filepath):
    """Reads raw text from .txt or .pdf files."""
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

def split_into_questions(raw_text):
    """Splits raw text into individual questions by question numbers (e.g., Q1, 1., Q2:)."""
    # Pattern looks for lines starting with Q1, 1., 1), etc.
    pattern = r"(?=(?:^|\n)\s*(?:Q)?\d+[\.\:\)]\s*)"
    chunks = re.split(pattern, raw_text, flags=re.IGNORECASE)
    
    questions = []
    for chunk in chunks:
        cleaned = chunk.strip()
        if cleaned:
            # Clean up internal linebreaks inside the question body
            cleaned = re.sub(r"\s+", " ", cleaned)
            questions.append(cleaned)
            
    return questions

def generate_ai_topic(question_text):
    """Uses local Llama 3 model via Ollama to generate a clean, dynamic topic name."""
    prompt = (
        f"Analyze this exam question: '{question_text}'. "
        "Invent a concise, highly relevant topic name for it (e.g., 'Database Normalization', 'Pointers in C'). "
        "Return ONLY a valid JSON object with NO markdown formatting: "
        '{"topic": "Generated Topic Name"}'
    )

    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}]
        )

        raw_text = response['message']['content'].strip()
        clean_json = raw_text.removeprefix("```json").removesuffix("```").strip()
        data = json.loads(clean_json)

        return data.get("topic", "General")

    except Exception as e:
        print(f"  [!] Local AI Error ({e}). Defaulting to 'General'.")
        return "General"

def calculate_frequency(target_text, all_questions_text):
    """Counts how many times a question or key phrase appears across all past papers."""
    target_clean = re.sub(r'[^a-zA-Z0-9 ]', '', target_text.lower()).strip()
    
    count = 0
    for q in all_questions_text:
        q_clean = re.sub(r'[^a-zA-Z0-9 ]', '', q.lower()).strip()
        if target_clean in q_clean or q_clean in target_clean:
            count += 1
            
    return max(1, count)

def run_parser(output_file="parsed_questions.json"):
    """Parses questions, generates AI topics, and calculates true frequency count."""
    user_input = input("\nEnter file path to parse [default: sample_questions.txt]: ").strip()
    input_file = user_input if user_input else "sample_questions.txt"

    try:
        raw_text = extract_text_from_file(input_file)
    except FileNotFoundError:
        print(f"\n[!] Error: Source file '{input_file}' not found.")
        return
    except Exception as e:
        print(f"\n[!] Error reading file '{input_file}': {e}")
        return

    questions_list = split_into_questions(raw_text)
    
    if not questions_list:
        print(f"\n[!] Warning: No formatted questions found in '{input_file}'.")
        return

    print(f"\n[...] Processing {len(questions_list)} question(s) with AI topics & Frequency tracking...")

    parsed_data = []

    for idx, q_text in enumerate(questions_list, 1):
        topic = generate_ai_topic(q_text)
        freq_count = calculate_frequency(q_text, questions_list)
        
        parsed_data.append({
            "id": idx,
            "question": q_text,
            "topic": topic,
            "exam_frequency": freq_count,
            "importance": min(5, freq_count),
            "recency_score": 3
        })

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(parsed_data, file, indent=4)
        print(f"\n[+] Success! Parsed {len(parsed_data)} questions into '{output_file}'.")
    except IOError as e:
        print(f"\n[!] Error saving JSON file: {e}")

def update_metadata():
    """Allows user to update metadata for a question."""
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