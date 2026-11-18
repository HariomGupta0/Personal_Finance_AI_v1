# Complete B.Tech Engineering Thesis Outline

**Degree:** Bachelor of Technology (B.Tech) in Computer Science and Engineering (Artificial Intelligence)  
**Title:** EXPLAINABLE PERSONAL FINANCE AI ASSISTANT USING DYNAMIC KNOWLEDGE GRAPH AND LARGE LANGUAGE MODEL  

---

## Preliminary Pages
* Title Page
* Candidate's Declaration & Supervisor's Certificate
* Acknowledgements
* Abstract (Structured: Context, Problem, Methodology, Results, Key Contribution)
* Table of Contents
* List of Figures (referencing `thesis_documentation/figures_index.md`)
* List of Tables (referencing `thesis_documentation/tables_index.md`)
* List of Abbreviations and Acronyms (e.g., GraphRAG, XAI, NLU, Neo4j, LLM, DTI, EMI, UPI, SHA-256, PBKDF2)

---

## Chapter 1: Introduction
* **1.1 Background and Context**
  * The rise of conversational AI and consumer FinTech.
  * Challenges in personal financial literacy and autonomous decision support in the Indian economic landscape.
* **1.2 Motivation and Problem Statement**
  * The hallucination and arithmetic failure modes of generic Large Language Models.
  * The relational blind spots of conventional Vector RAG.
  * The opacity and lack of auditability in black-box AI advisors.
* **1.3 Research Objectives**
  * Development of an immutable symbolic Knowledge Graph in Neo4j.
  * Implementation of a deterministic Python financial reasoning engine using integer-paise precision.
  * Design of an intent-scoped GraphRAG subgraph retrieval pipeline.
  * Creation of a two-tier post-generation factual verifier to eliminate financial hallucinations.
  * Engineering of a full-stack interactive dashboard with multimodal transaction ingestion.
* **1.4 Core Contributions of the Work**
  * Decoupled neuro-symbolic framework separating data storage, math calculation, and natural language explanation.
  * 100% mathematical accuracy on complex multi-hop affordability and runway diagnostics.
  * Robust SHA-256 transaction deduplication and automated internal bank transfer disambiguation.
* **1.5 Scope and Delimitations**
* **1.6 Thesis Organization and Chapter Structure**

---

## Chapter 2: Literature Review & Related Work
* **2.1 Evolution of Personal Finance Management Systems (PFMS)**
  * Traditional rule-based budgeting apps (Mint, YNAB, Monefy).
* **2.2 Large Language Models in Financial Services**
  * FinGPT, BloombergGPT, and open-weights reasoning models.
  * The stochastic nature of next-token prediction and vulnerability in algebraic computation.
* **2.3 Retrieval-Augmented Generation (RAG) Architectures**
  * Dense vector embeddings (Cosine similarity, FAISS, Pinecone).
  * The "Flat Document" fallacy: why semantic similarity fails multi-hop relational financial accounting.
* **2.4 Knowledge Graphs and GraphRAG in AI Systems**
  * Entity-relationship modeling in financial knowledge representation.
  * Subgraph retrieval vs. vector chunking.
* **2.5 Explainable Artificial Intelligence (XAI) in FinTech**
  * Transparency, provenance tracking, and regulatory requirements (RBI guidelines, GDPR explainability).
* **2.6 Hallucination Detection and Guardrail Mechanisms**
  * Output validation, self-consistency prompting, and deterministic symbolic verifiers.
* **2.7 Literature Taxonomy and Comparative Analysis Matrix**
  * Analysis of 15–20 peer-reviewed papers (IEEE, ACM, Springer, Elsevier).
* **2.8 Identified Research Gap and Problem Formulation**

---

## Chapter 3: System Requirements & Architectural Design
* **3.1 Requirements Analysis**
  * Functional Requirements (FR1 to FR10: Transaction CRUD, CSV Ingestion, Vision OCR, Affordability, Runway, DTI, Health Score, Multi-turn Chat, Transfer Detection).
  * Non-Functional Requirements (NFR1 to NFR6: Sub-2s Latency, Zero Floating-Point Error, 100% Math Accuracy, Rate Limiting, User Isolation, Session Security).
* **3.2 Architectural Philosophy: Decoupled Neuro-Symbolic GraphRAG**
* **3.3 Tier-by-Tier Component Architecture**
  * Presentation Tier (React 18, Vite, Recharts, Lucide UI).
  * API Gateway Tier (FastAPI, Uvicorn, SlowAPI, Signed HTTP-Only Cookies).
  * Dynamic Knowledge Graph Tier (Neo4j, Bolt Driver, Schema Constraints).
  * Deterministic Financial Engine Tier (Python integer-paise source of truth).
  * Multimodal Ingestion Tier (CSV Parser, Groq Vision OCR, Normalizer, Fingerprinter).
  * Language Orchestration Tier (Groq Cloud LLM, Prompt Registry, XML Isolation).
  * Guardrail Verification Tier (Two-tier regex metric verifier, Fallback generator).
* **3.4 Architectural and UML Modeling**
  * High-Level System Architecture Diagram (Figure 2.1).
  * End-to-End Execution Sequence Diagram (Figure 2.2).
  * GraphRAG Subgraph Retrieval Flow (Figure 2.3).
  * Hallucination-Defense Verification State Machine (Figure 2.4).
* **3.5 Security, Privacy, and User Isolation Architecture**
  * Zero-trust user ID derivation from server-side HMAC session tokens.
  * PBKDF2 password hashing with cryptographically secure random salts.
  * XML delimiter boundary defense against prompt injection attacks.

---

## Chapter 4: Data Engineering, Ingestion & Knowledge Graph Modeling
* **4.1 Financial Data Sources & Characteristics**
  * Synthetic demo portfolios, bank statement CSV formats (HDFC, SBI, ICICI dialects), receipt and UPI images.
* **4.2 Data Preprocessing and Ingestion Pipeline**
  * CSV dialect detection and column mapping.
  * Indian banking narration parsing and canonical merchant extraction.
  * SHA-256 transaction fingerprinting with collision-resistant occurrence indices.
* **4.3 Automated Internal Bank Transfer Detection**
  * Multi-account transfer detection ($\pm 2$ day window, opposite types, equal amounts).
  * ATM, cash withdrawal, and commercial merchant disqualification heuristics.
  * User confirmation workflow and retroactive linking in Neo4j.
* **4.4 Multimodal Receipt and UPI Screenshot Extraction**
  * Groq Vision OCR pipeline using `qwen/qwen3.8-27b`.
  * Zero-shot JSON extraction schema with strict legible-value constraints.
* **4.5 Neo4j Knowledge Graph Schema Design**
  * Entity node specifications (User, Account, Category, Transaction, Income, Loan, EMI, Goal, Merchant, ImportBatch).
  * Relationship semantics, properties, and cardinalities.
  * Schema constraints and B-Tree indexing.

---

## Chapter 5: Methodology & Implementation Details
* **5.1 Natural Language Understanding (NLU) & Question Parsing**
  * Fast rule-based regex AST parser with conversational context memory.
  * Date ambiguity detection and conversational clarification flow.
  * Secondary LLM parser fallback for unstructured complex queries.
* **5.2 Targeted GraphRAG Subgraph Retrieval**
  * Intent-to-Cypher mapping algorithms.
  * Authorized entity extraction avoiding full-database token bloat.
* **5.3 Deterministic Financial Reasoning Engine**
  * Mathematical foundations: Savings Rate, Emergency Reserve Buffer, Emergency Runway, DTI Ratio.
  * Purchase Safety Affordability Algorithm (liquid balance, pending debts, reserve buffers).
  * 0–100 Financial Health Scoring model with letter grade cutoffs (A, B, C, D).
  * Task 2 Historical Runway improvements: 4-state account lifecycle, MTD interval anchoring, and continuous gap detection.
* **5.4 Grounded Prompt Engineering & LLM Orchestration**
  * Versioned prompt templates (v1.0 baseline vs v1.1 4-section executive cards).
  * XML delimiter isolation preventing prompt injection.
  * Asynchronous Groq API client with exponential backoff.
* **5.5 Post-Generation Verification & Fallback Subsystem**
  * Two-tier regex metric extraction and status auditing.
  * Automated retry feedback loop and deterministic fallback generation.
* **5.6 Frontend Engineering & Visual Dashboards**
  * Recharts integration for expense breakdown and historical trends.
  * Interactive Assistant Chat with glassmorphic executive cards.
  * Import Manager with dual CSV and Vision upload tabs.

---

## Chapter 6: Verification, Testing & Empirical Evaluation
* **6.1 Testing Methodology & Infrastructure**
  * Unit test suite (84 tests covering financial engine, historical runway, money helpers).
  * Integration test suite (Neo4j live Bolt database transactions, transfer linking).
  * Authentication and rate-limiting test suite.
* **6.2 Automated Multi-Dimensional Research Benchmark (24 Scenarios)**
  * Dimension 1: Numerical Correctness (5/5 passed, 100%).
  * Dimension 2: Status Consistency (4/4 passed, 100%).
  * Dimension 3: Unsupported Claims / Phantom Number Rejection (4/4 passed, 100%).
  * Dimension 4: Reporting Periods & Missing Data Handling (4/4 passed, 100%).
  * Dimension 5: Prompt Injection Resistance (4/4 passed, 100%).
  * Dimension 6: Safe Fallback Handling during Outages (3/3 passed, 100%).
* **6.3 Quantitative Performance & Latency Profiling**
  * Micro-benchmarking of latency across NLU, Graph, Engine, Prompt, and LLM stages.
  * Empirical latency verification (~1,802 ms end-to-end turn).
* **6.4 Qualitative Case Studies & Failure Mode Analysis**
  * Case Study 1: Affordability query (*"Can I spend ₹15,000 on a phone?"*) comparing Vector RAG failure vs GraphRAG grounded success.
  * Case Study 2: Historical runway diagnostics with incomplete current month data.

---

## Chapter 7: Results and Discussion
* **7.1 Analysis of Experimental Findings**
  * Proven superiority of decoupled neuro-symbolic architecture over naive LLM reasoning.
  * Elimination of floating-point rounding errors via integer-paise representation.
* **7.2 Evaluation Against Project Objectives**
* **7.3 Practical Significance for Consumer FinTech in India**
  * Support for UPI, Indian banking narrations, Rupee formatting, and localized debt obligations.
* **7.4 Limitations and Identified Gaps**
  * Absence of live Account Aggregator API feeds.
  * Need for extensive longitudinal multi-year human usability trials.

---

## Chapter 8: Conclusion & Future Scope
* **8.1 Summary of Completed Work and Technical Contributions**
* **8.2 Future Research and Engineering Directions**
  * Account Aggregator (AA) framework integration.
  * Real-time investment and equity portfolio valuation.
  * Multilingual conversational models for vernacular financial advice.
  * Native cross-platform mobile application deployment.

---

## References
* Authoritative peer-reviewed papers cited in standard IEEE format.

## Appendices
* **Appendix A:** Neo4j Graph Database Cypher Initialization Scripts & Constraints.
* **Appendix B:** FastAPI REST Endpoint Documentation & OpenAPI Specifications.
* **Appendix C:** Prompt Templates (v1.0 Baseline vs. v1.1 4-Section Executive Card).
* **Appendix D:** Full 24-Scenario Research Benchmark Dataset Specification.

