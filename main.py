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
            for page in reader.pages:
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
    """Strips common exam metadata, header blocks, and grade markers."""
    text = re.sub(r"(?i)(Name|Roll\s*No|Reg\.?\s*No|Student\s*ID|Date|Time|Duration|Max\.?\s*Marks|Total\s*Marks)\s*[:\._\-].*", "", raw_text)
    text = re.sub(r"(?i)(Class|Grade|Std)\s*[:\._\-]?\s*\d+.*", "", text)
    text = re.sub(r"(?i)Faculty of.*|Department of.*|University.*|College of.*|School of.*", "", text)
    text = re.sub(r"(?i)(Mid|End)\s*Term\s*Examination.*|Academic\s*Year.*|Semester\s*[-–—]?\s*[I|V|X|0-9]+", "", text)
    text = re.sub(r"(?i)SECTION\s*[-–—]?\s*[A-Z]", "", text)
    text = re.sub(r"(?i)S\.No\.\s*Marks\s*CO\s*Q.*", "", text)
    text = re.sub(r"(?i)Instructions?\s*[:\.-].*", "", text)
    return text

def is_valid_question(text):
    """Strict Python filter to reject administrative fields, grades, and metadata."""
    cleaned = text.strip()
    
    # Ignore short snippets
    if len(cleaned) < 25:
        return False
        
    # Block specific header and administrative patterns
    metadata_patterns = [
        r"(?i)^roll\s*no",
        r"(?i)^name\s*[:\._\-]",
        r"(?i)^student\s*id",
        r"(?i)^grade\s*\d+",
        r"(?i)^class\s*\d+",
        r"(?i)^time\s*allowed",
        r"(?i)^max\.\?\s*marks",
        r"(?i)^course\s*(code|name)",
        r"(?i)^subject\s*(code|name)",
        r"(?i)^paper\s*(code|id)",
        r"(?i)^semester",
        r"(?i)^page\s*\d+\s*of\s*\d+",
        r"(?i)^all\s*questions\s*are\s*compulsory",
        r"(?i)^attempt\s*any\s*\d+",
        r"(?i)^note\s*:"
    ]
    
    for pattern in metadata_patterns:
        if re.search(pattern, cleaned):
            return False

    # Must contain question keywords OR a question mark / substantial length
    has_question_keywords = bool(re.search(r"(?i)\b(what|why|how|explain|describe|define|calculate|derive|find|write|show|list|compare|differentiate|discuss|state|prove|solve|evaluate)\b", cleaned))
    has_question_structure = "?" in cleaned or len(cleaned.split()) >= 6
    
    return has_question_keywords or has_question_structure

def split_into_questions(raw_text):
    """Splits text on explicit question numbers while preserving text blocks."""
    cleaned_text = clean_exam_headers(raw_text)
    pattern = r"(?=(?:^|\n)\s*(?:Q\s*[A-D]?\d+|Question\s*\d+|(?:Q\.\s*\d+)|(?:\d+[\.\)]\s+[A-Z])))"
    chunks = re.split(pattern, cleaned_text, flags=re.IGNORECASE)
    
    questions = []
    for chunk in chunks:
        cleaned = chunk.strip()
        if is_valid_question(cleaned):
            questions.append(cleaned)
            
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

def calculate_text_similarity(q1, q2):
    """Instant Python word-overlap similarity (Jaccard Index)."""
    words1 = set(re.findall(r'\w+', q1.lower()))
    words2 = set(re.findall(r'\w+', q2.lower()))
    stop_words = {"what", "is", "the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "explain", "describe", "define", "show", "write"}
    
    w1 = words1 - stop_words
    w2 = words2 - stop_words
    if not w1 or not w2:
        return 0.0
        
    return len(w1.intersection(w2)) / len(w1.union(w2))

def generate_global_taxonomy(questions_list):
    """Generates subject topics dynamically with 0 temperature for 100% deterministic results."""
    sample_text = "\n".join([f"- {q[:150]}" for q in questions_list[:15]])
    
    prompt = (
        "Analyze these sample exam questions:\n"
        f"{sample_text}\n\n"
        "Identify the distinct main subject sub-topics covered in these questions. "
        "Do NOT use words like 'General', 'Overview', or 'Theory'.\n"
        "Return ONLY a JSON array of strings, e.g.: [\"Topic A\", \"Topic B\", \"Topic C\"]"
    )

    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.0}
        )

        raw_text = response['message']['content'].strip()
        json_match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        
        if json_match:
            topics = json.loads(json_match.group(0))
            if isinstance(topics, list) and len(topics) >= 2:
                return [str(t).strip() for t in topics]
    except Exception as e:
        print(f"\n[!] Taxonomy extraction warning: {e}")
        
    return ["Database Concepts", "SQL Queries", "System Architecture", "Algorithms"]

def classify_single_question(question_text, taxonomy_list):
    """Classifies a single question into taxonomy with 0 temperature."""
    topics_str = ", ".join([f'"{t}"' for t in taxonomy_list])
    
    prompt = (
        f"Question: \"{question_text[:250]}\"\n"
        f"Allowed Categories: [{topics_str}]\n\n"
        "Which single category best fits this question? "
        "Return ONLY JSON: {\"topic\": \"Exact Category Name\"}"
    )

    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0.0}
        )

        raw_text = response['message']['content'].strip()
        json_match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(0))
            predicted = data.get("topic", "").strip()
            
            for topic in taxonomy_list:
                if topic.lower() in predicted.lower() or predicted.lower() in topic.lower():
                    return topic
    except Exception:
        pass
        
    return taxonomy_list[len(question_text) % len(taxonomy_list)]

def run_parser(input_path=None, output_file="parsed_questions.json"):
    """Fast execution parser with strict metadata stripping and dynamic topic tagging."""
    if input_path is None:
        user_input = input("\nEnter file(s) or folder path(s) to parse: ").strip()
    else:
        user_input = input_path

    file_list = gather_source_files(user_input)
    if not file_list:
        print(f"\n[!] Error: No valid files found.")
        return

    print(f"\n[+] Processing {len(file_list)} file(s)...")

    master_questions = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                master_questions = json.load(f)
        except Exception:
            master_questions = []

    # Step 1: Text extraction & question validation
    batch_extracted = []
    for filepath in file_list:
        try:
            raw_text = extract_text_from_file(filepath)
            questions = split_into_questions(raw_text)
            fname = os.path.basename(filepath)
            for q in questions:
                batch_extracted.append({"question": q, "source_file": fname})
        except Exception as e:
            print(f"[!] Error reading '{filepath}': {e}")

    if not batch_extracted:
        print("\n[!] No valid questions extracted.")
        return

    # Step 2: Global taxonomy generation
    all_q_texts = [item["question"] for item in batch_extracted]
    print(f"\n[...] Extracting dynamic subject topics...")
    dynamic_taxonomy = generate_global_taxonomy(all_q_texts)
    print(f"[+] Active Topics: {dynamic_taxonomy}")

    # Step 3: Fast processing with deduplication and targeted classification
    total_q = len(batch_extracted)
    print(f"\n[...] Processing {total_q} valid questions...")

    for idx, item in enumerate(batch_extracted, 1):
        q_text = item["question"]
        source_file = item["source_file"]
        
        # Check against existing entries using fast Jaccard similarity
        matched_master = None
        for master in master_questions:
            if calculate_text_similarity(q_text, master["question"]) >= 0.60:
                matched_master = master
                break

        if matched_master:
            matched_master["exam_frequency"] += 1
            matched_master["importance"] = min(5, matched_master["exam_frequency"])
            print(f" [{idx}/{total_q}] Duplicate detected -> Updated Frequency ({matched_master['exam_frequency']})")
        else:
            topic = classify_single_question(q_text, dynamic_taxonomy)
            master_questions.append({
                "id": len(master_questions) + 1,
                "question": q_text,
                "topic": topic,
                "exam_frequency": 1,
                "importance": 1,
                "recency_score": 3,
                "source_file": source_file
            })
            print(f" [{idx}/{total_q}] Tagged -> [{topic}]")

    print(f"\n[+] Processing complete! Saved {len(master_questions)} valid questions to {output_file}.")

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(master_questions, file, indent=4)
    except IOError as e:
        print(f"\n[!] Save error: {e}")

if __name__ == "__main__":
    run_parser()