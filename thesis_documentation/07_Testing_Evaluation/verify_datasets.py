# verify_datasets.py
import os
import json
import csv

DATA_DIR = r"C:\Users\gupta\Documents\HARIOM\Personal_Finance_AI_FYP\thesis_documentation\07_Testing_Evaluation\data"

print("="*70)
print("VERIFYING EMPIRICAL EVALUATION DATASETS")
print("="*70)

# 1. Categorization
with open(os.path.join(DATA_DIR, "categorization_benchmark_300.json"), "r", encoding="utf-8") as f:
    cats = json.load(f)

total_cats = len(cats)
correct_cats = sum(1 for c in cats if c["is_correct"])
acc_cats = (correct_cats / total_cats) * 100

print(f"\n1. Categorization Benchmark (N={total_cats}):")
print(f"   Correct: {correct_cats} / {total_cats}")
print(f"   Overall Accuracy: {acc_cats:.2f}%")

# Compute per-class precision and recall
classes = sorted(list(set(c["ground_truth_category"] for c in cats)))
f1_list = []
print("   Per-Class Breakdown:")
for cls in classes:
    tp = sum(1 for c in cats if c["ground_truth_category"] == cls and c["predicted_category"] == cls)
    fp = sum(1 for c in cats if c["ground_truth_category"] != cls and c["predicted_category"] == cls)
    fn = sum(1 for c in cats if c["ground_truth_category"] == cls and c["predicted_category"] != cls)
    support = sum(1 for c in cats if c["ground_truth_category"] == cls)
    p = tp / (tp + fp) if (tp + fp) > 0 else 0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0
    f1_list.append(f1)
    print(f"     * {cls:<25}: Support={support:2d}, P={p*100:5.1f}%, R={r*100:5.1f}%, F1={f1*100:5.1f}%")

macro_f1 = (sum(f1_list) / len(f1_list)) * 100
print(f"   Calculated Macro-F1: {macro_f1:.1f}%")

# 2. Transfer
with open(os.path.join(DATA_DIR, "transfer_benchmark_60.json"), "r", encoding="utf-8") as f:
    tr = json.load(f)

tp = sum(1 for t in tr if t["classification_outcome"] == "TP")
fp = sum(1 for t in tr if t["classification_outcome"] == "FP")
fn = sum(1 for t in tr if t["classification_outcome"] == "FN")
tn = sum(1 for t in tr if t["classification_outcome"] == "TN")
p_tr = tp / (tp + fp)
r_tr = tp / (tp + fn)
f1_tr = (2 * p_tr * r_tr) / (p_tr + r_tr)
fpr_tr = fp / (fp + tn)

print(f"\n2. Transfer Disambiguation Benchmark (N={len(tr)}):")
print(f"   TP={tp}, FP={fp}, FN={fn}, TN={tn}")
print(f"   Precision: {p_tr*100:.1f}%, Recall: {r_tr*100:.1f}%, F1-Score: {f1_tr*100:.1f}%, FPR: {fpr_tr*100:.1f}%")

# 3. Receipt OCR
with open(os.path.join(DATA_DIR, "receipt_ocr_benchmark_60.json"), "r", encoding="utf-8") as f:
    ocr = json.load(f)

digital = [o for o in ocr if o["receipt_type"] == "DIGITAL_UPI_SCREENSHOT"]
paper = [o for o in ocr if o["receipt_type"] == "PHYSICAL_THERMAL_PAPER"]

fea_d = sum(1 for o in digital if o["all_fields_correct"]) / len(digital) * 100
fea_p = sum(1 for o in paper if o["all_fields_correct"]) / len(paper) * 100
fea_all = sum(1 for o in ocr if o["all_fields_correct"]) / len(ocr) * 100

print(f"\n3. Multimodal Receipt OCR Benchmark (N={len(ocr)}):")
print(f"   Digital Screenshots (N={len(digital)}): FEA = {fea_d:.1f}% ({sum(1 for o in digital if o['all_fields_correct'])}/{len(digital)})")
print(f"   Physical Paper (N={len(paper)}):      FEA = {fea_p:.1f}% ({sum(1 for o in paper if o['all_fields_correct'])}/{len(paper)})")
print(f"   Combined Overall (N={len(ocr)}):       FEA = {fea_all:.1f}% ({sum(1 for o in ocr if o['all_fields_correct'])}/{len(ocr)})")

# 4. SUS Survey
with open(os.path.join(DATA_DIR, "sus_survey_20_responses.csv"), "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    sus_rows = list(reader)

scores = [float(r["composite_sus_score"]) for r in sus_rows]
times = [float(r["completion_time_sec"]) for r in sus_rows]
successes = [r["unassisted_task_success"] == "True" for r in sus_rows]

mean_sus = sum(scores) / len(scores)
mean_time = sum(times) / len(times)
succ_rate = sum(successes) / len(successes) * 100

print(f"\n4. System Usability Scale (SUS) Survey (N={len(sus_rows)}):")
print(f"   Mean Composite SUS Score: {mean_sus:.2f} / 100")
print(f"   Unassisted Success Rate:  {succ_rate:.1f}% ({sum(successes)}/{len(successes)})")
print(f"   Average Completion Time:  {mean_time:.1f} seconds ({mean_time/60:.2f} minutes)")
print("="*70)

