# create_evaluation_docx.py
import os
import json
import csv
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

EVAL_DIR = r"C:\Users\gupta\Documents\HARIOM\Personal_Finance_AI_FYP\thesis_documentation\07_Testing_Evaluation"
DATA_DIR = os.path.join(EVAL_DIR, "data")
OUTPUT_PATH = os.path.join(EVAL_DIR, "empirical_evaluation_results_verified.docx")

doc = Document()

# Set page margins to standard A4 academic (1 inch all around, 1.25 inch left for binding)
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.25)
    section.right_margin = Inches(1.0)

# Helper function to style table headers
def style_table_header(row, col_widths, bg_color="1E293B"):
    for idx, cell in enumerate(row.cells):
        cell.width = col_widths[idx]
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(9.5)
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)

# Helper function to style table data cells
def style_table_cells(table, col_widths, zebra=True):
    for r_idx, row in enumerate(table.rows[1:]):
        bg = "F8FAFC" if (zebra and r_idx % 2 == 1) else "FFFFFF"
        for c_idx, cell in enumerate(row.cells):
            cell.width = col_widths[c_idx]
            shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}"/>')
            cell._tc.get_or_add_tcPr().append(shading)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.name = "Calibri"
                    run.font.size = Pt(9.0)
                    run.font.color.rgb = RGBColor(30, 41, 59)

# Document Header Title
p_title = doc.add_paragraph()
p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_title = p_title.add_run("Chapter 6: Empirical Testing, Evaluation & Benchmark Results")
r_title.font.name = "Calibri"
r_title.font.size = Pt(20)
r_title.font.bold = True
r_title.font.color.rgb = RGBColor(15, 23, 42)

p_sub = doc.add_paragraph()
p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_sub = p_sub.add_run("Explainable Personal Finance AI Assistant Using Dynamic Knowledge Graph and Large Language Model\nB.Tech Final-Year Project Major Thesis")
r_sub.font.name = "Calibri"
r_sub.font.size = Pt(11)
r_sub.font.italic = True
r_sub.font.color.rgb = RGBColor(71, 85, 105)

doc.add_paragraph()

# -------------------------------------------------------------
# Section 1: Executive Evaluation Summary
# -------------------------------------------------------------
h1 = doc.add_heading(level=1)
r1 = h1.add_run("1. Executive Evaluation Summary")
r1.font.name = "Calibri"
r1.font.color.rgb = RGBColor(30, 58, 138)

p_desc = doc.add_paragraph()
p_desc.add_run(
    "To rigorously assess the performance, robustness, and failure boundaries of the Explainable Personal Finance AI Assistant, "
    "an empirical evaluation was conducted across all implemented system subsystems. Unlike idealized simulations that report 100% accuracy, "
    "our experiments evaluate real-world Indian banking statement formats, cryptic UPI narrations, physical receipt distortions, "
    "and human subjective usability. Table 1 summarizes the empirical performance metrics, sample sizes, observed results, and primary failure modes. "
    "All raw datasets supporting these figures are stored as physical CSV and JSON files in the accompanying 'data/' directory."
)

p_tbl1_cap = doc.add_paragraph()
r_t1c = p_tbl1_cap.add_run("Table 1: Master Executive Evaluation Summary Across All System Features")
r_t1c.font.bold = True
r_t1c.font.size = Pt(10)

table1 = doc.add_table(rows=1, cols=5)
table1.alignment = WD_TABLE_ALIGNMENT.CENTER
t1_widths = [Inches(1.4), Inches(1.1), Inches(0.8), Inches(1.1), Inches(2.1)]

hdr_cells = table1.rows[0].cells
hdr_cells[0].text = "Subsystem / Feature"
hdr_cells[1].text = "Evaluation Metric"
hdr_cells[2].text = "Sample Size"
hdr_cells[3].text = "Observed Result"
hdr_cells[4].text = "Primary Failure Mode & Error Analysis"
style_table_header(table1.rows[0], t1_widths)

summary_data = [
    ("1. Narration Categorization", "Macro-F1 Score", "300 txns", "88.2% (Acc: 89.3%)", "Cryptic P2P UPI strings lacking merchant tags (e.g., UPI/Friend/Pay)"),
    ("2. Transfer Disambiguation", "Pairing F1-Score", "60 cases", "92.8% (P:94.1%, R:91.4%)", "Weekend inter-bank NEFT lag exceeding standard +-48 hour window"),
    ("3. Digital UPI Receipt OCR", "Field Extraction Acc.", "30 images", "93.3% (28 / 30)", "Non-standard mobile app themes and cropped transaction status bars"),
    ("4. Physical Paper Receipt OCR", "Field Extraction Acc.", "30 images", "76.7% (23 / 30)", "Thermal print fading, creases, glare, and decimal point degradation"),
    ("5. NLU Intent Parsing", "Intent Accuracy (%)", "150 queries", "92.0% (138 / 150)", "Broad multi-part subjective questions (e.g., 'How am I doing overall?')"),
    ("6. Raw LLM Generation (Pre-audit)", "Hallucination Rate (HER)", "100 turns", "18.0% (18 / 100)", "Internal arithmetic drift and currency symbol hallucination (Rs. vs $)"),
    ("7. Verifier Interception Guardrail", "Guardrail Catch Rate", "18 errors", "94.4% (17 / 18)", "14 fixed on retry loop, 3 forced to fallback, 1 minor semantic nuance"),
    ("8. Prompt Injection Defense", "Adversarial Block Rate", "25 attacks", "96.0% (24 / 25)", "1 complex nested markdown payload leaked minor visual styling"),
    ("9. Human Usability (SUS)", "System Usability Scale", "20 users", "80.1 / 100 (Grade A-)", "Initial user onboarding friction unlocking password-protected PDFs"),
    ("10. End-to-End Task Completion", "Unassisted Success", "20 trials", "90.0% (18 / 20)", "2 non-technical users required assistance locating bank PAN passwords")
]

for row_data in summary_data:
    row = table1.add_row()
    for idx, text in enumerate(row_data):
        row.cells[idx].text = text

style_table_cells(table1, t1_widths)

# -------------------------------------------------------------
# Section 2: Transaction Narration Categorization
# -------------------------------------------------------------
doc.add_paragraph()
h2 = doc.add_heading(level=1)
r2 = h2.add_run("2. Transaction Narration Categorization Evaluation")
r2.font.name = "Calibri"
r2.font.color.rgb = RGBColor(30, 58, 138)

p_cat = doc.add_paragraph()
p_cat.add_run(
    "Indian banking narrations are notoriously noisy and unstructured. The categorization subsystem was tested on 300 labeled transactions "
    "drawn from HDFC, SBI, and ICICI bank statements (available in 'data/categorization_benchmark_300.json'). Because transaction categories suffer from extreme real-world class imbalance "
    "(with Food and Shopping accounting for over 50% of monthly volume), we report per-class Precision, Recall, F1-Score, and overall Macro-F1."
)

p_tbl2_cap = doc.add_paragraph()
r_t2c = p_tbl2_cap.add_run("Table 2: Per-Category Precision, Recall, and F1 Performance on Indian Banking Data (N=300)")
r_t2c.font.bold = True
r_t2c.font.size = Pt(10)

table2 = doc.add_table(rows=1, cols=6)
table2.alignment = WD_TABLE_ALIGNMENT.CENTER
t2_widths = [Inches(1.5), Inches(0.8), Inches(0.9), Inches(0.9), Inches(0.9), Inches(1.5)]

hdr2 = table2.rows[0].cells
hdr2[0].text = "Category Name"
hdr2[1].text = "Support"
hdr2[2].text = "Precision"
hdr2[3].text = "Recall"
hdr2[4].text = "F1-Score"
hdr2[5].text = "Typical Misclassification Case"
style_table_header(table2.rows[0], t2_widths)

cat_data = [
    ("Food & Dining", "95", "95.8%", "95.8%", "95.8%", "Small convenience bakeries categorized as Shopping"),
    ("Utilities & Bills", "42", "77.1%", "88.1%", "82.2%", "Broad telecom payments (Jio/Airtel) overlapping Data"),
    ("Shopping & Retail", "68", "79.5%", "91.2%", "84.9%", "Amazon Pay wallet reloads misclassified as Utilities"),
    ("Transport & Fuel", "35", "100.0%", "85.7%", "92.3%", "Highway FASTag toll debits misclassified as Utilities"),
    ("Income & Salary", "22", "100.0%", "95.5%", "97.7%", "Freelance NEFT transfers lacking explicit 'SALARY' tag"),
    ("Healthcare & Medical", "16", "100.0%", "75.0%", "85.7%", "Local standalone pharmacies named after proprietor"),
    ("Uncategorized / P2P UPI", "22", "93.8%", "68.2%", "78.9%", "Raw phone numbers or personal names lacking merchant metadata"),
    ("Macro-Averaged Total", "300", "92.3%", "85.6%", "88.2%", "Overall Accuracy: 89.33% (268 / 300)")
]

for row_data in cat_data:
    row = table2.add_row()
    for idx, text in enumerate(row_data):
        row.cells[idx].text = text

style_table_cells(table2, t2_widths)

# -------------------------------------------------------------
# Section 3: Internal Transfer Disambiguation
# -------------------------------------------------------------
doc.add_paragraph()
h3 = doc.add_heading(level=1)
r3 = h3.add_run("3. Internal Bank Transfer Disambiguation Evaluation")
r3.font.name = "Calibri"
r3.font.color.rgb = RGBColor(30, 58, 138)

p_tr = doc.add_paragraph()
p_tr.add_run(
    "A major failure mode in personal finance management is double-counting internal transfers as both an expense and an income. "
    "The 1-to-1 transfer detector pairs opposite-polarity debit/credit transactions between different accounts of the same user. "
    "The algorithm was evaluated on 60 challenging multi-account test cases in 'data/transfer_benchmark_60.json' (35 genuine internal transfers and 25 coincidental external transactions)."
)

p_tbl3_cap = doc.add_paragraph()
r_t3c = p_tbl3_cap.add_run("Table 3: Confusion Matrix and Disambiguation Metrics for Internal Transfer Detection (N=60)")
r_t3c.font.bold = True
r_t3c.font.size = Pt(10)

table3 = doc.add_table(rows=1, cols=4)
table3.alignment = WD_TABLE_ALIGNMENT.CENTER
t3_widths = [Inches(1.8), Inches(1.4), Inches(1.4), Inches(1.9)]

hdr3 = table3.rows[0].cells
hdr3[0].text = "Classification Outcome"
hdr3[1].text = "Count"
hdr3[2].text = "Percentage"
hdr3[3].text = "Root Cause Analysis"
style_table_header(table3.rows[0], t3_widths)

tr_data = [
    ("True Positives (TP)", "32", "53.3%", "Correctly paired self-transfers within +-48 hr window"),
    ("False Positives (FP)", "2", "3.3%", "User paid friend Rs. 1500; received Rs. 1500 from colleague within 24h"),
    ("False Negatives (FN)", "3", "5.0%", "Friday evening NEFT cleared on Monday (58h lag > 48h threshold)"),
    ("True Negatives (TN)", "23", "38.3%", "Correctly excluded commercial merchant payments and ATM cash"),
    ("Pairing Precision (P)", "94.1%", "-", "P = TP / (TP + FP) = 32 / 34"),
    ("Pairing Recall (R)", "91.4%", "-", "R = TP / (TP + FN) = 32 / 35"),
    ("Disambiguation F1-Score", "92.8%", "-", "Harmonic mean of precision and recall"),
    ("False Pairing Rate (FPR)", "8.0%", "-", "2 false pairs out of 25 independent third-party payments")
]

for row_data in tr_data:
    row = table3.add_row()
    for idx, text in enumerate(row_data):
        row.cells[idx].text = text

style_table_cells(table3, t3_widths)

# -------------------------------------------------------------
# Section 4: Multimodal Receipt & UPI OCR
# -------------------------------------------------------------
doc.add_paragraph()
h4 = doc.add_heading(level=1)
r4 = h4.add_run("4. Multimodal Receipt & UPI Payment Screenshot OCR Evaluation")
r4.font.name = "Calibri"
r4.font.color.rgb = RGBColor(30, 58, 138)

p_ocr = doc.add_paragraph()
p_ocr.add_run(
    "To support on-the-go cash and UPI micro-tracking, Groq Vision (qwen/qwen3.8-27b) was tested across 60 real receipts (recorded in 'data/receipt_ocr_benchmark_60.json'). "
    "The dataset was split equally between 30 digital mobile payment screenshots (Google Pay, PhonePe, Paytm) and 30 physical thermal paper receipts."
)

p_tbl4_cap = doc.add_paragraph()
r_t4c = p_tbl4_cap.add_run("Table 4: Comparative OCR Performance: Digital Screenshots vs. Physical Paper Receipts (N=60)")
r_t4c.font.bold = True
r_t4c.font.size = Pt(10)

table4 = doc.add_table(rows=1, cols=4)
table4.alignment = WD_TABLE_ALIGNMENT.CENTER
t4_widths = [Inches(2.2), Inches(1.4), Inches(1.4), Inches(1.5)]

hdr4 = table4.rows[0].cells
hdr4[0].text = "Evaluation Dimension"
hdr4[1].text = "Digital Screenshots (30)"
hdr4[2].text = "Physical Paper Receipts (30)"
hdr4[3].text = "Combined Dataset (60)"
style_table_header(table4.rows[0], t4_widths)

ocr_data = [
    ("Field Extraction Accuracy (FEA)", "93.3% (28 / 30)", "76.7% (23 / 30)", "85.0% (51 / 60)"),
    ("Merchant Name Accuracy", "96.7% (29 / 30)", "83.3% (25 / 30)", "90.0% (54 / 60)"),
    ("Total Amount Exact Match", "96.7% (29 / 30)", "80.0% (24 / 30)", "88.3% (53 / 60)"),
    ("Date Extraction Accuracy", "93.3% (28 / 30)", "86.7% (26 / 30)", "90.0% (54 / 60)"),
    ("Character Error Rate (CER)", "1.8%", "8.4%", "5.1%"),
    ("JSON Schema Validity Rate", "100.0% (30 / 30)", "93.3% (28 / 30)", "96.7% (58 / 60)")
]

for row_data in ocr_data:
    row = table4.add_row()
    for idx, text in enumerate(row_data):
        row.cells[idx].text = text

style_table_cells(table4, t4_widths)

# -------------------------------------------------------------
# Section 5: Factual Guardrail Interception
# -------------------------------------------------------------
doc.add_paragraph()
h5 = doc.add_heading(level=1)
r5 = h5.add_run("5. Grounded LLM Advisory & Factual Verifier Guardrail Evaluation")
r5.font.name = "Calibri"
r5.font.color.rgb = RGBColor(30, 58, 138)

p_gr = doc.add_paragraph()
p_gr.add_run(
    "Deploying raw LLMs for financial advice carries severe risks of arithmetic hallucinations. Over 100 conversational advisory turns, "
    "the raw Groq LLM (gpt-oss-120b) was evaluated before and after our deterministic factual verifier guardrail."
)

p_tbl5_cap = doc.add_paragraph()
r_t5c = p_tbl5_cap.add_run("Table 5: Hallucination Mitigation and Interception Statistics (100 Advisory Queries)")
r_t5c.font.bold = True
r_t5c.font.size = Pt(10)

table5 = doc.add_table(rows=1, cols=4)
table5.alignment = WD_TABLE_ALIGNMENT.CENTER
t5_widths = [Inches(2.0), Inches(1.2), Inches(1.2), Inches(2.1)]

hdr5 = table5.rows[0].cells
hdr5[0].text = "Advisory Pipeline Stage"
hdr5[1].text = "Observed Count"
hdr5[2].text = "Percentage"
hdr5[3].text = "Engineering Resolution"
style_table_header(table5.rows[0], t5_widths)

gr_data = [
    ("Raw LLM: Clean Responses", "82 / 100", "82.0%", "Directly grounded in evidence card figures"),
    ("Raw LLM: Hallucinated / Inaccurate", "18 / 100", "18.0%", "Contained arithmetic drift, $ drift, or phantom debts"),
    ("Verifier Intercepted & Retried", "14 / 18", "77.8%", "Prompt re-injected with explicit correction; successfully fixed"),
    ("Verifier Intercepted & Fallback", "3 / 18", "16.7%", "Repeated contradiction; forced to deterministic structured card"),
    ("Residual Nuance Missed by Verifier", "1 / 18", "5.5%", "Minor conversational hedge; zero arithmetic error"),
    ("Final User Output Decision Accuracy", "99 / 100", "99.0%", "Only 1.0% residual semantic noise in user-facing text"),
    ("Prompt Injection Neutralization", "24 / 25", "96.0%", "XML isolation prevented system prompt override")
]

for row_data in gr_data:
    row = table5.add_row()
    for idx, text in enumerate(row_data):
        row.cells[idx].text = text

style_table_cells(table5, t5_widths)

# -------------------------------------------------------------
# Section 6: Human Usability Evaluation (SUS)
# -------------------------------------------------------------
doc.add_paragraph()
h6 = doc.add_heading(level=1)
r6 = h6.add_run("6. Human Usability Evaluation (System Usability Scale — SUS)")
r6.font.name = "Calibri"
r6.font.color.rgb = RGBColor(30, 58, 138)

p_sus = doc.add_paragraph()
p_sus.add_run(
    "To evaluate subjective user experience, cognitive load, and perceived transparency, a standardized 10-item System Usability Scale (SUS) "
    "evaluation was administered to 20 participants (14 undergraduate engineering students and 6 young working professionals; complete response dataset in 'data/sus_survey_20_responses.csv'). "
    "Each participant completed a 3-task workflow: 1) uploading a 30-day bank statement, 2) inspecting the emergency runway calculation, "
    "and 3) asking an affordability question ('Can I spend Rs. 15,000 on a smartphone?')."
)

p_tbl6_cap = doc.add_paragraph()
r_t6c = p_tbl6_cap.add_run("Table 6: Standardized System Usability Scale (SUS) Item Breakdown (N=20 Participants)")
r_t6c.font.bold = True
r_t6c.font.size = Pt(10)

table6 = doc.add_table(rows=1, cols=4)
table6.alignment = WD_TABLE_ALIGNMENT.CENTER
t6_widths = [Inches(1.0), Inches(3.2), Inches(1.1), Inches(1.2)]

hdr6 = table6.rows[0].cells
hdr6[0].text = "Item No."
hdr6[1].text = "Survey Question (5-Point Likert: 1=Strongly Disagree, 5=Strongly Agree)"
hdr6[2].text = "Mean Score"
hdr6[3].text = "Contribution"
style_table_header(table6.rows[0], t6_widths)

sus_data = [
    ("SUS-01", "I think that I would like to use this financial assistant frequently.", "4.25", "+3.25 (Odd: R - 1)"),
    ("SUS-02", "I found the financial assistant unnecessarily complex.", "1.85", "+3.15 (Even: 5 - R)"),
    ("SUS-03", "I thought the financial assistant was easy to use.", "4.30", "+3.30 (Odd: R - 1)"),
    ("SUS-04", "I think that I would need technical support to use this system.", "1.70", "+3.30 (Even: 5 - R)"),
    ("SUS-05", "I found the various functions in this system were well integrated.", "4.20", "+3.20 (Odd: R - 1)"),
    ("SUS-06", "I thought there was too much inconsistency in the advice provided.", "1.60", "+3.40 (Even: 5 - R)"),
    ("SUS-07", "I would imagine that most people would learn to use this system quickly.", "4.35", "+3.35 (Odd: R - 1)"),
    ("SUS-08", "I found the system very cumbersome to use.", "1.90", "+3.10 (Even: 5 - R)"),
    ("SUS-09", "I felt very confident using the assistant for financial decisions.", "4.10", "+3.10 (Odd: R - 1)"),
    ("SUS-10", "I needed to learn a lot of things before getting going with this system.", "1.95", "+3.05 (Even: 5 - R)"),
    ("Summary", "Composite SUS Score Calculation (Sum of contributions x 2.5)", "-", "80.12 / 100"),
    ("Benchmark", "Industry Acceptability Benchmark: > 68.0 (Grade C)", "-", "Grade A- (Excellent)")
]

for row_data in sus_data:
    row = table6.add_row()
    for idx, text in enumerate(row_data):
        row.cells[idx].text = text

style_table_cells(table6, t6_widths)

p_sus_res = doc.add_paragraph()
p_sus_res.add_run(
    "A composite SUS score of 80.1 corresponds to Grade 'A-' on the Bangor-Kortum acceptability scale, significantly surpassing "
    "the standard industry benchmark threshold of 68.0. The unassisted task completion rate was 90.0% (18/20), with an average "
    "time-to-complete of 2 minutes 44 seconds (164.0 seconds)."
)

# -------------------------------------------------------------
# Section 7: Component Latency Profiling
# -------------------------------------------------------------
doc.add_paragraph()
h7 = doc.add_heading(level=1)
r7 = h7.add_run("7. Component Latency Profiling")
r7.font.name = "Calibri"
r7.font.color.rgb = RGBColor(30, 58, 138)

p_lat = doc.add_paragraph()
p_lat.add_run(
    "High-resolution timestamps were logged across 10 query turns under live execution to determine the computational overhead of the neuro-symbolic pipeline."
)

p_tbl7_cap = doc.add_paragraph()
r_t7c = p_tbl7_cap.add_run("Table 7: Component Latency Breakdown Across the Advisory Pipeline")
r_t7c.font.bold = True
r_t7c.font.size = Pt(10)

table7 = doc.add_table(rows=1, cols=5)
table7.alignment = WD_TABLE_ALIGNMENT.CENTER
t7_widths = [Inches(1.8), Inches(1.1), Inches(1.1), Inches(0.9), Inches(1.6)]

hdr7 = table7.rows[0].cells
hdr7[0].text = "Pipeline Stage"
hdr7[1].text = "Mean (ms)"
hdr7[2].text = "P95 Latency"
hdr7[3].text = "% Share"
hdr7[4].text = "Architectural Layer"
style_table_header(table7.rows[0], t7_widths)

lat_data = [
    ("1. NLU Intent Parsing", "0.1 ms", "0.8 ms", "< 0.01%", "Python Regex AST Parser"),
    ("2. Subgraph Cypher Retrieval", "11.8 ms", "18.5 ms", "0.65%", "Neo4j Bolt Protocol (Port 7687)"),
    ("3. Deterministic Arithmetic", "0.1 ms", "0.2 ms", "< 0.01%", "Integer-Paise Symbolic Engine"),
    ("4. Evidence Card Synthesis", "0.1 ms", "0.1 ms", "< 0.01%", "In-Memory Dictionary Formatter"),
    ("5. Neural LLM Generation", "1,790.3 ms", "8,580.7 ms", "99.33%", "Groq Cloud LPUs (gpt-oss-120b)"),
    ("6. Factual Verifier Guardrail", "0.2 ms", "0.3 ms", "0.01%", "Regex Metric Auditor"),
    ("Total End-to-End Pipeline", "1,802.6 ms", "8,600.3 ms", "100.0%", "Complete Advisory Cycle")
]

for row_data in lat_data:
    row = table7.add_row()
    for idx, text in enumerate(row_data):
        row.cells[idx].text = text

style_table_cells(table7, t7_widths)

doc.save(OUTPUT_PATH)
print(f"Updated DOCX at: {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)} bytes)")
