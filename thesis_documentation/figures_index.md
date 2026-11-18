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

