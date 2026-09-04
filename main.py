import os
import re
import json
import ollama
from pypdf import PdfReader

def extract_text_from_file(filepath):
    """Reads raw text from .txt or .pdf files."""
    print(f"\n[...] Reading file: {filepath}")
    text = ""
    if filepath.lower().endswith(".pdf"):
        try:
            reader = PdfReader(filepath)
            for idx, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            print(f"[+] Extracted {len(text)} characters from PDF.")
        except Exception as e:
            print(f"[!] Error reading PDF '{filepath}': {e}")
    else:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
            text = file.read()
            print(f"[+] Extracted {len(text)} characters from TXT.")
            
    return text

def clean_exam_headers(raw_text):
    """Strips common exam metadata and header noise."""
    text = re.sub(r"(?i)Faculty of Engineering.*?(?=\b(?:Q|Question|\d+)\b)", "", raw_text, flags=re.DOTALL)
    text = re.sub(r"(?i)SECTION\s*[-–—]?\s*[A-Z]", "", text)
    text = re.sub(r"(?i)S\.No\.\s*Marks\s*CO\s*Q", "", text)
    return text

def split_into_questions(raw_text):
    """
    Splits text flexibly into questions.
    Supports formats: Q1, Q A1, Question 1, 1., 1)
    """
    cleaned_text = clean_exam_headers(raw_text)
    pattern = r"(?=(?:^|\n)\s*(?:Q\s*[A-D]?\d+|Question\s*\d+|\d+[\.\)]))"
    chunks = re.split(pattern, cleaned_text, flags=re.IGNORECASE)
    
    questions = []
    for chunk in chunks:
        cleaned = chunk.strip()
        if len(cleaned) > 15:
            questions.append(cleaned)
            
    print(f"[+] Identified {len(questions)} candidate question block(s).")
    return questions

def gather_source_files(user_input):
    """Resolves user input into a list of valid file paths."""
    if isinstance(user_input, list):
        paths = user_input
    else:
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

def run_parser(input_path=None, output_file="parsed_questions.json"):
    """Parses questions across multiple files and appends/deduplicates into master database."""
    if input_path is None:
        user_input = input("\nEnter file(s) or folder path(s) to parse [comma-separated, default: sample_questions.txt]: ").strip()
        user_input = user_input if user_input else "sample_questions.txt"
    else:
        user_input = input_path

    file_list = gather_source_files(user_input)
    if not file_list:
        print(f"\n[!] Error: No valid .pdf or .txt files found for '{user_input}'.")
        return

    print(f"\n[+] Processing {len(file_list)} file(s)...")

    # Load existing questions if file exists
    master_questions = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                master_questions = json.load(f)
            print(f"[+] Loaded {len(master_questions)} existing question(s) from database.")
        except Exception:
            master_questions = []

    for filepath in file_list:
        try:
            raw_text = extract_text_from_file(filepath)
            extracted = split_into_questions(raw_text)
            if not extracted:
                continue

            source_filename = os.path.basename(filepath)
            
            # PASS 1: Extract global dynamic taxonomy per paper context
            print(f"\n[...] PASS 1: Generating dynamic topic taxonomy for '{source_filename}'...")
            dynamic_taxonomy = generate_global_taxonomy(extracted)
            print(f"[+] Topics identified: {dynamic_taxonomy}")

            # PASS 2: Progressive Deduplication against master database
            total_q = len(extracted)
            print(f"\n[...] PASS 2: Classifying and deduplicating {total_q} question(s) from '{source_filename}'...")

            for idx, q_text in enumerate(extracted, 1):
                print(f" -> [{idx}/{total_q}] Processing...", end="\r", flush=True)
                
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
                        "recency_score": 3,
                        "source_file": source_filename
                    })
        except Exception as e:
            print(f"[!] Error processing '{filepath}': {e}")

    print(f"\n[+] AI processing complete! Database now holds {len(master_questions)} unique entries.")

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(master_questions, file, indent=4)
        print(f"[+] Saved updated database to '{output_file}'.")
    except IOError as e:
        print(f"\n[!] Error saving JSON file: {e}")

if __name__ == "__main__":
    run_parser()