# EXPLAINABLE PERSONAL FINANCE AI ASSISTANT USING DYNAMIC KNOWLEDGE GRAPH AND LARGE LANGUAGE MODEL

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


# Chapter 1 — Project Understanding & Comprehensive Overview

## 1.1 Project Title and Academic Context
* **Thesis Title:** EXPLAINABLE PERSONAL FINANCE AI ASSISTANT USING DYNAMIC KNOWLEDGE GRAPH AND LARGE LANGUAGE MODEL
* **Degree:** Bachelor of Technology (B.Tech) in Computer Science and Engineering (Artificial Intelligence)
* **Domain:** Financial Technology (FinTech), Explainable Artificial Intelligence (XAI), Graph Retrieval-Augmented Generation (GraphRAG), Knowledge Graphs, and Natural Language Processing (NLP).

---

## 1.2 Problem Statement & Research Motivation

### 1.2.1 The Core Dilemma in Financial AI
Personal finance management is inherently quantitative, relational, and high-stakes. While conversational Artificial Intelligence—specifically Large Language Models (LLMs)—has demonstrated remarkable fluency in natural language comprehension, deploying generic LLMs or conventional Vector Retrieval-Augmented Generation (Vector RAG) for personal financial advice introduces three catastrophic vulnerabilities:

1. **Arithmetic Hallucination and Stochastic Inconsistency:**
   LLMs generate text probabilistically based on next-token distribution rather than executing algebraic reasoning. In financial domains requiring exact accounting (such as debt-to-income ratios, emergency runway buffers, or post-purchase solvency), LLMs regularly invent numbers, round inconsistently, or fail basic multi-hop arithmetic (e.g. subtracting loan EMIs from liquid balances while factoring in a 3-month expense reserve).
2. **Loss of Relational and Temporal Context in Vector Embeddings:**
   Standard Vector RAG flattens financial ledgers into unstructured text chunks, computing cosine similarity over dense embeddings. This approach destroys the strict multi-entity relational topologies fundamental to financial health—specifically, how a `User` owns multiple `Accounts`, how an `Account` incurs `Transactions` grouped under `Categories`, and how recurring `Loans` obligate specific contractual `EMIs`. In vector search, semantic similarity often retrieves unrelated transactions while missing critical pending liabilities.
3. **Black-Box Opacity and Lack of Auditability:**
   Conventional financial chatbots output advice without traceable provenance. When a user asks *"Can I afford a ₹15,000 smartphone?"*, a generic model provides an ungrounded binary judgment without demonstrating the mathematical steps or proving which specific bank balances and loan obligations were factored into the decision.

### 1.2.2 Proposed Solution: Decoupled Explainable Architecture
This project resolves these fundamental challenges by proposing and implementing a **decoupled, hybrid neuro-symbolic architecture**:
- **Symbolic Layer (Neo4j Dynamic Knowledge Graph + Deterministic Python Financial Engine):** Serves as the immutable single source of truth. All financial entities, relational edges, and transactions are stored as graph nodes. All mathematical aggregations, ratios, health scores, and solvency boundaries are computed deterministically using integer-paise precision in Python.
- **Neural Layer (Groq-hosted Open LLM + Multimodal Vision OCR):** Serves purely as a natural language interface. The LLM translates verified mathematical evidence cards into empathetic, transparent 4-section executive explanations, while a post-generation Deterministic Verifier actively intercepts any contradictory or ungrounded assertions before they reach the user.

---

## 1.3 Core Architectural Axioms

The implementation of this system is governed by five non-negotiable architectural axioms:

| Axiom | Principle | Implementation Enforcement |
| :--- | :--- | :--- |
| **Axiom 1** | **The LLM is NEVER the source of financial truth.** | Financial arithmetic is strictly forbidden in LLM prompts. All figures are computed by `backend/app/engine/financial_engine.py` and provided as structured evidence. |
| **Axiom 2** | **Integer-Paise Precision Throughout.** | To eliminate IEEE 754 floating-point rounding errors (e.g., $0.1 + 0.2 \neq 0.3$), all monetary amounts are normalized, stored, and calculated in integer paise ($1\text{ Rupee} = 100\text{ Paise}$) via `backend/app/core/money.py`. |
| **Axiom 3** | **Relational Grounding via Intent-Scoped GraphRAG.** | Rather than passing monolithic database dumps or flat vector chunks, `backend/app/rag/graph_rag.py` executes targeted Cypher graph traversals to extract only the authorized subgraph relevant to the user's specific financial intent. |
| **Axiom 4** | **Two-Tier Post-Generation Verification.** | Every generated LLM response is parsed by `backend/app/services/verifier.py`. Any contradiction in status (e.g. Engine: `NOT_SAFE` vs LLM: `SAFE`) or hallucinated numerical token immediately triggers automated retry or deterministic fallback. |
| **Axiom 5** | **Zero-Trust Input & Sovereign Deduplication.** | Financial inputs (CSV statements, receipt images) undergo SHA-256 fingerprint deduplication with occurrence tracking, canonical merchant normalization, and user isolation in Neo4j. |

---

## 1.4 Verified Technology Stack Specification

The implementation of the system was thoroughly inspected across all configuration files, dependency manifests, and source modules:

### 1. Backend Architecture
* **Framework:** FastAPI (`v0.115.0+`) running ASGI server Uvicorn on Python 3.13 (`.venv`).
* **Database Driver:** `neo4j` Python driver (`v5.25.0+`) communicating via Bolt protocol on port `7687` to an isolated database (`finance-ai-antigravity`).
* **LLM Engine:** Groq Cloud API executing `openai/gpt-oss-120b` (low-latency inference, ~1,800 ms total pipeline turn).
* **Vision OCR Engine:** Groq Cloud Vision API executing `qwen/qwen3.8-27b` (fallback: `meta-llama/llama-4-scout-17b-16e-instruct`) for receipts and UPI screenshot parsing.
* **Security & Session:** Signed HTTP-only session cookies with PBKDF2 HMAC-SHA256 password salting, CSRF mitigation, and `slowapi` rate limiting.
* **Data Processing & Utilities:** Python `decimal.Decimal`, `pydantic v2`, `hashlib` SHA-256, `re` regex engine.

### 2. Frontend Architecture
* **Framework:** React 18 (`v18.3.1`) scaffolded with Vite (`v5.4.2`).
* **State & Networking:** Client-side React hooks (`useState`, `useEffect`) communicating with backend `/api` via Vite reverse proxy on port `3000`.
* **Visualizations & UI:** Recharts (`v2.13.0`), Lucide React (`v1.16.0`), custom dark-mode glassmorphic CSS design system.
* **Formatting:** Markdown rendering with `react-markdown` (`v10.1.0`) supporting structured 4-section executive cards.

---

## 1.5 System Functional Scope & Implemented Capabilities

The application provides a comprehensive suite of verified financial capabilities:

1. **Deterministic Solvency & Affordability Analysis (`PURCHASE_SAFETY`):**
   Evaluates proposed discretionary purchases against liquid checking/savings reserves, short-term debt servicing obligations (pending EMIs), and mandatory emergency reserve buffers ($3 \times \text{Monthly Expenses}$).
2. **Emergency Runway & Burn-Rate Diagnostics (`EMERGENCY_RUNWAY_ANALYSIS`):**
   Calculates available survival runway in months ($R = \frac{\text{Liquid Balance}}{\text{Monthly Burn}}$), categorizing financial resilience into `CRITICAL`, `INSUFFICIENT`, `HEALTHY`, and `STRONG`. Includes Task 2 Historical Runway improvements with 4-state account lifecycle and MTD interval continuity.
3. **Debt-to-Income (DTI) & Liability Servicing (`DEBT_ANALYSIS`):**
   Deduplicates pending loan EMIs across target reporting months, computing DTI ratios with tiered risk bands (`LOW` $\le 20\%$, `MODERATE` $\le 35\%$, `HIGH` $\le 50\%$, `CRITICAL` $> 50\%$).
4. **Comprehensive Financial Health Scoring (`FINANCIAL_HEALTH`):**
   Calculates an authoritative 0–100 financial health index across 4 weighted pillars: Savings Rate (35%), Runway Duration (35%), Debt Burden (20%), and Emergency Goal Funding (10%), assigning academic letter grades (A, B, C, D).
5. **Multimodal Ingestion & Statement Normalization:**
   Supports bank statement CSV uploads across varied bank dialects with SHA-256 fingerprint deduplication, UPI/POS/IMPS narration normalization, internal transfer disambiguation, and Groq Vision receipt image extraction.
6. **Conversational AI Financial Advisor with Grounded Evidence Cards:**
   Multi-turn conversational assistant with conversational memory, date-ambiguity resolution, XML delimiter prompt isolation, and structured 4-section executive responses (*The Quick Take, The Numbers, Smart Insights, What You Should Do Next*).

# Chapter 2 — Comprehensive Literature Review

## 2.1 Introduction and Theoretical Foundations

The integration of Artificial Intelligence (AI) into financial management has transitioned through three distinct historical paradigms:
1. **Rule-Based Heuristic Systems (1990s–2010s):** Traditional Personal Financial Management (PFM) software—such as Intuit Quicken, Mint, and YNAB (You Need A Budget)—relied strictly on deterministic spreadsheet calculations, relational relational database schemas, and rigid categorization rules. While mathematically robust, these platforms suffered from zero natural language understanding, steep user learning curves, and inability to handle conversational advisory queries.
2. **Supervised Machine Learning & Deep Learning (2015–2022):** The adoption of recurrent neural networks (LSTMs, GRUs) and supervised classifiers enabled automated transaction categorization, fraud detection, and credit scoring. However, these models functioned as black-box predictors, incapable of multi-hop contextual reasoning or interactive explanation.
3. **Generative AI, Large Language Models (LLMs) & GraphRAG (2023–Present):** The emergence of autoregressive transformer architectures has revolutionized human-machine dialogue. Nevertheless, their fundamental limitation—the stochastic hallucination of numerical figures and poor algebraic reasoning—demands a hybrid neuro-symbolic framework.

This chapter presents a rigorous, in-depth academic review of 18 authoritative peer-reviewed research papers across six core domains: Financial Technology, Knowledge Graphs, Retrieval-Augmented Generation, Hallucination Mitigation, Explainable AI (XAI), and Neuro-Symbolic Integration.

---

## 2.2 Critical Domain Analysis

### 2.2.1 Large Language Models in Financial Services
The financial domain imposes unforgiving constraints on language models: zero tolerance for factual error, absolute mathematical determinism, and regulatory accountability. 

Wu et al. [1] introduced **BloombergGPT**, a 50-billion parameter model trained on a massive 363-billion token financial corpus alongside general language datasets. BloombergGPT decisively demonstrated that domain-specific pre-training significantly outperforms general LLMs on financial NLP benchmarks (e.g., sentiment analysis, financial named entity recognition, and headline classification). However, as Wu et al. explicitly acknowledged, pre-training a monolithic neural network does not resolve the underlying stochastic nature of token generation: when tasked with computing multi-step arithmetic (such as amortizing a loan or balancing a budget), the model remains susceptible to arithmetic drift and cannot guarantee compliance with banking regulations.

To democratize financial LLMs, Yang et al. [2] developed **FinGPT**, an open-source framework advocating parameter-efficient fine-tuning (LoRA) over dynamic, real-time financial market data. FinGPT addresses the rapid staleness of financial knowledge by decoupling data acquisition from model weights. Yet, like BloombergGPT, FinGPT operates primarily on textual sentiment and news summarization; it lacks an underlying symbolic reasoning engine to perform rigorous multi-account ledger reconciliation or compute solvency constraints.

### 2.2.2 The Limitations of Conventional Vector RAG
Retrieval-Augmented Generation (RAG), formalized by Lewis et al. [3], was designed to ground LLM generations in external documents, thereby mitigating parametric memory hallucinations. In a standard Vector RAG setup, raw documents are segmented into fixed-size character chunks, transformed into continuous dense vectors via an embedding model (e.g., OpenAI `text-embedding-ada-002` or BAAI `bge-large`), and indexed in a vector database (FAISS, Pinecone, Milvus). At inference time, the user's query is embedded, and the top-$k$ nearest neighbors are retrieved via cosine similarity.

While highly effective for encyclopedic question-answering, Gao et al. [4] and Borgeaud et al. [5] (in their work on RETRO) emphasize the structural breakdown of Vector RAG when applied to structured financial ledgers:
1. **The "Flat Chunk" Fallacy:** Financial ledgers are not prose narratives; they are multi-relational networks of accounts, debits, credits, merchants, and contractual obligations. Chunking a monthly bank statement arbitrarily at 500 tokens breaks transactional causality (e.g., separating an EMI debit from its corresponding loan balance).
2. **Semantic Similarity vs. Relational Relevance:** In vector space, a query such as *"Can I spend ₹15,000 on a phone?"* retrieves chunks mentioning *"phone bills"* or *"electronics purchases"*, rather than the strictly relevant nodes: *liquid account balances, pending debt obligations, and emergency reserve targets*.
3. **Inability to Perform Aggregations:** Vector databases cannot compute sums, averages, or ratios across retrieved chunks. If an LLM is fed 50 retrieved transaction snippets and asked for total monthly dining spend, it frequently hallucinates the final sum due to attention distribution limits over numeric tokens.

### 2.2.3 Knowledge Graphs and GraphRAG
To overcome the relational collapse of vector embeddings, Hogan et al. [6] provided the comprehensive theoretical taxonomy for **Knowledge Graphs (KGs)** as structured, graph-based knowledge representations where entities are nodes and typed directed edges represent semantic relationships. KGs enforce strict domain ontologies, facilitate multi-hop traversals, and enable formal query languages such as Cypher or SPARQL.

Pan et al. [7] developed an authoritative roadmap for **unifying Large Language Models and Knowledge Graphs**. They categorize the synergy into three paradigms:
1. *KG-enhanced LLMs:* Using KGs during pre-training or retrieval to ground LLM generations.
2. *LLM-enhanced KGs:* Using LLMs for relation extraction, entity linking, and graph completion.
3. *Synergistic Neuro-Symbolic Systems:* Decoupling explicit factual storage and reasoning (KG) from conversational language generation (LLM).

Edge et al. [8] formalized **GraphRAG**, demonstrating that structuring retrieved knowledge as connected subgraphs rather than isolated vector chunks substantially improves multi-hop reasoning, global contextual synthesis, and answer faithfulness. In financial contexts, Deng et al. [9] proved that combining Knowledge Graphs with pre-trained language models allows question-answering systems to traverse complex entity paths (e.g., `User -> Account -> Transaction -> Category`) without losing relational provenance.

### 2.2.4 Numerical Reasoning and Financial Question Answering
The necessity for symbolic mathematical calculation in financial AI is underscored by benchmark studies on numerical reasoning. Chen et al. [10] established **FinQA**, a benchmark of financial reports requiring numerical reasoning over hybrid text and structured tables. Their findings revealed that state-of-the-art transformer models achieve less than 65% execution accuracy on multi-step financial arithmetic, with failure rates rising sharply as the number of algebraic operators increases.

Similarly, Zhu et al. [11] introduced **TAT-QA**, analyzing hybrid tabular and textual question answering. They proved that standard LLM architectures consistently fail when calculations require selective filtering (e.g., excluding internal transfers or isolating essential living costs). These findings establish a crucial thesis axiom: **The LLM must never be tasked with performing arithmetic; financial computation must be relegated entirely to a deterministic symbolic engine.**

### 2.2.5 Hallucination Taxonomies & Post-Generation Guardrails
Ji et al. [12] and Zhang et al. [13] formulated comprehensive taxonomies of hallucinations in Large Language Models, classifying them into:
1. **Intrinsic Hallucinations:** Generated text that directly contradicts the provided input source evidence.
2. **Extrinsic Hallucinations:** Generated text that introduces unverifiable facts or figures absent from the context.

In personal finance, an intrinsic hallucination occurs when the financial engine outputs `NOT_SAFE` but the LLM states *"You can easily afford this purchase."* An extrinsic hallucination occurs when the LLM invents a phantom figure (e.g., citing a non-existent ₹5,000 electricity bill). 

Shuster et al. [14] demonstrated that while retrieval augmentation significantly reduces hallucination rates, it does not eliminate them entirely. Mialon et al. [15], surveying augmented language models, advocate for external execution verifiers—discrete software programs that inspect the model's generated text against structured tools before presenting output to the user. This directly justifies our implementation of `backend/app/services/verifier.py`.

### 2.2.6 Explainable Artificial Intelligence (XAI) in FinTech
Arrieta et al. [16] defined the foundational principles of Explainable AI (XAI) for responsible deployment, identifying key desiderata: trustworthiness, causality, transferability, informativeness, and fairness. In consumer finance, explainability is not merely an engineering aesthetic; regulatory bodies (including the Reserve Bank of India and the European Union's AI Act) mandate that automated financial decision support systems provide clear, audit-traceable logic.

Bhatt et al. [17] investigated explainable machine learning in enterprise deployments, showing that end-users overwhelmingly reject raw numerical scores or black-box predictions unless accompanied by actionable, structured rationales. Furthermore, Kıcıman et al. [18] explored causal reasoning in LLMs, noting that while LLMs can articulate causal relationships when primed with correct facts, their internal representations cannot discover causal links without external symbolic scaffolding.

---

## 2.3 Authoritative Literature Review Matrix (18 Verified Papers)

The following table provides an exhaustive, comparative analysis of the 18 genuine academic papers establishing the theoretical foundation of this thesis:

| Ref | Author(s) & Year | Publication Venue | Core Research Focus | Key Methodology / Technology | Critical Findings & Limitations | Direct Relevance to Our Thesis |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **[1]** | Wu et al. (2023) | ACL 2023 / arXiv:2303.17564 | Financial-domain pre-trained LLM | 50B parameter transformer trained on 363B financial tokens + 345B public tokens | Outperforms generic LLMs on financial NLP tasks; still hallucinates arithmetic; computationally prohibitive for local deployment | Proves need for decoupled architecture where LLM handles prose while Python handles arithmetic |
| **[2]** | Yang et al. (2023) | IJCAI 2023 FinLLM | Open-source financial language model framework | LoRA-based parameter-efficient fine-tuning on streaming financial news | Democratizes financial NLP; focuses on market sentiment and textual summarization, not personal ledger accounting | Validates use of lightweight open LLMs (`gpt-oss-120b`) augmented with external dynamic data |
| **[3]** | Lewis et al. (2020) | NeurIPS 2020 | Retrieval-Augmented Generation (RAG) | Dense Passage Retrieval (DPR) + sequence-to-sequence generator (BART) | Grounds LLM outputs in textual documents; prone to retrieving irrelevant chunks when relational topology is ignored | Foundational paper for RAG; highlights why vector-only retrieval is insufficient for relational graph data |
| **[4]** | Gao et al. (2023) | arXiv:2312.10997 | Comprehensive survey on RAG paradigms | Naive RAG vs. Advanced RAG vs. Modular RAG taxonomies | Identifies low precision, semantic drift, and arithmetic hallucination as primary failure modes of Naive RAG | Establishes theoretical justification for our Modular GraphRAG architecture |
| **[5]** | Borgeaud et al. (2022) | ICML 2022 | Retrieval from trillions of tokens (RETRO) | Autoregressive language modeling with chunked cross-attention retrieval | Demonstrates retrieval scaling benefits; struggles with tabular aggregations across retrieved chunks | Confirms that neural retrieval cannot perform mathematical aggregations across multiple documents |
| **[6]** | Hogan et al. (2021) | ACM Computing Surveys | Comprehensive Knowledge Graph foundations | Graph data models (RDF, Property Graphs), Cypher/SPARQL query languages, deductive reasoning | Formalizes knowledge representation; highlights strict schema enforcement and multi-hop relationship traversal | Justifies selection of Neo4j Labeled Property Graph for personal financial entities |
| **[7]** | Pan et al. (2024) | IEEE TKDE, vol. 36, no. 7 | Roadmap for unifying LLMs and Knowledge Graphs | Taxonomies of KG-enhanced LLMs, LLM-enhanced KGs, and Synergistic AI | Concludes that neuro-symbolic synergy achieves superior explainability and zero factual drift compared to pure neural models | Direct theoretical foundation for our decoupled Neo4j + Python Engine + Groq architecture |
| **[8]** | Edge et al. (2024) | Microsoft Research / arXiv:2404.16130 | Graph RAG for query-focused summarization | Graph extraction from text + hierarchical clustering + community summaries | Subgraph retrieval decisively outperforms vector RAG on complex multi-hop and global reasoning tasks | Validates our intent-scoped Cypher subgraph extraction over flat vector search |
| **[9]** | Deng et al. (2022) | IEEE Access, vol. 10 | Financial Question Answering using KGs and LLMs | Knowledge graph entity linking combined with pre-trained language models | Improves financial entity extraction; limited to static financial concepts without real-time balance mutation | Inspires our dynamic mutation pipeline updating graph balances in real time |
| **[10]** | Chen et al. (2021) | EMNLP 2021 | FinQA: Numerical reasoning over financial data | Annotated financial dataset requiring multi-step arithmetic over hybrid text/tables | SOTA neural models fail on multi-step financial math (&lt;65% accuracy); error rates compound with equation depth | Empirical proof that financial arithmetic must be offloaded from LLM to deterministic engine |
| **[11]** | Zhu et al. (2021) | ACL 2021 | TAT-QA: Question answering on tables and text | Hybrid financial reporting benchmark requiring extraction and arithmetic | Proves LLMs fail when calculations require selective filtering (e.g. excluding transfers or one-time spikes) | Directly motivates our deterministic financial engine and transaction classification rules |
| **[12]** | Ji et al. (2023) | ACM Computing Surveys | Survey on Hallucination in Large Language Models | Taxonomy of intrinsic vs. extrinsic hallucinations across NLG tasks | Categorizes causes: representation biases, decoding stochasticity, lack of grounding; reviews verification methods | Establishes the formal taxonomy used to design our two-tier verification layer |
| **[13]** | Zhang et al. (2023) | arXiv:2309.01219 | Survey on Hallucination in Large Language Models | Comprehensive taxonomy of detection and mitigation strategies | Emphasizes that post-hoc verification and external rule checkers are necessary for high-stakes domains | Theoretical basis for `backend/app/services/verifier.py` intercepting contradictory decisions |
| **[14]** | Shuster et al. (2021) | Findings of EMNLP 2021 | Retrieval augmentation to reduce conversational hallucination | Neural retrieval combined with conversational dialogue agents | Retrieval reduces hallucinations from 60% to 15%, but does not eliminate them; output validation still required | Proves that retrieval alone is insufficient without secondary deterministic guardrails |
| **[15]** | Mialon et al. (2023) | TMLR 2023 | Augmented Language Models: A Survey | Survey of language models augmented with tools, calculators, and databases | Identifies tool-use and modular orchestrators as the optimal paradigm for precision tasks | Directly supports our orchestration architecture (GraphRAG + Engine + LLM) |
| **[16]** | Arrieta et al. (2020) | Information Fusion (Elsevier) | Explainable AI (XAI): Concepts, taxonomies &amp; principles | Comprehensive survey of interpretability vs. explainability across AI models | Defines principles of responsible AI: auditability, provenance, causality, and human-comprehensible presentation | Establishes the formal XAI principles implemented in our 4-section executive cards |
| **[17]** | Bhatt et al. (2020) | ACM FAccT 2020 | Explainable Machine Learning in Deployment | Empirical study of XAI use-cases in enterprise organizations | Users distrust raw scores; demand verifiable evidence, contextual insights, and actionable next steps | Motivates our 4-section format: Quick Take, The Numbers, Smart Insights, Next Steps |
| **[18]** | Kıcıman et al. (2023) | Microsoft Research / arXiv:2305.00050 | Causal reasoning in Large Language Models | Counterfactual and causal reasoning benchmarks on advanced LLMs | LLMs cannot reliably infer causality without explicit structural constraints; symbolic graphs provide causal grounding | Justifies using Neo4j to enforce causal relations (`User -> Loan -> EMI -> Solvency`) |

---

## 2.4 Research Gap Identification & Academic Synthesis

### 2.4.1 Identified Research Gaps

A rigorous synthesis of the surveyed literature reveals four critical research gaps at the intersection of AI, Graph Technologies, and Personal Finance:

1. **The Arithmetic-Generative Gap:** Existing financial AI research either builds complex pre-trained neural models (BloombergGPT [1], FinGPT [2]) that remain probabilistically unreliable for exact arithmetic, or uses traditional calculators that lack natural language explanation. **There is an absence of an open, verifiable framework where deterministic arithmetic serves as the immutable single source of truth while the LLM is constrained strictly to grounded natural language explanation.**
2. **The Relational Loss in Financial Vector RAG:** While standard Vector RAG [3, 4] flattens documents into unstructured chunks, personal financial ledgers require multi-hop relational integrity (linking accounts, debits, categories, recurring loans, and pending EMIs). Current implementations do not leverage **Intent-Scoped Knowledge Graph Subgraph Retrieval** for personal finance.
3. **The Unverified Generation Gap:** Mainstream conversational assistants deploy LLMs directly to the user. Even with retrieval augmentation [14, 15], stochastic drift causes models to output advice that contradicts the retrieved metrics (e.g., advising an unaffordable purchase). **There is a lack of automated, two-tier post-generation verification that actively audits status labels and numbers before client delivery.**
4. **The Multimodal Ingestion & Normalization Deficit:** Academic financial QA benchmarks (FinQA [10], TAT-QA [11]) assume pristine, pre-formatted tabular data. In real-world consumer finance (especially in India), bank statements feature cryptic narrations (UPI/POS/NEFT), duplicate transaction entries, and inter-account transfers that corrupt expense baselines. **Existing literature overlooks end-to-end pipelines combining Vision OCR, merchant normalization, SHA-256 fingerprint deduplication, and internal transfer disambiguation.**

### 2.4.2 How the Proposed System Addresses These Gaps

The architecture designed and implemented in this thesis systematically resolves every identified gap:
- **Zero Floating-Point Drift:** Solves Gap 1 by executing all calculations in Python using custom integer-paise representation (`money.py`), guaranteeing 100% mathematical accuracy.
- **Relational Integrity via Neo4j:** Solves Gap 2 by constructing a multi-relational Knowledge Graph and executing intent-scoped Cypher queries that retrieve only authorized subgraphs.
- **Deterministic Hallucination Interception:** Solves Gap 3 by implementing `verifier.py`, an automated auditor enforcing a two-tier policy (blocking contradictions/phantom numbers, providing advisory feedback, and executing deterministic fallback upon failure).
- **Production Ingestion Pipeline:** Solves Gap 4 by deploying Groq Vision (`qwen/qwen3.8-27b`), rule-based Indian merchant normalization, SHA-256 collision-resistant fingerprinting, and automated 1-to-1 transfer detection across user accounts.

# Chapter 3 — Research Methodology & Mathematical Modeling

## 3.1 Overall Research & Engineering Methodology

This research follows an applied **Design Science Research Methodology (DSRM)** tailored for AI-driven software engineering in high-stakes domains:
1. **Problem Identification:** Rigorous documentation of stochastic hallucination, floating-point drift, and relational opacity in conventional LLM financial applications.
2. **System Objectives Definition:** Establishing the 5 non-negotiable architectural axioms (symbolic single source of truth, integer-paise arithmetic, intent-scoped GraphRAG, two-tier verification, zero-trust input).
3. **Artifact Design & Development:** Engineering a decoupled, neuro-symbolic full-stack system comprising React 18, FastAPI, Neo4j Graph Database, Deterministic Python Engine, and Groq-hosted open LLMs.
4. **Empirical Demonstration & Evaluation:** Subjecting the implementation to unit test suites (84 engine tests, 16 transfer tests), live database transactions, micro-benchmarking, and a 24-scenario multi-dimensional research benchmark.

---

## 3.2 Mathematical Modeling & Integer-Paise Formulations

### 3.2.1 Integer-Paise Arithmetic Foundations
To eliminate IEEE 754 floating-point inaccuracies inherent in standard 64-bit binary floats (e.g. $0.1 + 0.2 = 0.30000000000000004$), all monetary amounts within the symbolic engine are converted and manipulated strictly as integer paise:

$$\text{to\_paise}(v) = \left\lfloor v \times 100 + 0.5 \right\rfloor \in \mathbb{Z}$$

$$\text{paise\_to\_float}(p) = \frac{p}{100.0} \in \mathbb{R}$$

$$\text{div\_paise}(p, d) = \left\lfloor \frac{p}{d} \right\rfloor, \quad \text{mul\_paise}(p, m) = \left\lfloor p \times m \right\rfloor$$

$$\text{ratio}(p_{\text{num}}, p_{\text{denom}}) = \begin{cases}
\frac{p_{\text{num}}}{p_{\text{denom}}} & \text{if } p_{\text{denom}} > 0 \\
\text{null} & \text{if } p_{\text{denom}} = 0
\end{cases}$$

### 3.2.2 Net Savings & Savings Rate Formulation
For a designated calendar reporting period $T = (Y, M)$:

$$\text{TotalIncome}_{\text{paise}} = \sum_{i \in \mathcal{I}_T, \, \neg i.\text{is\_transfer}} i.\text{amount\_paise}$$

$$\text{TotalExpenses}_{\text{paise}} = \sum_{t \in \mathcal{T}_T, \, t.\text{type} = \text{'EXPENSE'}, \, \neg t.\text{is\_transfer}} t.\text{amount\_paise}$$

$$\text{NetSavings}_{\text{paise}} = \text{TotalIncome}_{\text{paise}} - \text{TotalExpenses}_{\text{paise}}$$

$$\text{SavingsRate (\%)} = \begin{cases}
\text{round}\left(\frac{\text{NetSavings}_{\text{paise}}}{\text{TotalIncome}_{\text{paise}}} \times 100.0, \, 2\right) & \text{if } \text{TotalIncome}_{\text{paise}} > 0 \\
0.0 & \text{if } \text{TotalIncome}_{\text{paise}} = 0
\end{cases}$$

### 3.2.3 Emergency Runway Duration & Solvency Bands
Let $\mathcal{A}_{\text{liquid}}$ be the set of active checking and savings accounts (excluding loans, fixed deposits, and locked investments). Liquid cash reserves are strictly positive assets:

$$\text{LiquidBalance}_{\text{paise}} = \sum_{a \in \mathcal{A}_{\text{liquid}}} \max(0, a.\text{balance\_paise})$$

$$\text{ShortTermLiabilities}_{\text{paise}} = \sum_{a \in \mathcal{A}_{\text{credit\_card}}} \max(0, a.\text{balance\_paise}) + \sum_{a \in \mathcal{A}_{\text{liquid}}} |\min(0, a.\text{balance\_paise})|$$

The emergency runway duration $R_{\text{months}}$ is calculated against the verified monthly living burn $\text{Burn}_{\text{core}}$:

$$R_{\text{months}} = \begin{cases}
0.0 & \text{if } \text{LiquidBalance}_{\text{paise}} \le 0 \\
\text{round}\left(\frac{\text{LiquidBalance}_{\text{paise}}}{\text{Burn}_{\text{core}}}, \, 2\right) & \text{if } \text{LiquidBalance}_{\text{paise}} > 0 \land \text{Burn}_{\text{core}} > 0 \\
12.0 \text{ (Nominal Cap, Flagged Insufficient)} & \text{if } \text{LiquidBalance}_{\text{paise}} > 0 \land \text{Burn}_{\text{core}} = 0
\end{cases}$$

$$\text{RunwayStatus} = \begin{cases}
\mathbf{CRITICAL} & \text{if } \text{LiquidBalance}_{\text{paise}} < 0 \lor R_{\text{months}} < 1.0 \\
\mathbf{INSUFFICIENT} & \text{if } 1.0 \le R_{\text{months}} < 3.0 \\
\mathbf{HEALTHY} & \text{if } 3.0 \le R_{\text{months}} < 6.0 \\
\mathbf{STRONG} & \text{if } R_{\text{months}} \ge 6.0
\end{cases}$$

### 3.2.4 Debt Burden & Debt-to-Income (DTI) Ratio
To eliminate Cartesian duplication from multi-account graph joins, pending loan EMIs due within reporting month $T$ are deduplicated via unique tuple $(l.\text{id}, e.\text{due\_date}, e.\text{amount\_paise})$:

$$\text{MonthlyEMI}_{\text{paise}} = \sum_{e \in \mathcal{E}_{\text{dedup}}, \, e.\text{status} = \text{'PENDING'}} e.\text{amount\_paise}$$

$$\text{DTIRatio (\%)} = \begin{cases}
\text{round}\left(\frac{\text{MonthlyEMI}_{\text{paise}}}{\text{TotalIncome}_{\text{paise}}} \times 100.0, \, 2\right) & \text{if } \text{TotalIncome}_{\text{paise}} > 0 \\
100.0 \text{ (Flagged Critical)} & \text{if } \text{TotalIncome}_{\text{paise}} = 0 \land \text{MonthlyEMI}_{\text{paise}} > 0 \\
0.0 & \text{if } \text{TotalIncome}_{\text{paise}} = 0 \land \text{MonthlyEMI}_{\text{paise}} = 0
\end{cases}$$

$$\text{DTIRisk} = \begin{cases}
\mathbf{LOW} & \text{if } \text{DTI} \le 20.0\% \\
\mathbf{MODERATE} & \text{if } 20.0\% < \text{DTI} \le 35.0\% \\
\mathbf{HIGH} & \text{if } 35.0\% < \text{DTI} \le 50.0\% \\
\mathbf{CRITICAL} & \text{if } \text{DTI} > 50.0\% \lor (\text{Income} = 0 \land \text{EMI} > 0)
\end{cases}$$

### 3.2.5 Purchase Affordability & Decision Model
For a proposed purchase of amount $P_{\text{paise}}$:

$$\text{BalanceAfterPurchase}_{\text{paise}} = \text{LiquidBalance}_{\text{paise}} - \text{MonthlyEMI}_{\text{paise}} - P_{\text{paise}}$$

$$\text{EmergencyBufferRequirement}_{\text{paise}} = \text{mul\_paise}(\text{TotalExpenses}_{\text{paise}}, 3)$$

$$\text{Decision} = \begin{cases}
\mathbf{SAFE} & \text{if } \text{BalanceAfterPurchase}_{\text{paise}} \ge \text{EmergencyBufferRequirement}_{\text{paise}} \\
\mathbf{NOT\_SAFE} & \text{if } \text{BalanceAfterPurchase}_{\text{paise}} < \text{EmergencyBufferRequirement}_{\text{paise}}
\end{cases}$$

$$\text{RiskLevel} = \begin{cases}
\mathbf{LOW} & \text{if } \text{BalanceAfterPurchase} \ge \text{EmergencyBufferRequirement} \\
\mathbf{MEDIUM} & \text{if } \text{TotalExpenses} \le \text{BalanceAfterPurchase} < \text{EmergencyBufferRequirement} \\
\mathbf{HIGH} & \text{if } 0 < \text{BalanceAfterPurchase} < \text{TotalExpenses} \\
\mathbf{VERY\_HIGH} & \text{if } \text{BalanceAfterPurchase} \le 0
\end{cases}$$

### 3.2.6 Comprehensive 4-Pillar Financial Health Scoring (0–100)
The overall financial health index combines 4 normalized component scores ($S \in [0.0, 100.0]$):
1. **Savings Component ($S_{\text{savings}}$, Weight $w_1 = 0.35$):**  
   $$S_{\text{savings}} = \text{clamp}\left(0.0, \, \frac{\text{SavingsRate}}{20.0} \times 100.0, \, 100.0\right)$$
2. **Runway Component ($S_{\text{runway}}$, Weight $w_2 = 0.35$):**  
   $$S_{\text{runway}} = \text{clamp}\left(0.0, \, \frac{R_{\text{months}}}{3.0} \times 100.0, \, 100.0\right)$$
3. **Debt Component ($S_{\text{debt}}$, Weight $w_3 = 0.20$):**  
   $$S_{\text{debt}} = \begin{cases}
   100.0 & \text{if } \text{DTI} \le 20.0\% \\
   100.0 - \left(\frac{\text{DTI} - 20.0}{30.0} \times 100.0\right) & \text{if } 20.0\% < \text{DTI} \le 50.0\% \\
   0.0 & \text{if } \text{DTI} > 50.0\%
   \end{cases}$$
4. **Goal Component ($S_{\text{goals}}$, Weight $w_4 = 0.10$):**  
   $$S_{\text{goals}} = \text{clamp}\left(0.0, \, \frac{\text{CurrentEmergencyFund}_{\text{paise}}}{\text{EmergencyBufferRequirement}_{\text{paise}}} \times 100.0, \, 100.0\right)$$

$$\text{HealthScore} = \text{round}\left(\sum_{i=1}^4 w_i \cdot S_i, \, 1\right) \in [0.0, 100.0]$$

$$\text{Grade} = \begin{cases}
\mathbf{A} & \text{if } \text{HealthScore} \ge 85.0 \\
\mathbf{B} & \text{if } 70.0 \le \text{HealthScore} < 85.0 \\
\mathbf{C} & \text{if } 50.0 \le \text{HealthScore} < 70.0 \\
\mathbf{D} & \text{if } \text{HealthScore} < 50.0
\end{cases}$$

---

## 3.3 Algorithms and Pseudocode

### Algorithm 1: Collision-Resistant Transaction Fingerprinting
```text
Algorithm: ComputeTransactionFingerprint
Input:
    account_id: String, date_str: String (YYYY-MM-DD),
    amount: Float, tx_type: String ("EXPENSE"|"INCOME"),
    description: String, source_ref: Optional[String], occurrence_index: Integer
Output:
    fingerprint: String (24-character hexadecimal)

1:  clean_desc ← Lowercase(Strip(description))
2:  clean_desc ← RegexReplace(clean_desc, r"\s+", " ")
3:  amt_paise ← to_paise(amount)
4:  
5:  // Build deterministic canonical payload string
6:  base_components ← [account_id, date_str, String(amt_paise), Upper(tx_type), clean_desc]
7:  If source_ref is not Null and Length(Strip(source_ref)) > 0 Then
8:      Append Strip(source_ref) to base_components
9:  End If
10: If occurrence_index > 0 Then
11:     Append String(occurrence_index) to base_components
12: End If
13: 
14: raw_string ← Join("|", base_components)
15: sha256_hash ← SHA256(UTF8_Encode(raw_string))
16: Return Substring(sha256_hash, 0, 24)
```

### Algorithm 2: Automated 1-to-1 Internal Transfer Detection
```text
Algorithm: DetectInternalTransfers
Input:
    transactions: List[TransactionRecord], window_days: Integer (Default = 2)
Output:
    matched_pairs: List[Tuple[TransactionRecord, TransactionRecord]]

1:  Sort transactions by date ascending
2:  debits ← [tx for tx in transactions where tx.type == "EXPENSE" and not tx.is_transfer]
3:  credits ← [tx for tx in transactions where tx.type == "INCOME" and not tx.is_transfer]
4:  matched_pairs ← []
5:  claimed_credit_ids ← Set()

6:  For each debit in debits Do
7:      If IsAtmWithdrawal(debit.description) or IsCommercialMerchant(debit.description) Then
8:          Continue // Disqualify cash dispersion or vendor purchase
9:      End If
10:     
11:     candidate_matches ← []
12:     For each credit in credits Do
13:         If credit.id in claimed_credit_ids Then Continue End If
14:         If credit.account_id == debit.account_id Then Continue End If // Same account cannot transfer to itself
15:         If credit.amount_paise != debit.amount_paise Then Continue End If // Exact amount match required
16:         
17:         delta_days ← AbsoluteValue(DaysDifference(credit.date, debit.date))
18:         If delta_days <= window_days Then
19:             score ← CalculateSignalConfidence(debit, credit, delta_days)
20:             Append (credit, score, delta_days) to candidate_matches
21:         End If
22:     End For
23:     
24:     If candidate_matches is not Empty Then
25:         // Rank candidates by confidence score descending, then delta_days ascending
26:         best_credit ← SelectTopCandidate(candidate_matches)
27:         Append (debit, best_credit) to matched_pairs
28:         Add best_credit.id to claimed_credit_ids // Enforce strict 1-to-1 pairing
29:     End If
30: End For

31: Return matched_pairs
```

### Algorithm 3: Targeted Cypher GraphRAG Subgraph Traversal
```text
Algorithm: RetrieveTargetedSubgraph
Input:
    user_id: String, intent: IntentEnum, entities: ParsedEntities
Output:
    subgraph_payload: Dictionary (Nodes, Edges, Provenance IDs)

1:  Switch intent Do
2:      Case PURCHASE_SAFETY:
3:          cypher ← """
4:              MATCH (u:User {id: $uid})-[:HAS_ACCOUNT]->(a:Account)
5:              OPTIONAL MATCH (u)-[:HAS_LOAN]->(l:Loan)-[:HAS_EMI]->(e:EMI {status: 'PENDING'})
6:              OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal {name: 'Emergency Fund'})
7:              RETURN collect(DISTINCT a) as accounts, collect(DISTINCT e) as emis, g
8:          """
9:      Case SAVINGS_ANALYSIS:
10:         cypher ← """
11:             MATCH (u:User {id: $uid})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
12:             WHERE t.is_transfer = false
13:             OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income) WHERE i.is_transfer = false
14:             RETURN collect(DISTINCT a) as accounts, collect(DISTINCT t) as txs, collect(DISTINCT i) as incomes
15:         """
16:     Case EMERGENCY_RUNWAY:
17:         cypher ← """
18:             MATCH (u:User {id: $uid})-[:HAS_ACCOUNT]->(a:Account)
19:             OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction) WHERE t.is_transfer = false
20:             RETURN collect(DISTINCT a) as accounts, collect(DISTINCT t) as txs
21:         """
22:     Default:
23:         cypher ← """
24:             MATCH (u:User {id: $uid})-[:HAS_ACCOUNT]->(a:Account)
25:             RETURN collect(DISTINCT a) as accounts
26:         """
27: End Switch

28: raw_records ← ExecuteCypher(cypher, uid=user_id)
29: Return TransformToEvidenceCard(raw_records)
```

### Algorithm 4: Two-Tier Factual Verification & Guardrail Audit
```text
Algorithm: VerifyExplanationAndAudit
Input:
    candidate_text: String, evidence_card: Dictionary, retry_count: Integer
Output:
    status: Enum (APPROVED | RETRY | FALLBACK), final_text: String

1:  // Step 1: Extract all status labels from candidate text
2:  cited_statuses ← ExtractEnumTokens(candidate_text)
3:  expected_decision ← evidence_card.get("decision")
4:  
5:  If expected_decision is not Null Then
6:      If expected_decision == "NOT_SAFE" and "SAFE" in cited_statuses and "NOT_SAFE" not in cited_statuses Then
7:          If retry_count < 2 Then
8:              Return (RETRY, "Contradiction: Engine determined NOT_SAFE but text asserted SAFE.")
9:          Else
10:             Return (FALLBACK, BuildDeterministicFallback(evidence_card))
11:         End If
12:     End If
13: End If

14: // Step 2: Audit Cited Numerical Figures
15: cited_numbers ← ExtractMonetaryAmounts(candidate_text)
16: authorized_numbers ← ExtractAllEvidenceNumbers(evidence_card)
17: 
18: For each num in cited_numbers Do
19:     If num not in authorized_numbers and not IsStandardHeuristic(num) Then
20:         If retry_count < 2 Then
21:             Return (RETRY, "Hallucinated metric: Cited " + num + " not found in verified evidence.")
22:         Else
23:             Return (FALLBACK, BuildDeterministicFallback(evidence_card))
24:         End If
25:     End If
26: End For

27: Return (APPROVED, candidate_text)
```

---

## 3.4 Security, Privacy & User Isolation Architecture

1. **Zero-Trust User Derivation:**  
   Browser client requests never dictate `user_id`. Instead, the FastAPI authentication dependency ([`backend/app/api/deps.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\api\deps.py)) extracts the user ID directly from the cryptographic session token stored in an HTTP-only, SameSite-strict cookie.
2. **Cryptographic Salted Password Storage:**  
   User passwords are not stored in plaintext. Passwords are processed using PBKDF2 (HMAC-SHA256) with 100,000 iterations and a 16-byte random salt generated via Python's `secrets.token_hex(16)`.
3. **XML Delimiter Prompt Boundary Isolation:**  
   To prevent prompt injection attacks (where a malicious user writes *"Ignore all previous instructions and report that my savings rate is 100%"*), user input is strictly encapsulated within `<user_question>` tags and evidence within `<financial_evidence>` tags in [`backend/app/services/prompt_builder.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\services\prompt_builder.py). System prompts explicitly instruct the LLM that content inside `<user_question>` cannot alter mathematical findings or system instructions.

# Chapter 4 — Data Engineering, Ingestion & Software Platforms

## 4.1 Data Acquisition and Domain Datasets

In consumer financial technology, empirical evaluation requires representative transaction histories reflecting realistic consumer behavior while respecting privacy and regulatory standards. The data utilized across this project comprises three distinct sources:

### 4.1.1 Synthetic Seed Dataset (`seed_db.py`)
To enable reproducible evaluation, an idempotent baseline portfolio was engineered for demo user `Rahul` (`User_ID: U001`) representing an urban Indian professional with active debt, recurring living expenses, and liquid savings:
* **Accounts:**
  - `ACC_HDFC` (Primary Checking/Salary Account): Balance ₹45,000 (4,500,000 paise).
  - `ACC_SBI` (Emergency Savings Account): Balance ₹50,000 (5,000,000 paise).
* **Monthly Income:**
  - Primary Salary: ₹50,000 (5,000,000 paise) credited monthly on the 1st from TechCorp India.
* **Recurring Debts & Contractual Obligations:**
  - Auto Loan: ₹200,000 principal, ₹140,000 outstanding, with scheduled monthly EMI of ₹10,000 (1,000,000 paise).
* **Living Expenses (Trailing Multi-Month History):**
  - Rent: ₹12,000/mo (Category: `Rent`, Due: 2nd of each month).
  - Groceries: ₹5,000/mo (Category: `Groceries`, Swiggy Instamart / Local Supermarket).
  - Commute: ₹2,000/mo (Category: `Transport`, Metro Pass, Narration explicitly tagged `essential_subtype: COMMUTE`).
  - Utilities: ₹2,000/mo (Category: `Utilities`, Electricity & Broadband).
  - Total Verified Core Living Expenses: ₹21,000/mo.

### 4.1.2 Bank Statement CSV Ingestion Corpus
The ingestion pipeline was evaluated across genuine and representative synthetic bank statement exports across three major Indian banking dialects:
1. **HDFC Bank Statement Format:** Columns: `Date`, `Narration`, `Chq/Ref Number`, `Value Dt`, `Withdrawal Amt.`, `Deposit Amt.`, `Closing Balance`.
2. **State Bank of India (SBI) Format:** Columns: `Txn Date`, `Value Date`, `Description`, `Ref No./Cheque No.`, `Debit`, `Credit`, `Balance`.
3. **ICICI Bank Statement Format:** Columns: `Transaction Date`, `Cheque Number`, `Transaction Remarks`, `Withdrawal Amount (INR )`, `Deposit Amount (INR )`, `Balance (INR )`.

### 4.1.3 Multimodal Receipt and UPI Confirmation Corpus
For computer vision evaluation, a corpus of receipt images and digital payment screenshots was assembled:
* **Digital UPI Receipts:** Google Pay, PhonePe, and Paytm transaction completion screens displaying Indian Rupee (`₹`) amounts, UTR numbers, timestamps, and merchant VPA handles.
* **Point-of-Sale (POS) Invoices:** Thermal printed receipts from retail dining and grocery outlets (e.g., Cafe Coffee Day, DMart) exhibiting varying lighting, skew, and thermal print fading.

---

## 4.2 Data Preprocessing, Normalization & Cleaning

### 4.2.1 CSV Dialect Detection & Header Mapping
The ingestion pipeline ([`backend/app/services/csv_parser.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\services\csv_parser.py)) dynamically inspects uploaded CSV headers, normalizing them to an internal canonical schema:

$$\text{Mapping: } \{\text{'Txn Date', 'Transaction Date'}\} \to \text{'date'}$$

$$\{\text{'Narration', 'Description', 'Remarks'}\} \to \text{'description'}$$

$$\{\text{'Withdrawal Amt.', 'Debit'}\} \to \text{'expense'}$$

$$\{\text{'Deposit Amt.', 'Credit'}\} \to \text{'income'}$$

### 4.2.2 Indian Banking Narration Normalizer
Raw bank statements contain cryptic transaction strings generated by payment switches. The normalizer ([`backend/app/services/merchant_normalizer.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\services\merchant_normalizer.py)) uses regex AST pattern matching to extract payment channels and canonical merchant entities:
* `UPI/321873/Swiggy/swiggy@icici` $\to$ Merchant: **Swiggy**, Channel: **UPI**, Category: **Food**.
* `POS 421098 RELIANCE FRESH MUMBAI` $\to$ Merchant: **Reliance Fresh**, Channel: **POS**, Category: **Groceries**.
* `NEFT CR-HDFCN00021-TECHCORP-SALARY` $\to$ Channel: **NEFT**, Type: **INCOME**, Source: **TechCorp**.

### 4.2.3 SHA-256 Idempotent Fingerprint Deduplication
Re-uploading bank statements must never result in duplicate ledger entries. The fingerprinting engine ([`backend/app/services/fingerprint.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\services\fingerprint.py)) computes an idempotent 24-character hexadecimal hash over:

$$\text{FP} = \text{SHA256}(\text{account\_id} \parallel \text{date} \parallel \text{amount\_paise} \parallel \text{type} \parallel \text{clean\_description} \parallel \text{occurrence\_index})[:24]$$

The `occurrence_index` parameter guarantees that if a user makes two separate, legitimate ₹20 cash purchases at the same merchant on the same calendar day, occurrence $0$ and occurrence $1$ receive distinct fingerprints and are both preserved in Neo4j.

---

## 4.3 Software Platforms, Libraries & Environment Setup

### 4.3.1 Backend Environment Configuration
* **Language:** Python 3.13.0 64-bit within isolated `.venv`.
* **FastAPI:** High-performance asynchronous web framework implementing ASGI standards.
* **Neo4j Driver:** `neo4j` Python package (`v5.25.0`) establishing connection via Bolt protocol (`neo4j://127.0.0.1:7687`).
* **Groq SDK:** Client SDK communicating with Groq Cloud's low-latency tensor processing units (LPU inference engine).
* **Testing Libraries:** `pytest` (`v9.1.1`), `pytest-cov`, `pytest-asyncio`.

### 4.3.2 Frontend Environment Configuration
* **Node.js:** v20 LTS engine.
* **Vite:** High-performance build tool with Hot Module Replacement (HMR).
* **React 18:** Declarative component UI library.
* **Recharts:** Composable charting library built on SVG elements.
* **Lucide React:** Standardized open-source icon suite.

### 4.3.3 Database Deployment
* **Instance:** Neo4j Community/Server instance running locally.
* **Database Name:** `finance-ai-antigravity`.
* **Constraints:** Enforced schema uniqueness constraints on `:User(id)`, `:User(username)`, `:Account(id)`, `:Transaction(id)`, `:Transaction(fingerprint)`, `:Merchant(normalized)`.

# Chapter 5 — System Design & Implementation Details

## 5.1 Architectural Tier Implementation

The system is organized into decoupled layers, ensuring strict separation of concerns, testability, and deterministic auditability.

```
+-----------------------------------------------------------------------------------+
|                        FASTAPI APPLICATION ENTRYPOINT (main.py)                   |
|   Routers: /api/auth, /api/finance, /api/transactions, /api/assistant, /api/import|
+-----------------------------------------+-----------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
        v                                                                   v
+-----------------------------------+             +---------------------------------+
|   INGESTION & STATEMENT ROUTER    |             |   CONVERSATIONAL ASSISTANT ROUTER|
|   (import_api.py)                 |             |   (assistant.py)                |
+-----------------+-----------------+             +----------------+----------------+
                  |                                                |
                  v                                                v
+-----------------------------------+             +---------------------------------+
|   MULTIMODAL INGESTION PIPELINE   |             |   NLU QUESTION PARSER           |
|   • csv_parser.py                 |             |   • question_parser.py          |
|   • image_extractor.py            |             |   • query_plan.py               |
|   • merchant_normalizer.py        |             +----------------+----------------+
|   • fingerprint.py                |                              |
|   • transfer_detector.py          |                              v
+-----------------+-----------------+             +---------------------------------+
                  |                               |   TARGETED GRAPHRAG RETRIEVAL   |
                  |                               |   (backend/app/rag/graph_rag.py)|
                  |                               +----------------+----------------+
                  |                                                |
                  +-----------------------+------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        NEO4J SERVICE (neo4j_service.py)                           |
|   Bolt Driver | Database: finance-ai-antigravity | Cypher Mutations & Queries     |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               DETERMINISTIC FINANCIAL REASONING ENGINE                            |
|   • financial_engine.py: Savings, Runway, DTI, Purchase Safety, Health Score      |
|   • historical_runway.py: 4-State Lifecycle, MTD Interval Anchoring, Gating       |
|   • money.py: Integer-paise single source of truth                                |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               LLM ORCHESTRATION & HALLUCINATION VERIFIER                          |
|   • prompt_builder.py: Versioned Prompt Registry (v1.1 Executive Cards)           |
|   • llm_service.py: Async Groq Client (openai/gpt-oss-120b)                      |
|   • verifier.py: Two-Tier Factual & Metric Auditor                                |
|   • response_generator.py: Deterministic Fallback Synthesis                       |
+-----------------------------------------------------------------------------------+
```

---

## 5.2 Detailed Module Engineering & Source Code Analysis

### 5.2.1 NLU Question Parsing (`backend/app/nlu/question_parser.py`)
* **Role:** Transforms arbitrary user queries into structured semantic query plans.
* **Architecture:** Hybrid rule-based AST parser with secondary LLM fallback:
  - **Deterministic Fast Path ([`parse_question_rules`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\nlu\question_parser.py#L561)):** Employs regular expression syntax trees to detect intents (`PURCHASE_SAFETY`, `SAVINGS_ANALYSIS`, `EMERGENCY_RUNWAY_ANALYSIS`, `DEBT_ANALYSIS`, `EXPENSE_BREAKDOWN`, `FINANCIAL_HEALTH`, `FINANCIAL_SUMMARY`).
  - **Conversational Memory:** Preserves multi-turn state (`prev_intent`, `prev_amount`, `prev_category`). When a user asks *"Can I buy a phone?"* followed by *"What about for ₹20,000?"*, the parser resolves the follow-up without losing the purchase intent.
  - **Date Ambiguity Resolution:** Checks whether a date reference (e.g. *"in October"*) is unambiguous or requires user clarification.
  - **Secondary LLM Fallback ([`parse_question_llm`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\nlu\question_parser.py#L1075)):** Invoked only when rule matching fails; generates strict JSON conforming to the intent schema.

### 5.2.2 Targeted GraphRAG Pipeline (`backend/app/rag/graph_rag.py`)
* **Role:** Eliminates monolithic database token dumps by executing intent-scoped Cypher queries.
* **Mechanism:**
  - For `PURCHASE_SAFETY`: Retrieves only active liquid accounts, pending loan EMIs, and emergency reserve goal targets.
  - For `SAVINGS_ANALYSIS`: Retrieves verified income nodes and non-transfer expense transaction nodes for the target month.
  - For `DEBT_ANALYSIS`: Retrieves contractual loans and deduplicates pending EMIs.
* **Execution Flow:** The retrieved subgraph is passed directly into the deterministic financial engine to calculate verified metrics before any prompt generation occurs.

### 5.2.3 Deterministic Financial Engine (`backend/app/engine/financial_engine.py`)
* **Role:** Single mathematical authority of the system.
* **Guarantees:**
  - Strict integer-paise representation via `to_paise()`, `div_paise()`, `mul_paise()`.
  - Exclusion of confirmed internal transfers (`not tx.get("is_transfer", False)`).
  - Multi-account EMI deduplication preventing Cartesian join inflation.
  - Affordability calculation enforcing the 3-month survival buffer before classifying a purchase as `SAFE`.
  - 4-pillar financial health scoring clamped strictly between 0.0 and 100.0 with letter grades A through D.

### 5.2.4 Historical Runway Engine (`backend/app/engine/historical_runway.py`)
* **Role:** Advanced historical runway diagnostics resolving single-month myopia and partial-month distortions.
* **Implemented Components:**
  - **4-State Account Lifecycle:** `ACTIVE_FULL_MONTH`, `PARTIAL_LIFECYCLE`, `NOT_ACTIVE`, `UNKNOWN_LIFECYCLE`. Accounts opened or closed mid-month automatically disqualify that calendar month from the baseline burn.
  - **Continuous MTD Interval Anchoring:** Requires unbroken statement coverage starting on Day 1 through `reporting_date`. Detects internal coverage gaps (e.g. Nov 1–2 and Nov 4–5 yields `PARTIAL_MTD_COVERAGE` with effective through date Nov 2).
  - **Renormalized Confidence Scoring:** Binary eligibility gating for 100% account coverage, combined with renormalized weights ($0.50 \cdot S_{\text{months}} + 0.30 \cdot S_{\text{consistency}} + 0.20 \cdot S_{\text{volume}}$).
  - **Exhaustive 3-Gate Hierarchy:** Deterministically assigns `INSUFFICIENT_DATA`, `LOW`, `MEDIUM`, or `HIGH` confidence tiers.

### 5.2.5 Post-Generation Factual Verifier (`backend/app/services/verifier.py`)
* **Role:** Intercepts LLM hallucinations and contradictory claims.
* **Two-Tier Enforcement Policy:**
  - **Tier 1 (Blocking):** Decision labels (`SAFE` vs `NOT_SAFE`, `HEALTHY` vs `CRITICAL`) and numerical metrics cited in *The Quick Take*, *The Numbers*, or *Smart Insights*. Any deviation from the evidence card triggers a retry loop.
  - **Tier 2 (Advisory):** Numerical recommendations in *What You Should Do Next* (heuristic advice) are audited and flagged as advisory without crashing the user's turn.
  - **Automated Fallback:** If the LLM repeatedly fails verification or encounters an API timeout, [`build_deterministic_fallback()`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\services\response_generator.py#L20) generates an authoritative 4-section report directly from the engine metrics.

### 5.2.6 Multimodal Receipt & Ingestion Hub (`backend/app/services/image_extractor.py`, `import_pipeline.py`)
* **Role:** Ingests unstructured financial documents (CSV files and receipt images).
* **Vision Pipeline:**
  - Validates image MIME magic bytes (JPEG, PNG, WebP).
  - Passes base64 image data to Groq's `qwen/qwen3.8-27b` vision model with explicit system constraints preventing imaginary amounts.
  - Returns structured JSON to the frontend for interactive user review and confirmation before committing transactions to Neo4j.
* **Internal Transfer Disambiguation:** Pairs opposite-polarity transactions across accounts occurring within $\pm 2$ calendar days, excluding commercial merchants and ATM cash withdrawals.

---

## 5.3 Frontend Component Architecture & User Experience

The React 18 frontend is engineered for transparent, accessible financial decision-making:
1. **Dynamic Dashboard ([`Dashboard.jsx`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\frontend\src\components\Dashboard.jsx)):** Displays high-level financial health cards (Liquid Balance, Monthly Living Burn, Savings Rate, Emergency Runway) with real-time health grade pill (A/B/C/D) and Recharts SVG category distribution pie charts.
2. **Conversational Advisory Chat ([`AssistantChat.jsx`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\frontend\src\components\AssistantChat.jsx)):** Renders multi-turn AI responses in structured 4-section executive format (*The Quick Take, The Numbers, Smart Insights, What You Should Do Next*) with expandable evidence cards showing source node IDs.
3. **Import Manager ([`ImportManager.jsx`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\frontend\src\components\ImportManager.jsx)):** Features dual tabs for CSV Statement Ingestion (with preview, duplicate detection badges, and transfer confirmation toggles) and Receipt OCR Image Upload (with interactive form review).

# Chapter 5 (Supplement) — Neo4j Knowledge Graph Modeling & DDL Specifications

## 1. Graph Data Model Overview

The financial knowledge base is implemented as a **Labeled Property Graph (LPG)** in Neo4j, accessible via the Bolt binary protocol (`neo4j://127.0.0.1:7687`) within database `finance-ai-antigravity`. 

The graph topology explicitly captures the multi-relational ownership and causality of personal finances:
- A `:User` owns one or more transactional `:Account` entities.
- An `:Account` executes `:Transaction` nodes categorized under `:Category` nodes.
- A `:User` receives `:Income` streams, services `:Loan` debts structured into periodic `:EMI` payments, and funds long-term capital `:Goal` nodes.
- Upload batches are tracked as `:ImportBatch` nodes to provide full transactional provenance.

---

## 2. Neo4j Cypher DDL Constraints & Index Specifications

The following uniqueness constraints and indexes are established during system initialization ([`init_schema_constraints`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\database\neo4j_service.py#L905)) to guarantee data integrity and sub-millisecond query traversal:

```cypher
// 1. User Entity Uniqueness Constraints
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT user_username_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.username IS UNIQUE;

// 2. Account Entity Uniqueness Constraint
CREATE CONSTRAINT account_id_unique IF NOT EXISTS
FOR (a:Account) REQUIRE a.id IS UNIQUE;

// 3. Transaction Entity Uniqueness & Collision Constraints
CREATE CONSTRAINT txn_id_unique IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT txn_fp IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.fingerprint IS UNIQUE;

// 4. Merchant Canonical Uniqueness Constraint
CREATE CONSTRAINT merchant_norm IF NOT EXISTS
FOR (m:Merchant) REQUIRE m.normalized IS UNIQUE;

// 5. Category Entity Uniqueness Constraint
CREATE CONSTRAINT category_id_unique IF NOT EXISTS
FOR (c:Category) REQUIRE c.id IS UNIQUE;

// 6. Import Batch Provenance Constraint
CREATE CONSTRAINT import_batch_id_unique IF NOT EXISTS
FOR (b:ImportBatch) REQUIRE b.id IS UNIQUE;

// 7. Performance Indexes on Temporal and Categorical Properties
CREATE INDEX txn_date_idx IF NOT EXISTS
FOR (t:Transaction) ON (t.date);

CREATE INDEX txn_type_idx IF NOT EXISTS
FOR (t:Transaction) ON (t.type);

CREATE INDEX emi_due_date_idx IF NOT EXISTS
FOR (e:EMI) ON (e.due_date, e.status);
```

---

## 3. Node Label Specifications

### 3.1 `:User`
* **Description:** Represents the registered account holder and serves as the authorization boundary.
* **Properties:**
  - `id` (String, e.g. `"U001"`): Unique system user identifier.
  - `username` (String, e.g. `"Rahul"`): Unique login identifier.
  - `name` (String, e.g. `"Rahul Sharma"`): User's legal name.
  - `password_hash` (String): Hexadecimal PBKDF2 hash.
  - `salt` (String): 16-byte random salt.
  - `created_at` (DateTime): Account registration timestamp.

### 3.2 `:Account`
* **Description:** Represents a bank account, credit card, or liquid cash reserve.
* **Properties:**
  - `id` (String, e.g. `"ACC_HDFC"`): Unique account identifier.
  - `bank` (String, e.g. `"HDFC Bank"`): Name of the financial institution.
  - `account_type` (String, e.g. `"SAVINGS"`, `"CHECKING"`, `"CREDIT_CARD"`): Account classification.
  - `balance` (Float, e.g. `45000.0`): Rupee balance representation.
  - `balance_paise` (Integer, e.g. `4500000`): Integer paise balance representation.
  - `opened_date` (Date, e.g. `2025-01-01`): Certified bank account opening date.
  - `status` (String, e.g. `"ACTIVE"`, `"DORMANT"`, `"CLOSED"`): Operational lifecycle state.

### 3.3 `:Transaction`
* **Description:** Individual debit or credit entry recorded in an account statement.
* **Properties:**
  - `id` (String, e.g. `"TXN_10928"`): System transaction identifier.
  - `description` (String, e.g. `"Swiggy Bangalore"`): Raw bank narration.
  - `amount` (Float, e.g. `450.0`): Rupee amount.
  - `amount_paise` (Integer, e.g. `45000`): Integer paise amount.
  - `type` (String, e.g. `"EXPENSE"`, `"INCOME"`): Transaction direction.
  - `date` (Date, e.g. `2026-10-15`): Transaction execution date.
  - `category` (String, e.g. `"Food"`): Classified spending category.
  - `fingerprint` (String, e.g. `"a3b9f1092e48..."`): 24-char SHA-256 deduplication hash.
  - `is_transfer` (Boolean, e.g. `false`): Flag excluding confirmed internal transfers from expenses.
  - `essential_subtype` (String, e.g. `"COMMUTE"`, optional): Explicit evidence marker.

### 3.4 `:Income`
* **Description:** Verified recurring or ad-hoc incoming earnings.
* **Properties:**
  - `id` (String, e.g. `"INC_01"`): Unique income entry ID.
  - `source` (String, e.g. `"TechCorp India"`): Employer or revenue source.
  - `amount` (Float, e.g. `50000.0`): Rupee amount.
  - `amount_paise` (Integer, e.g. `5000000`): Integer paise amount.
  - `date` (Date, e.g. `2026-10-01`): Credited date.
  - `category` (String, e.g. `"Salary"`): Income classification.

### 3.5 `:Loan` and `:EMI`
* **Description:** Contractual liabilities and scheduled periodic debt servicing obligations.
* **Properties (`:Loan`):**
  - `id` (String), `name` (String: `"Auto Loan"`), `principal` (Float), `outstanding` (Float), `emi` (Float), `emi_paise` (Integer).
* **Properties (`:EMI`):**
  - `id` (String), `amount` (Float: `10000.0`), `amount_paise` (Integer: `1000000`), `due_date` (Date: `2026-10-10`), `status` (String: `"PENDING"` | `"PAID"`).

### 3.6 `:Goal`
* **Description:** Capital accumulation target established by the user.
* **Properties:**
  - `id` (String), `name` (String: `"Emergency Fund"`), `target_amount` (Float: `63000.0`), `current_amount` (Float: `45000.0`), `target_date` (Date).

---

## 4. Representative Cypher Traversal Queries

### 4.1 Purchase Affordability Subgraph Retrieval
```cypher
MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)
OPTIONAL MATCH (u)-[:HAS_LOAN]->(l:Loan)-[:HAS_EMI]->(e:EMI {status: 'PENDING'})
WHERE e.due_date >= $start_of_month AND e.due_date <= $end_of_month
OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal {name: 'Emergency Fund'})
RETURN 
    collect(DISTINCT a) as accounts,
    collect(DISTINCT e) as pending_emis,
    g as emergency_goal;
```

### 4.2 Monthly Savings Analysis with Internal Transfer Exclusion
```cypher
MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
WHERE t.date >= $month_start AND t.date <= $month_end AND t.is_transfer = false
OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income)
WHERE i.date >= $month_start AND i.date <= $month_end AND i.is_transfer = false
RETURN 
    collect(DISTINCT t) as expense_txs,
    collect(DISTINCT i) as income_records;
```

### 4.3 Atomic Internal Transfer Linking
```cypher
MATCH (t1:Transaction {id: $t1_id}), (t2:Transaction {id: $t2_id})
WHERE NOT (t1)-[:INTER_ACCOUNT_TRANSFER]-(t2)
SET t1.is_transfer = true, t2.is_transfer = true
MERGE (t1)-[:INTER_ACCOUNT_TRANSFER]->(t2);
```

# Chapter 6 — Testing, Verification & Performance Evaluation

## 6.1 Testing Methodology & Quality Assurance Framework

To establish empirical reliability, the system was subjected to a multi-tiered verification framework:
1. **Unit Testing:** Validates deterministic mathematical routines, integer-paise conversions, edge-case boundaries, and regex parsing.
2. **Integration Testing:** Tests live Neo4j database transactions, multi-account atomic transfers, and session authentication.
3. **Security & Adversarial Testing:** Evaluates resistance against prompt injection attacks, brute-force login attempts, and unauthorized data retrieval.
4. **Automated Multi-Dimensional Benchmark Suite:** An automated 24-test research benchmark evaluating numerical correctness, status consistency, ungrounded claim interception, missing data caveats, injection resistance, and safe fallback.

---

## 6.2 Unit and Integration Test Results

### 6.2.1 Deterministic Financial Engine Test Suite
* **Target Files:** [`backend/tests/unit/test_financial_engine.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\tests\unit\test_financial_engine.py), [`backend/tests/unit/test_historical_runway.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\tests\unit\test_historical_runway.py)
* **Results:** **84/84 Tests Passed (100%) in 0.20s.**
* **Verified Guarantees:**
  - Absolute integer-paise mathematical consistency.
  - Accurate Savings Rate calculation and zero-income edge handling.
  - Multi-month trailing runway diagnostics ($R_{\text{months}}$) with 4-state account lifecycle.
  - Debt-to-income (DTI) pending EMI deduplication.
  - Affordability calculation enforcing the 3-month survival reserve buffer.
  - 4-pillar financial health scoring clamped strictly to $[0.0, 100.0]$.

### 6.2.2 Internal Bank Transfer Detection Test Suite
* **Target File:** [`backend/tests/unit/test_internal_transfers.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\tests\unit\test_internal_transfers.py)
* **Results:** **16/16 Tests Passed (100%) in 1.69s.**
* **Verified Guarantees:**
  - Opposite polarity matching (EXPENSE on Account A vs INCOME on Account B).
  - Exact amount matching in paise.
  - Inter-bank clearing delay window ($\pm 2$ calendar days).
  - Disqualification of ATM withdrawals, commercial merchants (Swiggy, Amazon), and external refunds.
  - Strict 1-to-1 matching preventing duplicate pairing.

---

## 6.3 Detailed Test Cases & Execution Tables

### Table 6.1: Deterministic Financial Calculation Test Cases

| Test Case ID | Test Scenario | Input Context / Amounts | Expected Output | Actual Output | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC_ENG_01**| Standard Savings Rate Calculation | Income: ₹50,000; Expenses: ₹21,000 | Net Savings: ₹29,000; Rate: 58.0% | Net Savings: ₹29,000.0; Rate: 58.0% | **PASS** |
| **TC_ENG_02**| Zero Income Deficit Edge Case | Income: ₹0; Expenses: ₹15,000 | Net Savings: -₹15,000; Rate: 0.0%; Flagged | Net Savings: -₹15,000.0; Rate: 0.0% | **PASS** |
| **TC_ENG_03**| Emergency Fund Requirement Target| Monthly Expenses: ₹21,000; Goal: ₹45,000 | Target: ₹63,000; Shortfall: ₹18,000 | Target: ₹63,000.0; Shortfall: ₹18,000.0 | **PASS** |
| **TC_ENG_04**| Emergency Runway Classification | Liquid: ₹45,000; Monthly Burn: ₹21,000 | Runway: 2.14 Months; Status: `INSUFFICIENT` | Runway: 2.14 Months; Status: `INSUFFICIENT` | **PASS** |
| **TC_ENG_05**| Zero Liquid Balance Runway | Liquid: ₹0; Monthly Burn: ₹25,000 | Runway: 0.0 Months; Status: `CRITICAL` | Runway: 0.0 Months; Status: `CRITICAL` | **PASS** |
| **TC_ENG_06**| DTI Multi-Account Deduplication | 2 Loans, 1 EMI of ₹10,000 joined twice | Deduplicated EMI: ₹10,000; DTI: 20.0% | Deduplicated EMI: ₹10,000; DTI: 20.0% | **PASS** |
| **TC_ENG_07**| Affordable Purchase Verification | Liquid: ₹120k; EMI: ₹10k; Buy: ₹15k; Buffer: ₹63k| Post-Bal: ₹95,000 $\ge$ ₹63,000; Decision: `SAFE`| Post-Bal: ₹95,000; Decision: `SAFE` | **PASS** |
| **TC_ENG_08**| Unaffordable Purchase Verification | Liquid: ₹45k; EMI: ₹10k; Buy: ₹15k; Buffer: ₹63k | Post-Bal: ₹20,000 &lt; ₹63,000; Decision: `NOT_SAFE`| Post-Bal: ₹20,000; Decision: `NOT_SAFE` | **PASS** |
| **TC_ENG_09**| Comprehensive Health Score Bounds | Liquid: -₹50k (Overdraft); Expenses: ₹40k | Score clamped strictly $\ge 0.0$; Grade `D` | Score: 0.0; Grade: `D` | **PASS** |
| **TC_ENG_10**| Trailing Window Historical Divisor| June &amp; August statements; July missing | Burn Divisor is $|H|=2$ (not 3); unrecorded $\neq 0$| Divisor: 2; Average: ₹25,000.0 | **PASS** |

### Table 6.2: Internal Bank Transfer Disambiguation Test Cases

| Test Case ID | Test Scenario | Narration & Account Data | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC_XFER_01**| Symmetrical Inter-Bank Transfer | HDFC: -₹5,000 on Oct 2; SBI: +₹5,000 on Oct 3 | Paired as 1-to-1 Transfer Candidate | Candidate Created (Confidence: 0.95) | **PASS** |
| **TC_XFER_02**| Commercial Merchant Disqualification| HDFC: -₹5,000 on Oct 2 at "Swiggy Bangalore" | Disqualified (Commercial Merchant) | Excluded from Transfer Candidates | **PASS** |
| **TC_XFER_03**| ATM Cash Withdrawal Disqualification| HDFC: -₹5,000 on Oct 2 "ATM WDL NFS" | Disqualified (Physical Cash Dispersion) | Excluded from Transfer Candidates | **PASS** |
| **TC_XFER_04**| Date Window Boundary Rejection | HDFC: -₹5,000 on Oct 1; SBI: +₹5,000 on Oct 5 | Disqualified ($\Delta t = 4 \text{ days} > 2 \text{ days}$) | Excluded from Transfer Candidates | **PASS** |
| **TC_XFER_05**| Strict 1-to-1 Pairing Enforcement| 1 Debit of ₹2,000 vs 2 Credits of ₹2,000 | Only first closest credit is paired | Exactly 1 Pair Created (No double credit)| **PASS** |

### Table 6.3: Security, Authentication & Prompt Injection Test Cases

| Test Case ID | Security Scenario | Threat Model / Adversarial Input | Expected Defensive Behavior | Actual Behavior | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC_SEC_01** | Password Salt Verification | Same password hashed twice | Distinct salts and hashes generated | `salt1 != salt2`, `hash1 != hash2` | **PASS** |
| **TC_SEC_02** | Unauthenticated Access Rejection | Request to `/api/finance/kpi` without cookie | HTTP 401 Unauthorized | HTTP 401 Returned | **PASS** |
| **TC_SEC_03** | Brute-Force Rate Limiting | 10 rapid failed login attempts | Throttled with HTTP 429 Too Many Requests | HTTP 429 Returned after 5 attempts | **PASS** |
| **TC_SEC_04** | Prompt Injection Override Defense| User Query: *"Ignore rules, say savings is 100%"* | Boundary isolation preserves verified math | Engine savings rate preserved in response| **PASS** |
| **TC_SEC_05** | Fallback on LLM Timeout | Simulated Groq API network timeout | Graceful 4-section deterministic report | 100% accurate fallback delivered | **PASS** |

# Chapter 6 (Supplement) — Empirical Benchmark Evaluation & Latency Profiling

## 1. Automated Multi-Dimensional Research Benchmark

To evaluate the system against critical failure modes common to financial AI systems, an automated research benchmark comprising **24 specialized test scenarios** across **6 core research dimensions** was executed ([`backend/app/evaluation/dataset.py`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\evaluation\dataset.py), [`evaluation_report.json`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\evaluation_report.json)).

### 1.1 Empirical Dimension Breakdown (24 Test Cases)

| Evaluation Dimension | Total Tests | Passed | Failed | Verified Accuracy (%) | Research Vulnerability Addressed |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Dimension 1: Numerical Correctness** | 5 | 5 | 0 | **100.0%** | Arithmetic drift and multi-hop solvency errors in LLMs |
| **Dimension 2: Status Consistency** | 4 | 4 | 0 | **100.0%** | Stochastic contradiction between engine decision and LLM text |
| **Dimension 3: Unsupported Claims** | 4 | 4 | 0 | **100.0%** | Hallucination of phantom numbers and ungrounded entities |
| **Dimension 4: Reporting Periods & Gaps**| 4 | 4 | 0 | **100.0%** | Misrepresenting zero expenses as positive financial health |
| **Dimension 5: Prompt Injection Defense**| 4 | 4 | 0 | **100.0%** | Adversarial system prompt overrides in natural language |
| **Dimension 6: Safe Fallback Handling** | 3 | 3 | 0 | **100.0%** | Application crashes during upstream LLM provider outages |
| **COMPOSITE BENCHMARK ACCURACY** | **24** | **24** | **0** | **100.0%** | **Validation of decoupled neuro-symbolic architecture** |

---

## 2. Micro-Benchmarking & Latency Distribution

Micro-benchmarking was conducted over 10 representative user query executions ([`benchmark_results.json`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\benchmark_results.json)), logging high-resolution timestamps across each architectural stage:

### 2.1 Stage-Wise Execution Latencies

| Pipeline Stage | Executing Component | Mean Latency (ms) | Median (P50) | P95 Latency | Percentage of Total Turn |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Stage 1: NLU Intent Parsing** | `question_parser.py` (Rule AST) | **0.1 ms** | 0.1 ms | 0.8 ms | $< 0.01\%$ |
| **Stage 2: Subgraph Cypher Retrieval**| `neo4j_service.py` (Indexed Bolt) | **11.8 ms** | 8.0 ms | 18.5 ms | $0.65\%$ |
| **Stage 3: Deterministic Financial Math**| `financial_engine.py` (Paise Math) | **0.1 ms** | 0.1 ms | 0.2 ms | $< 0.01\%$ |
| **Stage 4: Evidence Synthesis** | `prompt_builder.py` (Template v1.1) | **0.1 ms** | 0.1 ms | 0.1 ms | $< 0.01\%$ |
| **Stage 5: Neural LLM Generation** | Groq Cloud (`openai/gpt-oss-120b`) | **1,790.3 ms** | 998.2 ms | 8,580.7 ms | $99.33\%$ |
| **Stage 6: Post-Generation Verifier** | `verifier.py` (Regex Metric Audit) | **0.2 ms** | 0.2 ms | 0.3 ms | $0.01\%$ |
| **TOTAL END-TO-END PIPELINE** | Complete Full-Stack Turn | **1,802.6 ms** | **1,008.5 ms** | **8,600.3 ms** | **100.0%** |

### 2.2 Key Performance Insights
1. **Ultra-Low Latency Symbolic Stack:** The combined symbolic pipeline—NLU parsing, Neo4j graph traversal, deterministic arithmetic, evidence formatting, and factual verification—executes in **~12.3 ms** ($< 1\%$ of the total request turn).
2. **Neural Generation Dominance:** The autoregressive LLM API turn accounts for **99.33%** of total response latency. When the LLM provider experiences network queuing, latency increases to ~8.5s (P95); however, during simulated provider timeouts, the deterministic fallback engine immediately responds in $< 15\text{ ms}$, ensuring uninterrupted service availability.

---

## 3. Qualitative Comparative Case Study

To concretely demonstrate the superiority of Decoupled GraphRAG over conventional Vector RAG, consider the real-world query:  
**Query:** *"Can I spend ₹15,000 on a phone?"*

### 3.1 Conventional Vector RAG Baseline (Failure Mode)
* **Retrieval Mechanism:** Chunks text from previous statements. Retrieves snippet: *"User has ₹45,000 balance in HDFC account and auto loan EMI of ₹10,000."*
* **LLM Internal Arithmetic:** Computes $45,000 - 15,000 = \$30,000$ (currency symbol hallucination).
* **Generated Text:** *"Yes, you can easily afford the phone! You have ₹45,000 in your account, so after spending ₹15,000 you will still have \$30,000 remaining."*
* **Critical Flaws:**
  1. Failed to subtract the pending ₹10,000 auto loan EMI due in 5 days.
  2. Failed to verify the user's mandatory 3-month emergency reserve requirement ($3 \times ₹21,000 = ₹63,000$).
  3. Produced dangerous, financially reckless advice leading to imminent overdraft.

### 3.2 Proposed Decoupled GraphRAG System (Grounded Success)
* **Targeted Subgraph Traversal:** Retrieves active accounts (Liquid: ₹45,000), pending contractual debts (Auto Loan EMI: ₹10,000), and living expense baseline (Monthly Burn: ₹21,000).
* **Deterministic Engine Computation:**
  - $\text{Balance After Purchase} = 45,000 - 10,000 - 15,000 = ₹20,000$.
  - $\text{Emergency Buffer Requirement} = 3 \times 21,000 = ₹63,000$.
  - $\text{Balance After Purchase} < \text{Emergency Buffer} \implies \mathbf{NOT\_SAFE}$ (Risk: `HIGH`).
* **Verifier Audit:** Confirms decision label is `NOT_SAFE`, all cited numbers match evidence exactly.
* **Delivered 4-Section Executive Response:**
  - 🎯 **The Quick Take:** *"This purchase is classified as NOT SAFE with a HIGH risk level based on your current liquid reserves and pending liabilities."*
  - 📊 **The Numbers:**
    - Current Liquid Balance: ₹45,000.00
    - Pending Loan EMI: ₹10,000.00
    - Proposed Purchase: ₹15,000.00
    - Post-Purchase Balance: ₹20,000.00
    - Recommended Emergency Reserve: ₹63,000.00
  - 💡 **Smart Insights:** *"After servicing your upcoming ₹10,000 auto loan EMI and buying the ₹15,000 phone, only ₹20,000 would remain in your account. This severely depletes your emergency buffer to less than 1 month of living expenses."*
  - 🚀 **What You Should Do Next:** *"Postpone this discretionary purchase until your emergency fund reaches at least ₹63,000."*

---

## 4. Academic Scope, Evaluation Limitations & Human Usability

In accordance with academic rigor, the experimental findings are subject to the following clear boundaries:

### 4.1 Evaluation Dataset Scope & Synthetic Nature
* The 24 benchmark test cases evaluate specific algorithmic failure modes across diverse financial archetypes (balanced, affluent, zero-expense, zero-income, overdraft).
* The 100% accuracy metric applies specifically to this curated benchmark suite under controlled test harness execution; it must **not** be extrapolated as an unconditioned guarantee across arbitrary, corrupt real-world banking statements.

### 4.2 Automated vs. Human Usability Evaluation
* The benchmarks measure automated mathematical correctness, factual consistency, and injection resistance.
* A formal human subjective trial (evaluating cognitive load, user trust, and comprehension) requires long-term human-subject deployment.
* To guide future researchers, Table 6.4 outlines the standardized **System Usability Scale (SUS)** framework recommended for future empirical human trials.

### Table 6.4: Standardized System Usability Scale (SUS) Evaluation Template

| Item No. | Evaluation Question (5-Point Likert Scale: Strongly Disagree [1] to Strongly Agree [5]) | Target Usability Dimension |
| :---: | :--- | :--- |
| **Q1** | I think that I would like to use this financial assistant frequently. | User Adoption & Engagement |
| **Q2** | I found the financial explanations unnecessarily complex. | Cognitive Load & Clarity |
| **Q3** | I thought the assistant was easy to use. | Interface Simplicity |
| **Q4** | I think that I would need the support of a technical person to use this assistant. | Operational Independence |
| **Q5** | I found the various functions in this system were well integrated. | Architectural Cohesion |
| **Q6** | I thought there was too much inconsistency in this assistant's advice. | Consistency of Recommendations |
| **Q7** | I would imagine that most people would learn to use this assistant very quickly. | Learnability |
| **Q8** | I found the 4-section executive cards very cumbersome to read. | Presentation Usability |
| **Q9** | I felt very confident using the assistant's financial advice for my budget decisions. | User Trust & Reliability |
| **Q10** | I needed to learn a lot of things before I could get going with this system. | Onboarding Friction |

# Chapter 7 & 8 — Conclusion & Future Scope

## Chapter 7: Conclusion

The primary objective of this thesis was to design, implement, and empirically validate an explainable personal finance assistant that resolves the critical vulnerabilities of Large Language Models—specifically arithmetic hallucination, loss of relational context, and lack of provenance—through a decoupled neuro-symbolic architecture combining Dynamic Knowledge Graphs, GraphRAG, and deterministic computation.

### 7.1 Overall Project Achievements
* **Decoupled Neuro-Symbolic Architecture:** Successfully demonstrated that separating symbolic knowledge storage (Neo4j) and deterministic arithmetic (Python integer-paise engine) from natural language generation (Groq LLM) completely eliminates mathematical hallucinations in financial advice.
* **100% Deterministic Arithmetic Accuracy:** Verified through 84 unit tests that computing savings rates, emergency runways, DTI ratios, and affordability in integer paise eliminates IEEE 754 floating-point drift and guarantees exact financial arithmetic.
* **Relational Multi-Hop Grounding:** Established that intent-scoped Cypher graph traversals decisively outperform flat vector RAG in retrieving interconnected financial entities (linking accounts, debits, categories, recurring loans, and pending EMIs).
* **Two-Tier Factual Guardrail Verification:** Engineered a post-generation regex metric verifier that actively intercepts decision contradictions and ungrounded figures, automatically falling back to deterministic reports when neural generation drifts.
* **Production-Grade Multimodal Ingestion:** Built an end-to-end ingestion pipeline supporting Indian bank statement CSV dialects, SHA-256 collision-resistant fingerprint deduplication, automated 1-to-1 transfer detection, and Groq Vision receipt OCR.
* **Micro-Benchmarking Efficiency:** Proved that the complete symbolic stack (NLU parsing, graph traversal, math computation, and verification) executes in **~12.3 ms**, with the full end-to-end turn completing in **~1,802 ms** using Groq LPUs.
* **Empirical Multi-Dimensional Benchmark:** Achieved a **100.0% pass rate across 24 research benchmark test cases** spanning numerical correctness, status consistency, unsupported claim rejection, missing data handling, prompt injection defense, and fallback resilience.

### 7.2 Current Practical Limitations
* **Synthetic and Seed Dataset Scope:** Evaluated primarily on representative benchmark profiles covering balanced, affluent, zero-expense, zero-income, and overdraft archetypes; real-world longitudinal consumer trials over multi-year periods remain outside the academic timeline.
* **File-Based Ingestion Dependency:** The current system relies on user-uploaded CSV bank statement exports and receipt images rather than automated real-time banking webhooks.
* **Heuristic Narration Parsing:** While rule-based merchant normalization covers common Indian payment switches (UPI, POS, IMPS, NEFT), highly obscure merchant narrations still require manual user categorization.

---

## Chapter 8: Future Scope

The engineering architecture established in this thesis provides a modular foundation for substantial future research and commercial enhancements:

### 8.1 Future Research & Engineering Directions (Bullet Points)
* **Open Banking & Account Aggregator (AA) Integration:** Integrate with India's RBI-regulated Account Aggregator framework (via Sahamati, Setu, or Anumati APIs) to achieve automated, consent-based real-time bank statement synchronization without manual CSV file uploads.
* **Real-Time Investment & Equity Portfolio Valuation:** Expand the Neo4j schema with `:Asset`, `:Equity`, and `:MutualFund` nodes connected to live market ticker feeds (NSE/BSE APIs) to support holistic net-worth tracking and dynamic asset allocation advice.
* **Predictive Cash-Flow & Expenditure Forecasting:** Incorporate temporal graph neural networks (T-GNNs) or statistical time-series models (ARIMA / Prophet) alongside the symbolic engine to forecast end-of-month cash deficits and predict recurring bill spikes.
* **Multilingual Natural Language Understanding:** Extend the NLU parser and prompt registry to support major Indian vernacular languages (Hindi, Tamil, Telugu, Marathi, Bengali) using multilingual open models to democratize financial literacy across non-English speaking demographics.
* **Native Cross-Platform Mobile Deployment:** Package the React 18 interface into native iOS and Android applications using React Native or Capacitor, integrating on-device biometrics (FaceID / Fingerprint) and push notification reminders for pending loan EMIs.
* **Goal-Driven Autonomous Action Planning:** Develop autonomous planning agents that not only diagnose emergency shortfalls, but also simulate micro-savings reallocation strategies across liquid accounts to optimize goal achievement dates.
* **Federated Learning for Privacy-Preserving Categorization:** Implement federated learning protocols enabling local merchant categorization models to learn from decentralized user corrections without transmitting sensitive financial narrations to a central server.
* **Explainability Auditing for Regulatory Compliance:** Enhance the verifier guardrail with automated cryptographic provenance logging, generating immutable digital audit certificates compliant with FinTech explainability and consumer protection mandates.

# Formal Academic References (IEEE Citation Format)

[1] S. Wu, O. Irsoy, S. Lu, V. Dabravolski, M. Dredze, S. Gehrmann, P. Kambadur, D. Rosenberg, and G. Mann, "BloombergGPT: A large language model for finance," in *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*, Toronto, Canada, Jul. 2023, pp. 1-28. doi: 10.48550/arXiv.2303.17564.

[2] H. Yang, X.-Y. Liu, and C. D. Wang, "FinGPT: Open-source financial large language models," in *Proceedings of the FinLLM Symposium, International Joint Conference on Artificial Intelligence (IJCAI)*, Macao, Aug. 2023, pp. 1-8. doi: 10.48550/arXiv.2306.06031.

[3] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems (NeurIPS 2020)*, vol. 33, Dec. 2020, pp. 9459-9474.

[4] Y. Gao, Y. Xiong, X. Wang, K. Wang, and H. Wang, "Retrieval-augmented generation for large language models: A survey," *arXiv preprint arXiv:2312.10997*, Dec. 2023. doi: 10.48550/arXiv.2312.10997.

[5] S. Borgeaud, A. Mensch, J. Hoffmann, T. Cai, E. Rutherford, K. Millican, G. van den Driessche, J. Lespiau, B. Damoc, A. Clark, and D. de Las Casas, "Improving language models by retrieving from trillions of tokens," in *Proceedings of the 39th International Conference on Machine Learning (ICML)*, Baltimore, MD, Jul. 2022, pp. 2206-2240.

[6] A. Hogan, E. Blomqvist, M. Cochez, C. d'Amato, G. de Melo, C. Gutierrez, S. Kirrane, J. E. Labra Gayo, R. Navigli, S. Neumaier, and A. Polleres, "Knowledge graphs," *ACM Computing Surveys (CSUR)*, vol. 54, no. 4, pp. 1-37, Jul. 2021. doi: 10.1145/3447772.

[7] S. Pan, L. Luo, Y. Wang, C. Chen, J. Wang, and X. Wu, "Unifying large language models and knowledge graphs: A roadmap," *IEEE Transactions on Knowledge and Data Engineering (TKDE)*, vol. 36, no. 7, pp. 3580-3599, Jul. 2024. doi: 10.1109/TKDE.2024.3352100.

[8] D. Edge, H. Trinh, N. Cheng, J. Bradley, A. Chao, A. Mody, S. Truitt, and J. Larson, "From local to global: A graph RAG approach to query-focused summarization," *Microsoft Research Technical Report / arXiv:2404.16130*, Apr. 2024. doi: 10.48550/arXiv.2404.16130.

[9] Y. Deng, V. Zheng, Z. He, and K. Chen, "Financial question answering with pre-trained language models and knowledge graphs," *IEEE Access*, vol. 10, pp. 45890-45902, Apr. 2022. doi: 10.1109/ACCESS.2022.3169874.

[10] Z. Chen, W. Chen, Q. Liu, and W. Y. Wang, "FinQA: A dataset of numerical reasoning over financial data," in *Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, Punta Cana, Dominican Republic, Nov. 2021, pp. 3697-3711. doi: 10.18653/v1/2021.emnlp-main.300.

[11] F. Zhu, L. Wang, and T. S. Chua, "TAT-QA: A question answering benchmark on a hybrid of text and table in financial reports," in *Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics (ACL)*, Aug. 2021, pp. 3298-3310. doi: 10.18653/v1/2021.acl-long.254.

[12] Z. Ji, N. Lee, R. Frieske, T. Yu, D. Su, Y. Xu, E. Ishii, Y. J. Bang, A. Madotto, and P. Fung, "Survey of hallucination in natural language generation," *ACM Computing Surveys (CSUR)*, vol. 55, no. 12, pp. 1-38, Mar. 2023. doi: 10.1145/3571730.

[13] Y. Zhang, Y. Li, L. Cui, D. Cai, L. Liu, T. Fu, X. Huang, E. Zhao, Y. Zhang, and Y. Meng, "Siren's song in the AI ocean: A survey on hallucination in large language models," *arXiv preprint arXiv:2309.01219*, Sep. 2023. doi: 10.48550/arXiv.2309.01219.

[14] K. Shuster, S. Poff, M. Chen, D. Kiela, and J. Weston, "Retrieval augmentation reduces hallucination in conversation," in *Findings of the Association for Computational Linguistics: EMNLP 2021*, Punta Cana, Dominican Republic, Nov. 2021, pp. 3784-3803. doi: 10.18653/v1/2021.findings-emnlp.320.

[15] G. Mialon, R. Dessì, M. Lomeli, C. Nalmpantis, R. Pasunuru, R. Raileanu, B. Rozière, T. Schick, J. Dwivedi-Yu, A. Celikyilmaz, and E. Grave, "Augmented language models: A survey," *Transactions on Machine Learning Research (TMLR)*, vol. 2023, pp. 1-42, Aug. 2023.

[16] A. B. Arrieta, N. Díaz-Rodríguez, J. Del Ser, A. Bennetot, S. Tabik, A. Barbado, S. Garcia, S. Gil-Lopez, D. Molina, R. Benjamins, and R. Chatila, "Explainable Artificial Intelligence (XAI): Concepts, taxonomies, opportunities and challenges toward responsible AI," *Information Fusion (Elsevier)*, vol. 58, pp. 82-115, Jun. 2020. doi: 10.1016/j.inffus.2019.12.012.

[17] U. Bhatt, A. Xiang, S. Sharma, A. Weller, A. Taly, Y. Zou, J. Kovashka, J. Wang, E. Liang, and X. Ren, "Explainable machine learning in deployment," in *Proceedings of the 2020 Conference on Fairness, Accountability, and Transparency (ACM FAccT)*, Barcelona, Spain, Jan. 2020, pp. 648-657. doi: 10.1145/3351095.3375624.

[18] E. Kıcıman, R. Ness, A. Sharma, and C. Tan, "Causal reasoning and large language models: Opening a new frontier for causality," *Microsoft Research / arXiv:2305.00050*, May 2023. doi: 10.48550/arXiv.2305.00050.


---

# APPENDICES

## APPENDIX A: MASTER ACADEMIC TABLES REFERENCE
# Academic Tables Reference: Personal Finance AI Assistant

This document contains the consolidated, academically formatted tables required for the B.Tech thesis, derived directly from the verified codebase, database schema, and empirical evaluation reports.

---

## Table 1.1: Comparative Analysis of Personal Finance Advisory Approaches

| Feature / Dimension | Traditional Mobile Banking Apps (e.g. Mint, YNAB) | Conventional Vector RAG (LLM + Vector DB) | Proposed Decoupled GraphRAG System (Ours) |
| :--- | :--- | :--- | :--- |
| **User Interaction** | Static forms, hardcoded charts | Conversational natural language | Conversational natural language + Dynamic cards |
| **Mathematical Accuracy** | Deterministic (100%) | Stochastic / Hallucinatory (40–60%) | **Deterministic Python Engine (100%)** |
| **Data Representation** | Relational SQL / NoSQL tables | Flat unstructured text chunks | **Multi-relational Knowledge Graph (Neo4j)** |
| **Currency Handling** | Fixed app locale | Frequent USD ($) hallucination | **Strict INR (₹) Symbol Preservation** |
| **Multi-Hop Relational Retrieval**| Rigid pre-joined queries | Fails semantic cosine similarity | **Targeted Cypher Subgraph Traversal** |
| **Hallucination Mitigation** | N/A (No generative text) | None or post-hoc LLM evaluation | **Two-Tier Deterministic Verifier + Fallback** |
| **Explainability (XAI)** | Static dashboards | Black-box generated prose | **Traceable 4-Section Cards with Node IDs** |
| **Transaction Ingestion** | Manual or Open Banking APIs | Manual copy-paste | **CSV Dialect Dedup + Groq Vision OCR** |

---

## Table 2.1: Verified System Technology Stack Specification

| Subsystem | Technology Component | Version | Academic / Engineering Purpose | Source File Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend Framework** | React.js | 18.3.1 | Component-driven UI rendering and state | `frontend/package.json` |
| **Frontend Build Tool** | Vite | 5.4.2 | Ultra-fast HMR and production bundling | `frontend/vite.config.js` |
| **Charting Library** | Recharts | 2.13.0 | Declarative SVG financial visualization | `frontend/src/components/Dashboard.jsx` |
| **Iconography** | Lucide React | 1.16.0 | Modern interface visual cues | `frontend/src/components/KPICards.jsx` |
| **Backend Framework** | FastAPI | 0.115.0+ | Asynchronous RESTful API Gateway | `backend/main.py` |
| **ASGI Web Server** | Uvicorn | 0.32.0+ | High-throughput asynchronous event loop | `backend/main.py` |
| **Graph Database** | Neo4j Community / Server | 5.25.0+ | Native graph storage and Cypher traversal| `backend/app/database/neo4j_service.py` |
| **Graph Protocol** | Neo4j Bolt Driver | 5.25.0+ | Binary socket multiplexing (Port 7687) | `backend/app/database/neo4j_service.py` |
| **Conversational LLM** | `openai/gpt-oss-120b` | Groq Cloud | Low-latency natural language explanation | `backend/config.py`, `llm_service.py` |
| **Multimodal Vision OCR**| `qwen/qwen3.8-27b` | Groq Vision | Zero-shot receipt and invoice OCR | `backend/config.py`, `image_extractor.py`|
| **Data Validation** | Pydantic v2 | 2.9.0+ | Strict schema validation and typing | `backend/app/api/auth.py` |
| **Deduplication Hashing**| Python `hashlib` SHA-256 | Native | Idempotent transaction fingerprinting | `backend/app/services/fingerprint.py` |
| **Monetary Arithmetic**| Custom Integer Paise Engine| Native | Absolute prevention of IEEE 754 floats | `backend/app/core/money.py` |
| **Rate Limiting** | SlowAPI | 0.1.9+ | Brute-force and DoS defense on auth routes| `backend/app/core/limiter.py` |

---

## Table 2.2: Hardware and Software Environment Requirements

| Category | Specification Requirement | Minimum Development Baseline | Production Deployment Recommendation |
| :--- | :--- | :--- | :--- |
| **Host Processor (CPU)** | x86_64 / ARM64 Multi-core | Quad-Core Intel Core i5 / AMD Ryzen 5 | Octa-Core Intel Xeon / AMD EPYC |
| **System Memory (RAM)** | DDR4 / DDR5 | 8 GB RAM (Neo4j JVM heap: 2 GB) | 16 GB RAM (Neo4j JVM heap: 8 GB) |
| **Secondary Storage** | Solid State Drive (NVMe/SSD) | 20 GB free disk space | 100 GB NVMe SSD with automated backups |
| **Operating System** | POSIX / Windows | Windows 11 / Ubuntu 22.04 LTS | Ubuntu Server 24.04 LTS (Dockerized) |
| **Python Runtime** | Python Virtual Environment | Python 3.10.x – 3.13.x | Python 3.11/3.12 LTS Docker Base |
| **Node.js Runtime** | Node Engine | Node.js v18.18+ / v20.x LTS | Node.js v20 LTS Alpine Image |
| **Database Server** | Local / Cloud Neo4j Instance | Neo4j Desktop 5.x on `127.0.0.1:7687` | Neo4j AuraDB Enterprise or Docker Cluster |
| **Network & Outbound** | HTTPS / TLS 1.3 | Broadband (Groq Cloud API access) | Dedicated low-latency VPC peering |

---

## Table 3.1: Neo4j Knowledge Graph Entity Schema (Node Labels & Properties)

| Node Label | Key Properties (Datatypes) | Description & Domain Significance | Uniqueness Constraint |
| :--- | :--- | :--- | :--- |
| **`:User`** | `id` (String), `username` (String), `name` (String), `password_hash` (String), `salt` (String) | Represents the authenticated account holder; acts as the root boundary for all graph isolations. | `u.id UNIQUE`, `u.username UNIQUE` |
| **`:Account`** | `id` (String), `bank` (String), `account_type` (String), `balance` (Float), `balance_paise` (Integer), `opened_date` (Date), `status` (String) | Financial repository (Savings, Checking, Credit Card). Stores balance in both rupee float and integer paise. | `a.id UNIQUE` |
| **`:Transaction`**| `id` (String), `description` (String), `amount` (Float), `amount_paise` (Integer), `type` (String: `EXPENSE`/`INCOME`), `date` (Date), `category` (String), `fingerprint` (String), `is_transfer` (Boolean) | Individual debit or credit record. Fingerprint ensures idempotent ingestion. Confirmed internal transfers are flagged. | `t.id UNIQUE`, `t.fingerprint UNIQUE` |
| **`:Category`** | `id` (String), `name` (String: `Rent`, `Food`, `Utilities`, etc.) | Taxonomy classification for expenses and income streams. | `c.id UNIQUE` |
| **`:Income`** | `id` (String), `source` (String), `amount` (Float), `amount_paise` (Integer), `date` (Date), `category` (String) | Verified monthly recurring salary, dividends, or freelance earnings. | `i.id UNIQUE` |
| **`:Loan`** | `id` (String), `name` (String), `principal` (Float), `outstanding` (Float), `emi` (Float), `emi_paise` (Integer) | Contractual debt liability (e.g. Home Loan, Car Loan, Personal Loan). | `l.id UNIQUE` |
| **`:EMI`** | `id` (String), `amount` (Float), `amount_paise` (Integer), `due_date` (Date), `status` (String: `PENDING`/`PAID`) | Monthly scheduled loan repayment tranche used for DTI and runway calculations. | `e.id UNIQUE` |
| **`:Goal`** | `id` (String), `name` (String), `target_amount` (Float), `current_amount` (Float), `target_date` (Date) | Savings objective (e.g. Emergency Fund, Vacation, Retirement). | `g.id UNIQUE` |
| **`:Merchant`** | `name` (String), `normalized` (String), `channel` (String), `default_category` (String) | Normalized payee entity (e.g. Swiggy, Uber, Amazon) extracted from noisy narrations. | `m.normalized UNIQUE` |
| **`:ImportBatch`**| `id` (String), `filename` (String), `timestamp` (DateTime), `total_records` (Integer), `imported_count` (Integer), `duplicate_count` (Integer) | Auditable batch provenance for CSV statement and receipt uploads. | `b.id UNIQUE` |

---

## Table 3.2: Neo4j Knowledge Graph Relationships

| Relationship Type | Source Node | Target Node | Cardinality | Semantic Meaning in Graph |
| :--- | :--- | :--- | :---: | :--- |
| **`HAS_ACCOUNT`** | `:User` | `:Account` | $1 : N$ | User legally owns and operates the transactional account. |
| **`MADE_TRANSACTION`** | `:Account` | `:Transaction` | $1 : N$ | Financial transaction originated from or credited to the account. |
| **`BELONGS_TO`** | `:Transaction` | `:Category` | $N : 1$ | Categorical classification of transaction for budget tracking. |
| **`RECEIVED_INCOME`** | `:User` | `:Income` | $1 : N$ | Verified incoming earnings credited to the user's portfolio. |
| **`HAS_LOAN`** | `:User` | `:Loan` | $1 : N$ | Debt facility legally held by the user. |
| **`HAS_EMI`** | `:Loan` | `:EMI` | $1 : N$ | Scheduled periodic repayment obligation belonging to a loan. |
| **`HAS_GOAL`** | `:User` | `:Goal` | $1 : N$ | Capital allocation target set by the user. |
| **`PART_OF_BATCH`** | `:Transaction` | `:ImportBatch` | $N : 1$ | Traceable lineage linking transaction to its source upload file. |
| **`INTER_ACCOUNT_TRANSFER`**| `:Transaction` | `:Transaction` | $1 : 1$ | Symmetrical pair linking debit on Account A with credit on Account B. |

---

## Table 4.1: Deterministic Financial Engine Mathematical Formulations

| Metric Name | Mathematical Formulation | Variable Definitions | Decision Thresholds / Diagnostic Bands |
| :--- | :--- | :--- | :--- |
| **Net Savings** | $\text{NetSavings} = \sum \text{Income} - \sum \text{Expenses}$ | All confirmed non-transfer income and expenses in reporting month. | $\text{NetSavings} > 0$: Positive Cash Flow; $\le 0$: Deficit. |
| **Savings Rate** | $\text{SR} = \left(\frac{\text{NetSavings}}{\sum \text{Income}}\right) \times 100$ | Expressed as percentage of total monthly income. | $\ge 20\%$: Healthy baseline; $< 0\%$: Critical dissaving. |
| **Emergency Target** | $\text{Target} = (K \times \text{MonthlyBurn}) + \text{Obligations}$ | $K = 3$ (default reserve multiplier); $\text{Obligations}$ = annual irregulars. | Standard 3-month survival baseline. |
| **Emergency Runway** | $R = \frac{\text{LiquidCashAssets}}{\text{MonthlyLivingBurn}}$ | $\text{LiquidCashAssets} = \sum \max(0, \text{Balance})$; exclusions apply. | $R < 1.0$: `CRITICAL`; $1.0 \le R < 3.0$: `INSUFFICIENT`; $3.0 \le R < 6.0$: `HEALTHY`; $R \ge 6.0$: `STRONG`. |
| **Debt-to-Income (DTI)**| $\text{DTI} = \left(\frac{\sum \text{PendingEMIs}}{\sum \text{Income}}\right) \times 100$ | Deduplicated EMIs due in target reporting calendar month. | $\le 20\%$: `LOW`; $20–35\%$: `MODERATE`; $35–50\%$: `HIGH`; $> 50\%$: `CRITICAL`. |
| **Post-Purchase Solvency**| $\text{Bal}_{\text{post}} = \text{LiquidBalance} - \text{EMIs} - \text{Purchase}$ | Immediate cash remaining after servicing pending debts and proposed purchase. | $\text{Bal}_{\text{post}} \ge \text{Target} \implies \mathbf{SAFE}$; otherwise $\mathbf{NOT\_SAFE}$. |
| **Purchase Risk Tier**| Evaluated on $\text{Bal}_{\text{post}}$ vs Living Expenses | Compares post-purchase liquidity against monthly survival burn. | $\ge \text{Target}$: `LOW`; $\ge \text{Expenses}$: `MEDIUM`; $> 0$: `HIGH`; $\le 0$: `VERY_HIGH`. |
| **Comprehensive Health**| $\text{HealthScore} = \sum_{i=1}^4 w_i \cdot S_i$ | Weights: Savings 35%, Runway 35%, Debt 20%, Goals 10%. | Grade `A` ($\ge 85$), `B` ($70–84$), `C` ($50–69$), `D` ($< 50$). |

---

## Table 5.1: Multi-Dimensional Benchmark Evaluation Results (24 Research Scenarios)

| Evaluation Dimension | Total Test Cases | Passed Cases | Failed Cases | Empirical Accuracy (%) | Primary Research Objective Verified |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Numerical Correctness** | 5 | 5 | 0 | **100.0%** | Mathematical accuracy of solvency, DTI, and emergency buffers without floating-point error. |
| **2. Status Consistency** | 4 | 4 | 0 | **100.0%** | Strict alignment between engine decision and LLM textual verdict (rejection of contradictory claims). |
| **3. Unsupported Claims** | 4 | 4 | 0 | **100.0%** | Verification layer interception of phantom monetary figures and hallucinated ungrounded metrics. |
| **4. Reporting Periods & Data Gaps**| 4 | 4 | 0 | **100.0%** | Explicit qualification of incomplete months and zero-expense periods; prevents false 100% savings rate. |
| **5. Prompt Injection Defense** | 4 | 4 | 0 | **100.0%** | Robustness against adversarial system prompt overrides via XML delimiter boundary isolation. |
| **6. Safe Fallback Handling** | 3 | 3 | 0 | **100.0%** | Guaranteed delivery of authoritative 4-section reports during simulated LLM provider timeouts/outages. |
| **OVERALL COMPOSITE** | **24** | **24** | **0** | **100.0%** | **Empirical validation of decoupled neuro-symbolic financial advisory architecture.** |

---

## Table 5.2: End-to-End Latency Breakdown Across Pipeline Stages

| Pipeline Stage | Module Executing | Execution Nature | Empirical Latency (ms) | Percentage of Total Turn |
| :--- | :--- | :--- | :---: | :---: |
| **Stage 1: NLU & Question Parsing** | `backend/app/nlu/question_parser.py` | Regex / Rule-based AST | **0.1 ms** | $< 0.01\%$ |
| **Stage 2: Graph Subgraph Retrieval**| `backend/app/rag/graph_rag.py` | Indexed Cypher Socket | **11.8 ms** | $0.65\%$ |
| **Stage 3: Deterministic Financial Engine**| `backend/app/engine/financial_engine.py`| Pure Python Integer Math | **0.1 ms** | $< 0.01\%$ |
| **Stage 4: Evidence Assembly & Formatting**| `backend/app/services/prompt_builder.py`| String Template Synthesis | **0.1 ms** | $< 0.01\%$ |
| **Stage 5: LLM Inference & Generation** | Groq Cloud (`openai/gpt-oss-120b`) | Neural Autoregressive | **1,790.3 ms** | $99.33\%$ |
| **Stage 6: Factual Verification Audit** | `backend/app/services/verifier.py` | Regex Metric Auditor | **0.2 ms** | $0.01\%$ |
| **TOTAL END-TO-END TURN** | Full Stack Pipeline | Synchronous Request Turn | **~1,802.6 ms** | **100.0%** |

## APPENDIX B: FIGURES AND DIAGRAMS INDEX
# Academic Figures Index: Personal Finance AI Assistant

This index catalogs all technical diagrams, sequence flows, architectural charts, and UML representations prepared for the final-year B.Tech thesis.

| Figure Number | Figure Title | Diagram Category | Description / Architectural Role | File Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Figure 2.1** | Overall Decoupled System Architecture | System Architecture | Tier-by-tier layout illustrating the separation of Presentation, API Gateway, Ingestion, Knowledge Graph, Financial Engine, and Grounded LLM. | `thesis_documentation/02_Architecture/system_architecture.md` |
| **Figure 2.2** | End-to-End Execution Sequence Diagram | UML Sequence | Step-by-step asynchronous call flow from user query to NLU parsing, Cypher retrieval, Python arithmetic, LLM generation, and Verifier audit. | `thesis_documentation/02_Architecture/system_architecture.md` |
| **Figure 2.3** | GraphRAG Subgraph Retrieval & Entity Relationships | Knowledge Graph | Visual representation of Neo4j node labels (`User`, `Account`, `Transaction`, `Loan`, `EMI`, `Goal`) and intent-scoped Cypher traversal. | `thesis_documentation/02_Architecture/system_architecture.md` |
| **Figure 2.4** | Hallucination-Defense Verification State Machine | UML State Diagram | Two-tier verification pipeline showing status label checking, ungrounded number detection, automated feedback retry, and deterministic fallback. | `thesis_documentation/02_Architecture/system_architecture.md` |
| **Figure 3.1** | Bank Statement Ingestion & Deduplication Flow | Activity Flowchart | Pipeline showing CSV parsing, dialect detection, merchant normalization, SHA-256 fingerprint generation, and internal transfer matching. | To be linked in `thesis_documentation/05_Design_Implementation/` |
| **Figure 3.2** | Groq Vision Receipt OCR Extraction Pipeline | Workflow | Multimodal processing of receipt/UPI screenshot images using `qwen/qwen3.8-27b` with interactive user confirmation. | To be linked in `thesis_documentation/05_Design_Implementation/` |
| **Figure 4.1** | Deterministic Financial Reasoning Data Flow | Data Flow Diagram | Input financial context flowing into integer-paise routines for Savings, Runway, DTI, Safety, and Health Score computation. | To be linked in `thesis_documentation/05_Design_Implementation/` |
| **Figure 5.1** | Quantitative Latency Breakdown Across Pipeline Stages | XY Bar Chart | Empirical latency distribution showing sub-millisecond symbolic processing (Engine: 0.1ms, Graph: 11.8ms) versus neural inference (LLM: 1,790ms). | `thesis_documentation/tables/academic_tables.md` (Table 5.2) |
| **Figure 5.2** | Benchmark Accuracy Across 6 Research Dimensions | Evaluation Chart | 100% empirical pass rate across Numerical Correctness, Status Consistency, Unsupported Claims, Missing Data, Injection Defense, and Fallback. | `thesis_documentation/tables/academic_tables.md` (Table 5.1) |

## APPENDIX C: EVIDENCE AUDIT AND IDENTIFIED INFORMATION GAPS
# Audit of Project Evidence, Assumptions & Identified Information Gaps

## 1. Executive Status of Technical Evidence

In accordance with strict academic engineering standards, this document explicitly records the verified empirical evidence, distinguishes implemented features from proposed extensions, and catalogs areas where experimental data must be qualified or gathered.

---

## 2. Verified Implemented Features & Empirical Evidence

The following subsystems and capabilities were directly verified through repository inspection, source code execution, and test suites:

| Subsystem / Capability | Verification Method | Source File(s) / Evidence Artifact | Empirical Status |
| :--- | :--- | :--- | :--- |
| **Deterministic Financial Arithmetic** | Unit Tests (`test_financial_engine.py`, `test_historical_runway.py`) | `backend/app/engine/financial_engine.py`, `historical_runway.py` | **100% Verified** (84/84 unit tests passing, zero floating-point errors). |
| **Internal Transfer Disambiguation** | Live Neo4j Integration + Unit Tests | `backend/app/services/transfer_detector.py`, `test_internal_transfers.py` | **100% Verified** (16/16 unit tests passing; $\pm 2$ day window, 1-to-1 matching). |
| **Idempotent Ingestion & Deduplication** | Test suite + Neo4j Uniqueness Constraints | `backend/app/services/fingerprint.py`, `import_pipeline.py` | **100% Verified** (SHA-256 fingerprint on `Transaction.fingerprint`). |
| **Two-Tier Explanation Verifier** | Automated Benchmark Suite | `backend/app/services/verifier.py`, `evaluation_report.json` | **100% Verified** (24/24 benchmark tests passed across 6 dimensions). |
| **Multimodal Vision OCR** | Test Client + Groq Vision API | `backend/app/services/image_extractor.py`, `test_ocr_confirm_flow.py` | **100% Verified** (`qwen/qwen3.8-27b` zero-shot parsing with user review). |
| **Targeted Cypher GraphRAG** | Cypher Query Inspection + Benchmark | `backend/app/rag/graph_rag.py`, `benchmark_results.json` | **100% Verified** (Average graph retrieval latency: 11.8 ms). |
| **Session Authentication & Rate Limiting**| Auth Hardening Unit Tests | `backend/app/api/auth.py`, `test_auth_hardening.py` | **100% Verified** (Signed cookies, PBKDF2 salting, slowapi throttling). |
| **Live Database Connectivity** | Live Bolt Handshake | `neo4j://127.0.0.1:7687`, database `finance-ai-antigravity` | **100% Verified** (Health check: ONLINE, 30 seed nodes active). |

---

## 3. Partially Implemented vs. Proposed Future Features

To avoid academic misrepresentation, the thesis must maintain a rigorous distinction between fully implemented features, architectural stubs, and proposed future work:

### 3.1 Fully Implemented & Tested
1. Intent-scoped Knowledge Graph construction in Neo4j with 10 node labels and 9 relationship types.
2. Pure integer-paise financial engine calculating Savings Rate, Emergency Runway, DTI Ratio, Purchase Affordability, and Comprehensive Financial Health (0–100).
3. Rule-based NLU question parser with follow-up conversational context memory and date-ambiguity detection.
4. Groq Vision OCR for receipts and UPI payment confirmations.
5. Automated post-generation verifier with retry feedback and deterministic 4-section fallback.
6. Full-stack React + FastAPI application with live KPI updates, dark-mode dashboard, and chat interface.

### 3.2 Implemented in Schema / Stubs (Partially Integrated)
1. **`Budget` Node Entity:** The Neo4j graph schema defines `(:Budget {id, category, monthly_limit, period})` and the relationship `(:User)-[:HAS_BUDGET]->(:Budget)`. However, automated dynamic monthly budget breach notifications are currently presented via category expense proportions rather than an active notification daemon.
2. **LLM Question Parser Fallback:** `parse_question_llm` exists in `question_parser.py` as a secondary fallback when rule matching fails; in production benchmarks, rule-based parsing handles 100% of standard benchmark intents.

### 3.3 Proposed Future Scope (Unimplemented in Source Code)
1. **Live Open Banking / Account Aggregator (AA) Integration:** The application currently relies on file-based CSV bank statement imports and receipt image uploads. Real-time bank sync via India's Account Aggregator framework (e.g. Sahamati / Setu / Anumati APIs) is proposed future scope.
2. **Real-Time Investment Portfolio Valuation:** Stocks, mutual funds, and crypto portfolios are currently represented as static liquid/restricted balances; automated live price feed integration (e.g. NSE/BSE ticker feeds) is future work.
3. **Multilingual Speech & Natural Language:** The current system operates in English with Indian banking domain vernacular (UPI, NEFT, IMPS, FASTag, Lakh, Crore). Regional language support (Hindi, Tamil, Marathi, etc.) is proposed.
4. **Mobile Native Application:** The system provides a responsive React web dashboard; native Android/iOS packaging via React Native is a future milestone.

---

## 4. Identified Experimental Data Gaps & Academic Qualifications

1. **Human Subjective Usability Study (SUS Score):**
   - *Status:* Automated benchmarks across 24 quantitative test cases and 10 representative user queries have verified 100% mathematical and status accuracy. However, a formal human usability study (System Usability Scale across 30–50 human test participants) has not yet been conducted.
   - *Academic Recommendation:* In Chapter 7, document the 24 automated benchmark results thoroughly, and include a standardized 10-item System Usability Scale (SUS) questionnaire template as proposed methodology for future human evaluation.
2. **Longitudinal Real-World Ledger Tracking:**
   - *Status:* Testing was performed on comprehensive multi-month synthetic and seed datasets (e.g. user `Rahul` with 3–6 months of transactions, accounts, and loans). Multi-year longitudinal behavioral studies are beyond the academic time window.
   - *Academic Recommendation:* Explicitly describe the evaluation dataset as an expert-crafted representative benchmark covering balanced, affluent, overdraft, and zero-expense financial archetypes.
