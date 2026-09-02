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

def clean_exam_headers(raw_text):
    """Strips exam metadata, page headers, section banners, and solution labels."""
    # Strip top university/course header blocks up to the first Question tag
    text = re.sub(r"(?i)Faculty of Engineering.*?(?=(?:Q\s*)?[A-C]\d+\b)", "", raw_text, flags=re.DOTALL)
    # Strip Section labels like 'SECTION A', 'SECTION-C'
    text = re.sub(r"(?i)SECTION\s*[-–—]?\s*[A-Z]", "", text)
    # Strip common table header noise
    text = re.sub(r"(?i)S\.No\.\s*Marks\s*CO\s*Q", "", text)
    return text

def format_question_text(text):
    """Adds clean line breaks and indentations to make raw PDF text human-readable."""
    # Insert newlines before assembly instructions
    text = re.sub(r"\s+(LOAD|ADD|STORE|MUL|SUB|CMP|MOVE|BEQ|BLE|BR|HALT)\b", r"\n   \1", text)
    
    # Insert newlines before numbered steps (e.g., Step 1:, Step 2:)
    text = re.sub(r"\s+(Step\s*\d+:)", r"\n\n   \1", text)
    
    # Insert newlines before sub-parts like (a), (b)
    text = re.sub(r"\s+(\([a-z]\))", r"\n   \1", text)
    
    # Insert newlines before bullet points or explanations
    text = re.sub(r"\s+(•|Explanation)", r"\n   \1", text)
    
    # Insert newlines before marks tags like [2], [6], [10]
    text = re.sub(r"\s+(\[\d+\])", r" \1\n", text)
    
    return text.strip()

def split_into_questions(raw_text):
    """Splits raw text strictly into main questions (Q A1..A5, Q B1..B5, Q C1..C2, Q D1..D2)."""
    cleaned_text = clean_exam_headers(raw_text)

    # Stricter Regex: Matches explicit 'Q' headers like 'Q A1', 'Q B4', 'Q C1', 'Q D1'
    # or standalone section markers at line starts only.
    pattern = r"(?=(?:^|\n)\s*(?:Q\s*)?[A-D]\d+[\.\:\)]?\s+)"
    chunks = re.split(pattern, cleaned_text, flags=re.IGNORECASE)
    
    questions = []
    for chunk in chunks:
        cleaned = chunk.strip()
        # Ensure it starts with a valid question marker and contains real question text
        if len(cleaned) > 25 and re.match(r"(?i)^(?:Q\s*)?[A-D]\d+", cleaned):
            # Exclude chunks that are just single math formula lines (e.g., C4 = G3 + ...)
            if not re.match(r"(?i)^C\d+\s*=", cleaned):
                formatted = format_question_text(cleaned)
                questions.append(formatted)
            
    return questions

def generate_global_taxonomy(questions_list):
    """PASS 1: Analyzes all exam questions to extract a unified, dynamic taxonomy."""
    # Sample question texts for LLM context
    sample_text = "\n".join([f"- {q[:150]}" for q in questions_list[:10]])
    
    prompt = (
        "You are an expert academic curriculum parser. Read these sample questions from an exam:\n"
        f"{sample_text}\n\n"
        "Generate a dynamic list of 5 to 8 concise, high-level subject topics that represent this entire exam paper. "
        "Return ONLY a valid JSON object with NO markdown formatting, ticks, or text outside the JSON: "
        '{"topics": ["Topic 1", "Topic 2", "Topic 3"]}'
    )

    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}]
        )

        raw_text = response['message']['content'].strip()
        json_match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(0))
            topics = data.get("topics", [])
            if isinstance(topics, list) and len(topics) > 0:
                return topics
    except Exception as e:
        print(f"\n[!] Warning: Pass 1 taxonomy generation fell back. ({e})")
        
    return ["General Concepts"]

def generate_ai_topic(question_text, taxonomy_list):
    """PASS 2: Maps an individual question strictly to one of the dynamic global topics."""
    topics_str = ", ".join([f"'{t}'" for t in taxonomy_list])
    
    prompt = (
        f"Examine this exam question: '{question_text}'.\n"
        f"Classify this question strictly into ONE of the following topics: [{topics_str}]. "
        "Select the single best matching topic. "
        "Return ONLY a valid JSON object with NO markdown or extra text: "
        '{"topic": "Selected Topic Name"}'
    )

    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}]
        )

        raw_text = response['message']['content'].strip()
        json_match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(0))
            return data.get("topic", taxonomy_list[0])
        else:
            return taxonomy_list[0]

    except Exception:
        return taxonomy_list[0]

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
    """Parses questions using Two-Pass AI classification & Frequency tracking."""
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

    total_q = len(questions_list)
    
    # PASS 1: Extract global dynamic taxonomy
    print(f"\n[...] PASS 1: Analyzing document structure & generating dynamic topic taxonomy...")
    dynamic_taxonomy = generate_global_taxonomy(questions_list)
    print(f"[+] PASS 1 Complete! Identified {len(dynamic_taxonomy)} core topics:")
    for t in dynamic_taxonomy:
        print(f"    - {t}")

    # PASS 2: Classify questions into the dynamic taxonomy
    print(f"\n[...] PASS 2: Classifying {total_q} questions into dynamic taxonomy...")

    parsed_data = []

    for idx, q_text in enumerate(questions_list, 1):
        print(f" -> [{idx}/{total_q}] Mapping topic...", end="\r", flush=True)
        topic = generate_ai_topic(q_text, dynamic_taxonomy)
        freq_count = calculate_frequency(q_text, questions_list)
        
        parsed_data.append({
            "id": idx,
            "question": q_text,
            "topic": topic,
            "exam_frequency": freq_count,
            "importance": min(5, freq_count),
            "recency_score": 3
        })

    print(f"\n[+] AI processing complete for all {total_q} questions!")

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(parsed_data, file, indent=4)
        print(f"[+] Success! Saved {len(parsed_data)} parsed questions into '{output_file}'.")
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
        print(f"ID {q['id']}: {q['question'][:80]}... [{q.get('topic', 'General')}]")

    q_id_input = input("\nEnter Question ID to edit (or press Enter to cancel): ").strip()
    if not q_id_input.isdigit():
        print("Cancelled.")
        return

    q_id = int(q_id_input)
    target_q = next((q for q in questions if q["id"] == q_id), None)

    if not target_q:
        print(f"[!] Question with ID {q_id} not found.")
        return

    print(f"\nEditing Question #{q_id}: '{target_q['question'][:100]}...'")
    
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
        print(f"\n[+] Success! Saved metadata updates for Question #{q_id}.")
    except IOError as e:
        print(f"\n[!] Error saving updates: {e}")

if __name__ == "__main__":
    run_parser()