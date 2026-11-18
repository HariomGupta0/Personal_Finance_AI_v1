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

