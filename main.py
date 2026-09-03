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
    sample_text = "\n".join([f"- {q[:150]}" for q in questions_list[:12]])
    
    prompt = (
        "You are an expert academic curriculum parser. Read these sample questions from an exam paper:\n"
        f"{sample_text}\n\n"
        "Generate a dynamic list of 5 to 8 concise, high-level subject topics that represent this exam paper. "
        "Return ONLY a valid JSON object with NO markdown formatting or conversational text:\n"
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

def batch_classify_topics(questions_list, taxonomy):
    """PASS 2: Maps each question ID to a topic using clean dictionary JSON."""
    formatted_q = "\n".join([f"Q{idx + 1}: {q[:180]}" for idx, q in enumerate(questions_list)])
    topics_str = ", ".join([f"'{t}'" for t in taxonomy])

    prompt = (
        f"Available topics: [{topics_str}]\n\n"
        f"Examine these exam questions:\n{formatted_q}\n\n"
        "Classify EACH question into the single best matching topic from the available topics list.\n"
        "Return ONLY a valid JSON dictionary mapping string Question IDs to Topic Names with NO markdown:\n"
        '{"1": "Topic Name", "2": "Topic Name"}'
    )

    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw_text = response['message']['content'].strip()
        json_match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        print(f"\n[!] Warning: Batch topic classification fell back. ({e})")

    return {}

def calculate_word_overlap(q1_text, q2_text):
    """Calculates term overlap between two questions to identify duplicate concepts."""
    words1 = set(re.findall(r'\w+', q1_text.lower()))
    words2 = set(re.findall(r'\w+', q2_text.lower()))
    if not words1 or not words2:
        return 0.0
    
    stop_words = {"what", "is", "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "explain", "describe", "define", "show", "write"}
    w1 = words1 - stop_words
    w2 = words2 - stop_words
    
    if not w1 or not w2:
        return 0.0
        
    intersection = w1.intersection(w2)
    union = w1.union(w2)
    return len(intersection) / len(union)

def run_parser(output_file="parsed_questions.json"):
    """Parses questions with 2-Pass Batch AI Strategy and fast in-memory deduplication."""
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
    
    # PASS 1: Dynamic Taxonomy
    print(f"\n[...] PASS 1/2: Extracting dynamic subject taxonomy...")
    dynamic_taxonomy = generate_global_taxonomy(all_raw_questions)
    print(f"[+] PASS 1 Complete! Identified {len(dynamic_taxonomy)} core topics:")
    for t in dynamic_taxonomy:
        print(f"    - {t}")

    # PASS 2: Batch Classification
    print(f"\n[...] PASS 2/2: Mapping topics for {total_q} questions...")
    topic_map = batch_classify_topics(all_raw_questions, dynamic_taxonomy)

    # Fast In-Memory Semantic Deduplication
    master_questions = []

    for idx, q_text in enumerate(all_raw_questions, 1):
        assigned_topic = topic_map.get(str(idx), dynamic_taxonomy[0])
        
        # Check against existing master questions for high term overlap
        duplicate_found = False
        for master in master_questions:
            overlap = calculate_word_overlap(q_text, master["question"])
            if overlap >= 0.45:  # High similarity threshold for duplicate matching
                master["exam_frequency"] += 1
                master["importance"] = min(5, master["exam_frequency"])
                duplicate_found = True
                break

        if not duplicate_found:
            master_questions.append({
                "id": len(master_questions) + 1,
                "question": q_text,
                "topic": assigned_topic,
                "exam_frequency": 1,
                "importance": 1,
                "recency_score": 3
            })

    print(f"\n[+] Processing complete! Deduplicated {total_q} raw questions into {len(master_questions)} unique entries across topics.")

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