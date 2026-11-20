import os

DOC_DIR = r"C:\Users\gupta\Documents\HARIOM\Personal_Finance_AI_FYP\thesis_documentation"

def read_file(rel_path):
    full_path = os.path.join(DOC_DIR, rel_path)
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return f"[Missing component: {rel_path}]"

ch1 = read_file("01_Project_Overview/project_understanding.md")
ch2_lit = read_file("06_Literature_Review/literature_review.md")
ch2_ref = read_file("06_Literature_Review/references.md")
ch3_meth = read_file("03_Methodology/methodology.md")
ch4_data = read_file("04_Data_Collection/data_collection_tools.md")
ch5_impl = read_file("05_Design_Implementation/implementation_details.md")
ch5_db = read_file("05_Design_Implementation/database_modelling.md")
ch6_test = read_file("07_Testing_Evaluation/testing.md")
ch6_eval = read_file("07_Testing_Evaluation/evaluation.md")
ch7_8_conc = read_file("08_Conclusion_Future_Scope/conclusion_future_scope.md")
tables = read_file("tables/academic_tables.md")
fig_index = read_file("figures_index.md")
missing_info = read_file("missing_information.md")

prelims = """# EXPLAINABLE PERSONAL FINANCE AI ASSISTANT USING DYNAMIC KNOWLEDGE GRAPH AND LARGE LANGUAGE MODEL

**A Major Project Thesis Submitted in Partial Fulfillment of the Requirements for the Degree of**  
**Bachelor of Technology (B.Tech)**  
**in**  
**Computer Science and Engineering (Artificial Intelligence)**

---

## CANDIDATE DECLARATION

I hereby declare that the work presented in this final-year thesis entitled **"Explainable Personal Finance AI Assistant Using Dynamic Knowledge Graph and Large Language Model"** is an authentic record of our own research and engineering work conducted under supervision. The content embodied in this thesis has not been submitted for the award of any other degree or diploma.

---

## SUPERVISOR CERTIFICATE

This is to certify that the thesis entitled **"Explainable Personal Finance AI Assistant Using Dynamic Knowledge Graph and Large Language Model"** represents the bona fide work carried out by the candidate under my guidance and supervision in partial fulfillment of the requirements for the degree of Bachelor of Technology in Computer Science and Engineering (Artificial Intelligence).

---

## ABSTRACT

Personal finance management is inherently quantitative, relational, and high-stakes. While conversational Artificial Intelligence—specifically Large Language Models (LLMs)—has demonstrated remarkable fluency in natural language comprehension, deploying generic LLMs or conventional Vector Retrieval-Augmented Generation (Vector RAG) for financial advisory introduces critical failure modes: arithmetic hallucinations, loss of relational context across multi-account ledgers, and black-box opacity.

This thesis presents the design, implementation, and empirical evaluation of an **Explainable Personal Finance AI Assistant** employing a **Decoupled Neuro-Symbolic GraphRAG Architecture**. The framework enforces a strict boundary between symbolic computation and neural language generation:
1. **Symbolic Single Source of Truth:** A native Neo4j Labeled Property Graph (`finance-ai-antigravity`) models complex multi-relational financial networks (Users, Accounts, Transactions, Categories, Incomes, Loans, EMIs, Goals, Merchants). All financial metrics—including net savings rates, multi-month emergency runways, debt-to-income (DTI) ratios, post-purchase solvency boundaries, and a 0–100 comprehensive financial health score—are calculated deterministically in pure Python using integer-paise representation ($1 Rupee = 100 Paise$), completely eliminating IEEE 754 floating-point rounding errors.
2. **Intent-Scoped GraphRAG Retrieval:** Fast, rule-based natural language parsing and intent classification trigger targeted Cypher graph traversals that extract only the authorized, relevant subgraphs, avoiding monolithic database token dumps and semantic drift.
3. **Neural Language Synthesis & Multimodal Ingestion:** Groq-hosted open LLMs (`openai/gpt-oss-120b`) translate verified mathematical evidence cards into empathetic, transparent 4-section executive reports (*The Quick Take, The Numbers, Smart Insights, What You Should Do Next*). Multimodal receipt and UPI transaction screenshots are extracted zero-shot via Groq Vision (`qwen/qwen3.8-27b`) with mandatory user confirmation.
4. **Deterministic Factual Guardrail & Verifier:** A post-generation regex metric verifier audits generated explanations against the symbolic engine's output. Any decision contradiction or hallucinated amount triggers an automated retry feedback loop, falling back to deterministic reports upon repeated failure.

The system was verified through comprehensive testing suites: 84/84 financial engine tests passing, 16/16 internal transfer detection tests passing, and a 24-scenario multi-dimensional research benchmark achieving 100.0% accuracy across numerical correctness, status consistency, ungrounded claim interception, missing data caveats, prompt injection defense, and fallback resilience. Latency micro-benchmarking revealed that the complete symbolic pipeline (parsing, graph retrieval, arithmetic, and verification) executes in ~12.3 ms, with end-to-end turns completing in ~1,802 ms. The resulting platform bridges the gap between natural language fluency and regulatory-grade mathematical auditability.

**Keywords:** Explainable AI (XAI), GraphRAG, Knowledge Graphs, Neo4j, Personal Finance Technology (FinTech), Large Language Models (LLMs), Neuro-Symbolic AI, Deterministic Financial Arithmetic, Hallucination Mitigation.

---

## TABLE OF CONTENTS

1. **Chapter 1: Introduction & Project Overview**
2. **Chapter 2: Literature Review & Related Work**
3. **Chapter 3: Research Methodology & Mathematical Modeling**
4. **Chapter 4: Data Engineering, Ingestion & Software Platforms**
5. **Chapter 5: System Design, Implementation & Knowledge Graph Modeling**
6. **Chapter 6: Testing, Verification & Performance Evaluation**
7. **Chapter 7: Conclusion**
8. **Chapter 8: Future Scope**
9. **References (IEEE Format)**
10. **Appendices**
    * *Appendix A: Academic Tables Reference*
    * *Appendix B: Figures and Diagrams Index*
    * *Appendix C: Evidence Audit and Identified Gaps*

---
"""

appendices = f"""
---

# APPENDICES

## APPENDIX A: MASTER ACADEMIC TABLES REFERENCE
{tables}

## APPENDIX B: FIGURES AND DIAGRAMS INDEX
{fig_index}

## APPENDIX C: EVIDENCE AUDIT AND IDENTIFIED INFORMATION GAPS
{missing_info}
"""

full_thesis = "\n\n".join([
    prelims,
    ch1,
    ch2_lit,
    ch3_meth,
    ch4_data,
    ch5_impl,
    ch5_db,
    ch6_test,
    ch6_eval,
    ch7_8_conc,
    ch2_ref,
    appendices
])

out_path = os.path.join(DOC_DIR, "COMPLETE_THESIS_DRAFT.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(full_thesis)

print(f"COMPLETE_THESIS_DRAFT.md successfully written! Total characters: {len(full_thesis)}")
