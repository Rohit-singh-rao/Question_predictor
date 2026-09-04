import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file

# ReportLab imports for advanced PDF styling
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from main import run_parser

app = Flask(__name__)
app.secret_key = "super_secret_key_for_flash"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def load_data(filename="parsed_questions.json"):
    """Loads parsed question database safely."""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(data, filename="parsed_questions.json"):
    """Saves updated question list back to JSON."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

# PAGE 1: Upload & Ingestion
@app.route("/")
def upload_page():
    questions = load_data()
    has_data = len(questions) > 0
    
    # Extract list of unique source files tracked in parsed_questions.json
    uploaded_file_list = sorted(list(set(q.get("source_file", "Uploaded Paper") for q in questions if "source_file" in q)))
    
    return render_template(
        "upload.html", 
        has_data=has_data, 
        question_count=len(questions),
        uploaded_file_list=uploaded_file_list
    )

@app.route("/upload", methods=["POST"])
def upload_file():
    uploaded_files = request.files.getlist("file")
    
    if not uploaded_files or uploaded_files[0].filename == "":
        flash("No files selected", "danger")
        return redirect(url_for("upload_page"))

    saved_filepaths = []
    for file in uploaded_files:
        if file and file.filename != "":
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)
            saved_filepaths.append(filepath)

    if saved_filepaths:
        try:
            # Pass list of saved file paths into parser
            run_parser(input_path=saved_filepaths, output_file="parsed_questions.json")
            flash(f"Successfully processed {len(saved_filepaths)} file(s) and updated database!", "success")
            return redirect(url_for("dashboard_page"))
        except Exception as e:
            flash(f"Error parsing files: {e}", "danger")
            return redirect(url_for("upload_page"))
        finally:
            # Always clean up temporary files
            for fp in saved_filepaths:
                if os.path.exists(fp):
                    os.remove(fp)

    return redirect(url_for("upload_page"))

# Remove questions linked to a single specific source file
@app.route("/remove_file", methods=["POST"])
def remove_specific_file():
    target_file = request.form.get("filename")
    if not target_file:
        flash("No target file specified.", "warning")
        return redirect(url_for("upload_page"))

    questions = load_data()
    updated_questions = [q for q in questions if q.get("source_file") != target_file]

    if len(questions) == len(updated_questions):
        flash(f"No entries found matching file: {target_file}", "warning")
    else:
        save_data(updated_questions)
        flash(f"Successfully removed '{target_file}' from database!", "success")

    return redirect(url_for("upload_page"))

# PAGE 2: Action Dashboard (Guarded: requires parsed data)
@app.route("/dashboard")
def dashboard_page():
    questions = load_data()
    if not questions:
        flash("Please upload and parse an exam paper first before accessing the dashboard.", "warning")
        return redirect(url_for("upload_page"))

    total_unique = len(questions)
    total_occurrences = sum(q.get("exam_frequency", 1) for q in questions)

    topic_summary_dict = {}
    for q in questions:
        topic = q.get("topic", "General")
        freq = q.get("exam_frequency", 1)
        q_text = q.get("question", "")

        if topic not in topic_summary_dict:
            topic_summary_dict[topic] = {"occurrences": 0, "questions": []}

        topic_summary_dict[topic]["occurrences"] += freq
        topic_summary_dict[topic]["questions"].append(q_text)

    topic_summary = []
    for topic, data in sorted(topic_summary_dict.items(), key=lambda x: x[1]["occurrences"], reverse=True):
        weightage = round((data["occurrences"] / total_occurrences * 100), 1) if total_occurrences > 0 else 0
        topic_summary.append({
            "topic": topic,
            "occurrences": data["occurrences"],
            "weightage": weightage,
            "questions": data["questions"]
        })

    return render_template(
        "dashboard.html",
        total_unique=total_unique,
        total_occurrences=total_occurrences,
        topic_summary=topic_summary
    )

# PAGE 3: Export Styled PDF Report
@app.route("/export/pdf")
def export_pdf():
    questions = load_data()
    if not questions:
        flash("No data available to generate report.", "warning")
        return redirect(url_for("upload_page"))

    pdf_path = "prediction_report.pdf"
    
    # Page setup
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Color definitions
    PRIMARY_COLOR = colors.HexColor("#1e293b")
    ACCENT_COLOR = colors.HexColor("#2563eb")
    TEXT_MUTED = colors.HexColor("#64748b")
    BG_LIGHT = colors.HexColor("#f8fafc")

    # Typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=PRIMARY_COLOR
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=TEXT_MUTED
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.white
    )

    question_style = ParagraphStyle(
        "QuestionText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=PRIMARY_COLOR
    )

    # 1. Header Banner
    story.append(Paragraph("🎓 Exam Question Prediction & Weightage Report", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')} | Question Analysis Pipeline", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_COLOR, spaceAfter=15))

    # 2. Metric Overview Table
    total_unique = len(questions)
    total_occurrences = sum(q.get("exam_frequency", 1) for q in questions)

    summary_data = [
        [
            Paragraph("<b>Total Unique Questions</b>", table_body_style),
            Paragraph("<b>Total Exam Occurrences</b>", table_body_style)
        ],
        [
            Paragraph(f"<font size=14 color='#2563eb'><b>{total_unique}</b></font>", table_body_style),
            Paragraph(f"<font size=14 color='#059669'><b>{total_occurrences}</b></font>", table_body_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[270, 270])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Data aggregation
    topic_dict = {}
    for q in questions:
        topic = q.get("topic", "General")
        freq = q.get("exam_frequency", 1)
        q_text = q.get("question", "")

        if topic not in topic_dict:
            topic_dict[topic] = {"occurrences": 0, "questions": []}

        topic_dict[topic]["occurrences"] += freq
        topic_dict[topic]["questions"].append({"text": q_text, "freq": freq})

    # 3. Topic Weightage Overview Table
    story.append(Paragraph("<b>📊 Topic Weightage Summary</b>", ParagraphStyle('Sub', parent=title_style, fontSize=13, leading=16)))
    story.append(Spacer(1, 8))

    overview_rows = [[
        Paragraph("Topic Name", table_header_style),
        Paragraph("Occurrences", table_header_style),
        Paragraph("Exam Weightage", table_header_style)
    ]]

    for topic, data in sorted(topic_dict.items(), key=lambda x: x[1]["occurrences"], reverse=True):
        weightage = round((data["occurrences"] / total_occurrences * 100), 1) if total_occurrences > 0 else 0
        overview_rows.append([
            Paragraph(topic, table_body_style),
            Paragraph(str(data["occurrences"]), table_body_style),
            Paragraph(f"{weightage}%", table_body_style)
        ])

    overview_table = Table(overview_rows, colWidths=[280, 130, 130])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 20))

    # 4. Detailed Question Bank per Topic
    story.append(Paragraph("<b>📚 Detailed Question Bank</b>", ParagraphStyle('Sub2', parent=title_style, fontSize=13, leading=16)))
    story.append(Spacer(1, 10))

    for topic, data in sorted(topic_dict.items(), key=lambda x: x[1]["occurrences"], reverse=True):
        # Section Header Banner
        banner_data = [[
            Paragraph(f"<b>{topic.upper()}</b>", section_header_style),
            Paragraph(f"Total Questions: {data['occurrences']}", ParagraphStyle('RightText', parent=section_header_style, alignment=2))
        ]]
        banner_table = Table(banner_data, colWidths=[380, 160])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ACCENT_COLOR),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 4))

        # Topic Questions Table
        q_rows = [[
            Paragraph("#", table_header_style),
            Paragraph("Question Details", table_header_style),
            Paragraph("Frequency", table_header_style)
        ]]

        for idx, q_info in enumerate(data["questions"], 1):
            q_rows.append([
                Paragraph(str(idx), table_body_style),
                Paragraph(q_info["text"], question_style),
                Paragraph(f"{q_info['freq']}x", table_body_style)
            ])

        q_table = Table(q_rows, colWidths=[30, 430, 80])
        q_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('ALIGN', (2,0), (2,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))

        story.append(q_table)
        story.append(Spacer(1, 15))

    doc.build(story)
    return send_file(pdf_path, as_attachment=True)

# Route to clear database and reset app state
@app.route("/reset", methods=["POST"])
def reset_data():
    json_path = "parsed_questions.json"
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
            flash("Database successfully cleared! You can now upload new papers.", "info")
        except Exception as e:
            flash(f"Error resetting database: {e}", "danger")
    else:
        flash("Database is already empty.", "warning")
        
    return redirect(url_for("upload_page"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)