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
    text = re.sub(r"(?i)Faculty of Engineering.*?(?=(?:Q\s*)?[A-C]\d+\b)", "", raw_text, flags=re.DOTALL)
    text = re.sub(r"(?i)SECTION\s*[-–—]?\s*[A-Z]", "", text)
    text = re.sub(r"(?i)S\.No\.\s*Marks\s*CO\s*Q", "", text)
    return text

def format_question_text(text):
    """Adds clean line breaks and indentations to make raw PDF text human-readable."""
    text = re.sub(r"\s+(LOAD|ADD|STORE|MUL|SUB|CMP|MOVE|BEQ|BLE|BR|HALT)\b", r"\n   \1", text)
    text = re.sub(r"\s+(Step\s*\d+:)", r"\n\n   \1", text)
    text = re.sub(r"\s+(\([a-z]\))", r"\n   \1", text)
    text = re.sub(r"\s+(•|Explanation)", r"\n   \1", text)
    text = re.sub(r"\s+(\[\d+\])", r" \1\n", text)
    return text.strip()

def split_into_questions(raw_text):
    """Splits raw text strictly into main questions (Q A1..A5, Q B1..B5, Q C1..C2, Q D1..D2)."""
    cleaned_text = clean_exam_headers(raw_text)
    pattern = r"(?=(?:^|\n)\s*(?:Q\s*)?[A-D]\d+[\.\:\)]?\s+)"
    chunks = re.split(pattern, cleaned_text, flags=re.IGNORECASE)
    
    questions = []
    for chunk in chunks:
        cleaned = chunk.strip()
        if len(cleaned) > 25 and re.match(r"(?i)^(?:Q\s*)?[A-D]\d+", cleaned):
            if not re.match(r"(?i)^C\d+\s*=", cleaned):
                formatted = format_question_text(cleaned)
                questions.append(formatted)
            
    return questions

def gather_source_files(user_input):
    """Resolves user input into a list of valid file paths."""
    paths = [p.strip() for p in user_input.split(",") if p.strip()]
    files_to_process = []

    for path in paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    if f.lower().endswith(".pdf") or f.lower().endswith(".txt"):
                        files_to_process.append(os.path.join(root, f))
        elif os.path.isfile(path):
            files_to_process.append(path)

    return files_to_process

def generate_global_taxonomy(questions_list):
    """PASS 1: Analyzes sample questions to generate a dynamic taxonomy."""
    sample_text = "\n".join([f"- {q[:150]}" for q in questions_list[:10]])
    
    prompt = (
        "You are an expert academic curriculum parser. Read these sample questions from an exam paper:\n"
        f"{sample_text}\n\n"
        "Generate a dynamic list of 5 to 8 concise, high-level subject topics that represent this exam paper. "
        "Return ONLY a valid JSON object with NO markdown formatting, ticks, or text outside the JSON:\n"
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
    """Maps an individual question strictly to one of the dynamic global topics."""
    topics_str = ", ".join([f"'{t}'" for t in taxonomy_list])
    
    prompt = (
        f"Examine this exam question: '{question_text[:250]}'.\n"
        f"Classify this question strictly into ONE of the following topics: [{topics_str}]. "
        "Select the single best matching topic. "
        "Return ONLY a valid JSON object with NO markdown or extra text:\n"
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

def should_check_llm(q1_text, q2_text, threshold=0.12):
    """Calculates term overlap to skip LLM calls on completely unrelated questions."""
    words1 = set(re.findall(r'\w+', q1_text.lower()))
    words2 = set(re.findall(r'\w+', q2_text.lower()))
    if not words1 or not words2:
        return False
    
    stop_words = {"what", "is", "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "explain", "describe", "define", "show", "write"}
    w1 = words1 - stop_words
    w2 = words2 - stop_words
    
    if not w1 or not w2:
        return False
        
    intersection = w1.intersection(w2)
    union = w1.union(w2)
    overlap = len(intersection) / len(union)
    
    return overlap >= threshold

def are_questions_equivalent(q1_text, q2_text):
    """Uses local Llama 3 to check if two candidate questions mean the same thing."""
    if not should_check_llm(q1_text, q2_text):
        return False

    prompt = (
        f"Question 1: '{q1_text[:200]}'\n"
        f"Question 2: '{q2_text[:200]}'\n"
        "Do these two questions ask for the exact same core concept or answer? "
        "(e.g., 'What is Python?' and 'Define Python' are equivalent, or math problems testing the same formula).\n"
        "Return ONLY a valid JSON object with NO extra text or markdown:\n"
        '{"is_duplicate": true}'
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
            return data.get("is_duplicate", False)
    except Exception:
        return False
    return False

def run_parser(output_file="parsed_questions.json"):
    """Parses questions across multiple files/folders with live progress tracking."""
    user_input = input("\nEnter file(s) or folder path(s) to parse [comma-separated, default: sample_questions.txt]: ").strip()
    user_input = user_input if user_input else "sample_questions.txt"

    file_list = gather_source_files(user_input)
    if not file_list:
        print(f"\n[!] Error: No valid .pdf or .txt files found for '{user_input}'.")
        return

    print(f"\n[+] Found {len(file_list)} file(s) to process:")
    for f in file_list:
        print(f"    - {f}")

    all_raw_questions = []
    for filepath in file_list:
        try:
            raw_text = extract_text_from_file(filepath)
            extracted = split_into_questions(raw_text)
            all_raw_questions.extend(extracted)
        except Exception as e:
            print(f"[!] Error processing '{filepath}': {e}")

    if not all_raw_questions:
        print("\n[!] Warning: No formatted questions extracted.")
        return

    total_q = len(all_raw_questions)
    
    # PASS 1: Extract global dynamic taxonomy
    print(f"\n[...] PASS 1: Generating dynamic topic taxonomy across all input papers...")
    dynamic_taxonomy = generate_global_taxonomy(all_raw_questions)
    print(f"[+] PASS 1 Complete! Identified {len(dynamic_taxonomy)} core topics:")
    for t in dynamic_taxonomy:
        print(f"    - {t}")

    # PASS 2: Progressive Deduplication & Topic Classification
    print(f"\n[...] PASS 2: Classifying and semantically deduplicating {total_q} question(s)...")

    master_questions = []

    for idx, q_text in enumerate(all_raw_questions, 1):
        print(f" -> [{idx}/{total_q}] Processing question...", end="\r", flush=True)
        
        duplicate_found = False
        
        for master in master_questions:
            if are_questions_equivalent(q_text, master["question"]):
                master["exam_frequency"] += 1
                master["importance"] = min(5, master["exam_frequency"])
                duplicate_found = True
                break

        if not duplicate_found:
            topic = generate_ai_topic(q_text, dynamic_taxonomy)
            master_questions.append({
                "id": len(master_questions) + 1,
                "question": q_text,
                "topic": topic,
                "exam_frequency": 1,
                "importance": 1,
                "recency_score": 3
            })

    print(f"\n[+] AI processing complete! Deduplicated {total_q} raw question(s) into {len(master_questions)} unique entries.")

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(master_questions, file, indent=4)
        print(f"[+] Success! Saved database into '{output_file}'.")
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