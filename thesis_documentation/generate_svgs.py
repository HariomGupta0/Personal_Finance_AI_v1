"""
Generates clean, professional academic SVG diagrams for the B.Tech Thesis.
Saves standalone SVG files into thesis_documentation/diagrams/
"""
import os

BASE_DIR = r"C:\Users\gupta\Documents\HARIOM\Personal_Finance_AI_FYP\thesis_documentation\diagrams"

def save_svg(subfolder, filename, content):
    folder_path = os.path.join(BASE_DIR, subfolder)
    os.makedirs(folder_path, exist_ok=True)
    full_path = os.path.join(folder_path, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"Generated: {full_path}")

# -------------------------------------------------------------
# 1. Overall System Architecture SVG
# -------------------------------------------------------------
svg_arch = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 700" width="100%" height="100%">
  <defs>
    <style>
      .title { font-family: 'Segoe UI', Arial, sans-serif; font-size: 18px; font-weight: bold; fill: #1e293b; }
      .subtitle { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; fill: #475569; }
      .box-title { font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; font-weight: bold; fill: #0f172a; }
      .box-desc { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; fill: #334155; }
      .tier-label { font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; font-weight: bold; fill: #2563eb; letter-spacing: 1px; }
      .arrow { stroke: #64748b; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
    </style>
    <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
    </marker>
    <linearGradient id="grad-blue" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#eff6ff" />
      <stop offset="100%" stop-color="#dbeafe" />
    </linearGradient>
    <linearGradient id="grad-green" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f0fdf4" />
      <stop offset="100%" stop-color="#dcfce7" />
    </linearGradient>
    <linearGradient id="grad-purple" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#faf5ff" />
      <stop offset="100%" stop-color="#f3e8ff" />
    </linearGradient>
    <linearGradient id="grad-amber" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fffbeb" />
      <stop offset="100%" stop-color="#fef3c7" />
    </linearGradient>
  </defs>

  <!-- Canvas Background -->
  <rect width="1000" height="700" fill="#ffffff" />
  <rect x="20" y="20" width="960" height="660" rx="12" fill="#f8fafc" stroke="#e2e8f0" stroke-width="2" />

  <!-- Main Title -->
  <text x="500" y="55" text-anchor="middle" class="title">Decoupled Neuro-Symbolic GraphRAG System Architecture</text>
  <text x="500" y="78" text-anchor="middle" class="subtitle">Explainable Personal Finance AI Assistant (FastAPI + Neo4j + Python Engine + Groq LLM + React)</text>

  <!-- TIER 1: Presentation Tier -->
  <text x="50" y="115" class="tier-label">1. PRESENTATION TIER (CLIENT BROWSER)</text>
  <rect x="50" y="125" width="900" height="85" rx="8" fill="url(#grad-blue)" stroke="#93c5fd" stroke-width="1.5" />
  <text x="70" y="150" class="box-title">React 18 Single Page Application (Vite 5 @ Port 3000)</text>
  <text x="70" y="172" class="box-desc">• Interactive Dashboard (4 Dynamic KPI Cards &amp; Letter Grade)</text>
  <text x="70" y="190" class="box-desc">• Multi-turn Advisory Chat with Markdown 4-Section Executive Cards</text>
  <text x="520" y="172" class="box-desc">• Recharts SVG Financial Visualizations &amp; Category Breakdowns</text>
  <text x="520" y="190" class="box-desc">• Dual Ingestion Hub (CSV Statements &amp; Vision OCR Upload)</text>

  <!-- Arrow T1 -> T2 -->
  <path d="M 500 210 L 500 240" class="arrow" />

  <!-- TIER 2: API Gateway & Security Tier -->
  <text x="50" y="255" class="tier-label">2. API GATEWAY &amp; SECURITY TIER (PORT 8000)</text>
  <rect x="50" y="265" width="900" height="80" rx="8" fill="url(#grad-purple)" stroke="#d8b4fe" stroke-width="1.5" />
  <text x="70" y="290" class="box-title">FastAPI Asynchronous Gateway &amp; Route Orchestration</text>
  <text x="70" y="312" class="box-desc">• Signed HTTP-Only Session Cookies (HMAC-SHA256, 8-hr TTL)</text>
  <text x="70" y="328" class="box-desc">• PBKDF2 Password Hashing (100,000 iterations + 16B Salt)</text>
  <text x="520" y="312" class="box-desc">• SlowAPI Rate Limiting (@5/min on Auth endpoints)</text>
  <text x="520" y="328" class="box-desc">• Deep Health Monitoring &amp; Zero-Trust User Derivation</text>

  <!-- Arrow T2 -> Splits to Ingestion and NLU -->
  <path d="M 270 345 L 270 375" class="arrow" />
  <path d="M 730 345 L 730 375" class="arrow" />

  <!-- TIER 3A: Ingestion Pipeline -->
  <rect x="50" y="380" width="430" height="110" rx="8" fill="url(#grad-amber)" stroke="#fcd34d" stroke-width="1.5" />
  <text x="70" y="405" class="box-title">Multimodal Ingestion Pipeline</text>
  <text x="70" y="427" class="box-desc">• Bank Statement CSV Dialect Normalizer</text>
  <text x="70" y="443" class="box-desc">• Groq Vision OCR (qwen/qwen3.8-27b) for Receipts/UPI</text>
  <text x="70" y="459" class="box-desc">• SHA-256 Collision-Resistant Fingerprint Deduplication</text>
  <text x="70" y="475" class="box-desc">• Automated 1-to-1 Internal Transfer Disambiguation</text>

  <!-- TIER 3B: NLU & GraphRAG Retrieval -->
  <rect x="520" y="380" width="430" height="110" rx="8" fill="url(#grad-amber)" stroke="#fcd34d" stroke-width="1.5" />
  <text x="540" y="405" class="box-title">NLU &amp; Targeted GraphRAG Layer</text>
  <text x="540" y="427" class="box-desc">• Intent Classifier (Purchase Safety, Savings, Runway, DTI, Health)</text>
  <text x="540" y="443" class="box-desc">• Date Ambiguity Resolution &amp; Conversational Context Memory</text>
  <text x="540" y="459" class="box-desc">• Subgraph Cypher Traversal (Extracts relevant nodes only)</text>
  <text x="540" y="475" class="box-desc">• Secondary LLM Intent Parser Fallback</text>

  <!-- Arrows into Neo4j Knowledge Graph -->
  <path d="M 270 490 L 270 515 L 450 515" class="arrow" />
  <path d="M 730 490 L 730 515 L 550 515" class="arrow" />

  <!-- TIER 4: Dynamic Knowledge Graph Tier -->
  <rect x="50" y="525" width="900" height="65" rx="8" fill="url(#grad-green)" stroke="#86efac" stroke-width="1.5" />
  <text x="70" y="550" class="box-title">Dynamic Knowledge Graph (Neo4j: finance-ai-antigravity @ Bolt 7687)</text>
  <text x="70" y="572" class="box-desc">Nodes: User, Account, Transaction, Category, Income, Loan, EMI, Goal, Merchant | Uniqueness Constraints on User, Account, Fingerprint</text>

  <!-- Arrow T4 -> T5 -->
  <path d="M 500 590 L 500 610" class="arrow" />

  <!-- TIER 5: Symbolic Engine & Neural LLM Explainer -->
  <rect x="50" y="615" width="430" height="65" rx="8" fill="url(#grad-blue)" stroke="#93c5fd" stroke-width="1.5" />
  <text x="70" y="635" class="box-title">Deterministic Financial Engine</text>
  <text x="70" y="652" class="box-desc">• Integer-Paise Arithmetic (Single Source of Truth)</text>
  <text x="70" y="667" class="box-desc">• Savings, Runway, DTI, Safety, Health (0-100)</text>

  <path d="M 480 647 L 515 647" class="arrow" />

  <rect x="520" y="615" width="430" height="65" rx="8" fill="url(#grad-purple)" stroke="#d8b4fe" stroke-width="1.5" />
  <text x="540" y="635" class="box-title">LLM Explainer &amp; Verifier Guardrail</text>
  <text x="540" y="652" class="box-desc">• Groq LLM (openai/gpt-oss-120b) + XML Boundary Isolation</text>
  <text x="540" y="667" class="box-desc">• Two-Tier Factual Verifier + Deterministic Fallback</text>

</svg>
"""

save_svg("architecture", "figure_2_1_system_architecture.svg", svg_arch)

# -------------------------------------------------------------
# 2. End-to-End Sequence Diagram SVG
# -------------------------------------------------------------
svg_seq = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600" width="100%" height="100%">
  <defs>
    <style>
      .title { font-family: 'Segoe UI', Arial, sans-serif; font-size: 16px; font-weight: bold; fill: #0f172a; }
      .actor-box { fill: #f1f5f9; stroke: #64748b; stroke-width: 1.5; rx: 6px; }
      .actor-text { font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; font-weight: bold; fill: #1e293b; text-anchor: middle; }
      .lifeline { stroke: #cbd5e1; stroke-width: 1.5; stroke-dasharray: 4 4; }
      .msg-line { stroke: #3b82f6; stroke-width: 1.5; marker-end: url(#arrow-blue); }
      .ret-line { stroke: #10b981; stroke-width: 1.5; stroke-dasharray: 4 3; marker-end: url(#arrow-green); }
      .msg-text { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; fill: #334155; }
    </style>
    <marker id="arrow-blue" markerWidth="6" markerHeight="5" refX="5" refY="2.5" orient="auto">
      <polygon points="0 0, 6 2.5, 0 5" fill="#3b82f6" />
    </marker>
    <marker id="arrow-green" markerWidth="6" markerHeight="5" refX="5" refY="2.5" orient="auto">
      <polygon points="0 0, 6 2.5, 0 5" fill="#10b981" />
    </marker>
  </defs>

  <rect width="900" height="600" fill="#ffffff" />
  <text x="450" y="30" text-anchor="middle" class="title">Figure 2.2: End-to-End Query Execution Sequence Flow</text>

  <!-- Actors -->
  <rect x="40" y="50" width="100" height="35" class="actor-box" />
  <text x="90" y="72" class="actor-text">Client (UI)</text>
  <line x1="90" y1="85" x2="90" y2="560" class="lifeline" />

  <rect x="180" y="50" width="110" height="35" class="actor-box" />
  <text x="235" y="72" class="actor-text">FastAPI Gateway</text>
  <line x1="235" y1="85" x2="235" y2="560" class="lifeline" />

  <rect x="330" y="50" width="110" height="35" class="actor-box" />
  <text x="385" y="72" class="actor-text">Question Parser</text>
  <line x1="385" y1="85" x2="385" y2="560" class="lifeline" />

  <rect x="480" y="50" width="110" height="35" class="actor-box" />
  <text x="535" y="72" class="actor-text">Neo4j Graph</text>
  <line x1="535" y1="85" x2="535" y2="560" class="lifeline" />

  <rect x="630" y="50" width="110" height="35" class="actor-box" />
  <text x="685" y="72" class="actor-text">Financial Engine</text>
  <line x1="685" y1="85" x2="685" y2="560" class="lifeline" />

  <rect x="770" y="50" width="100" height="35" class="actor-box" />
  <text x="820" y="72" class="actor-text">LLM &amp; Verifier</text>
  <line x1="820" y1="85" x2="820" y2="560" class="lifeline" />

  <!-- Step 1: User Query -->
  <line x1="90" y1="110" x2="230" y2="110" class="msg-line" />
  <text x="100" y="103" class="msg-text">1. POST /api/assistant/chat ("Can I spend ₹15k?")</text>

  <!-- Step 2: NLU Parsing -->
  <line x1="235" y1="140" x2="380" y2="140" class="msg-line" />
  <text x="245" y="133" class="msg-text">2. parse_question(text, history)</text>

  <line x1="380" y1="170" x2="240" y2="170" class="ret-line" />
  <text x="250" y="163" class="msg-text">3. {intent: 'PURCHASE_SAFETY', amt: 15000}</text>

  <!-- Step 3: Graph Retrieval -->
  <line x1="235" y1="200" x2="530" y2="200" class="msg-line" />
  <text x="250" y="193" class="msg-text">4. retrieve_subgraph(User, PURCHASE_SAFETY)</text>

  <line x1="530" y1="235" x2="240" y2="235" class="ret-line" />
  <text x="260" y="228" class="msg-text">5. Subgraph (Accounts: ₹45k, Pending EMIs: ₹10k, Living Expenses)</text>

  <!-- Step 4: Deterministic Math -->
  <line x1="235" y1="270" x2="680" y2="270" class="msg-line" />
  <text x="280" y="263" class="msg-text">6. check_purchase_safety(Context, 1500000 paise)</text>

  <line x1="680" y1="310" x2="240" y2="310" class="ret-line" />
  <text x="290" y="303" class="msg-text">7. Decision: NOT_SAFE (BalAfter: ₹20k &lt; ReserveBuffer: ₹63k)</text>

  <!-- Step 5: LLM Generation & Verification -->
  <line x1="235" y1="350" x2="815" y2="350" class="msg-line" />
  <text x="310" y="343" class="msg-text">8. build_prompt(Evidence, v1.1) -> Groq API</text>

  <line x1="820" y1="390" x2="820" y2="420" class="msg-line" />
  <text x="730" y="410" class="msg-text">9. verify_explanation()</text>

  <line x1="815" y1="450" x2="240" y2="450" class="ret-line" />
  <text x="350" y="443" class="msg-text">10. Verified 4-Section Executive Text + Fact Card</text>

  <!-- Step 6: Client Delivery -->
  <line x1="235" y1="490" x2="95" y2="490" class="ret-line" />
  <text x="110" y="483" class="msg-text">11. JSON Response: Formatted Card &amp; Graph Metrics</text>

  <!-- Completion Note -->
  <rect x="250" y="520" width="400" height="30" rx="4" fill="#ecfdf5" stroke="#10b981" />
  <text x="450" y="540" text-anchor="middle" class="msg-text" style="font-weight: bold; fill: #065f46;">
    100% Deterministic Math Accuracy Guaranteed — Zero Hallucination
  </text>
</svg>
"""

save_svg("workflow", "figure_2_2_sequence_diagram.svg", svg_seq)

# -------------------------------------------------------------
# 3. Knowledge Graph Entity Schema SVG
# -------------------------------------------------------------
svg_schema = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 550" width="100%" height="100%">
  <defs>
    <style>
      .node { stroke-width: 2; rx: 8px; }
      .node-text { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; font-weight: bold; fill: #ffffff; text-anchor: middle; }
      .rel-text { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10px; font-weight: bold; fill: #475569; text-anchor: middle; }
      .rel-line { stroke: #64748b; stroke-width: 1.5; marker-end: url(#arr); }
    </style>
    <marker id="arr" markerWidth="6" markerHeight="5" refX="5" refY="2.5" orient="auto">
      <polygon points="0 0, 6 2.5, 0 5" fill="#64748b" />
    </marker>
  </defs>

  <rect width="850" height="550" fill="#ffffff" />
  <text x="425" y="30" text-anchor="middle" font-family="'Segoe UI', Arial" font-size="16" font-weight="bold" fill="#0f172a">
    Figure 2.3: Neo4j Multi-Relational Financial Graph Schema
  </text>

  <!-- Nodes -->
  <!-- User -->
  <rect x="360" y="60" width="130" height="45" fill="#2563eb" class="node" />
  <text x="425" y="88" class="node-text">:User</text>

  <!-- Account -->
  <rect x="150" y="160" width="130" height="45" fill="#059669" class="node" />
  <text x="215" y="188" class="node-text">:Account</text>

  <!-- Income -->
  <rect x="570" y="160" width="130" height="45" fill="#16a34a" class="node" />
  <text x="635" y="188" class="node-text">:Income</text>

  <!-- Loan -->
  <rect x="360" y="240" width="130" height="45" fill="#dc2626" class="node" />
  <text x="425" y="268" class="node-text">:Loan</text>

  <!-- Transaction -->
  <rect x="80" y="290" width="130" height="45" fill="#d97706" class="node" />
  <text x="145" y="318" class="node-text">:Transaction</text>

  <!-- Category -->
  <rect x="80" y="420" width="130" height="45" fill="#9333ea" class="node" />
  <text x="145" y="448" class="node-text">:Category</text>

  <!-- EMI -->
  <rect x="360" y="370" width="130" height="45" fill="#e11d48" class="node" />
  <text x="425" y="398" class="node-text">:EMI</text>

  <!-- Goal -->
  <rect x="620" y="290" width="130" height="45" fill="#0891b2" class="node" />
  <text x="685" y="318" class="node-text">:Goal</text>

  <!-- ImportBatch -->
  <rect x="230" y="480" width="130" height="45" fill="#475569" class="node" />
  <text x="295" y="508" class="node-text">:ImportBatch</text>

  <!-- Relationships -->
  <!-- User -> Account -->
  <line x1="380" y1="105" x2="250" y2="155" class="rel-line" />
  <text x="300" y="125" class="rel-text">HAS_ACCOUNT</text>

  <!-- User -> Income -->
  <line x1="470" y1="105" x2="590" y2="155" class="rel-line" />
  <text x="560" y="125" class="rel-text">RECEIVED_INCOME</text>

  <!-- User -> Loan -->
  <line x1="425" y1="105" x2="425" y2="235" class="rel-line" />
  <text x="460" y="175" class="rel-text">HAS_LOAN</text>

  <!-- User -> Goal -->
  <line x1="480" y1="105" x2="650" y2="285" class="rel-line" />
  <text x="590" y="210" class="rel-text">HAS_GOAL</text>

  <!-- Account -> Transaction -->
  <line x1="190" y1="205" x2="160" y2="285" class="rel-line" />
  <text x="130" y="245" class="rel-text">MADE_TRANSACTION</text>

  <!-- Transaction -> Category -->
  <line x1="145" y1="335" x2="145" y2="415" class="rel-line" />
  <text x="190" y="380" class="rel-text">BELONGS_TO</text>

  <!-- Loan -> EMI -->
  <line x1="425" y1="285" x2="425" y2="365" class="rel-line" />
  <text x="455" y="330" class="rel-text">HAS_EMI</text>

  <!-- Transaction -> ImportBatch -->
  <line x1="170" y1="335" x2="260" y2="475" class="rel-line" />
  <text x="245" y="410" class="rel-text">PART_OF_BATCH</text>

  <!-- Transaction <-> Transaction (Internal Transfer) -->
  <path d="M 80 305 C 10 305, 10 330, 75 330" class="rel-line" />
  <text x="45" y="350" class="rel-text">INTER_ACCOUNT_TRANSFER</text>
</svg>
"""

save_svg("database", "figure_2_3_neo4j_graph_schema.svg", svg_schema)

# -------------------------------------------------------------
# 4. Latency Distribution Chart SVG
# -------------------------------------------------------------
svg_latency = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="100%" height="100%">
  <defs>
    <style>
      .title { font-family: 'Segoe UI', Arial, sans-serif; font-size: 15px; font-weight: bold; fill: #0f172a; }
      .axis-label { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; fill: #475569; }
      .bar-label { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; font-weight: bold; fill: #1e293b; }
      .val-label { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; font-weight: bold; fill: #2563eb; }
    </style>
  </defs>

  <rect width="700" height="400" fill="#ffffff" />
  <text x="350" y="28" text-anchor="middle" class="title">Figure 5.1: Stage-Wise Latency Profiling (Empirical Micro-Benchmark)</text>

  <!-- Grid lines -->
  <line x1="160" y1="60" x2="160" y2="330" stroke="#e2e8f0" stroke-width="1.5" />
  <line x1="160" y1="330" x2="650" y2="330" stroke="#94a3b8" stroke-width="1.5" />

  <!-- Bar 1: NLU Parsing -->
  <text x="150" y="95" text-anchor="end" class="bar-label">NLU Parsing</text>
  <rect x="160" y="80" width="2" height="25" fill="#3b82f6" rx="2" />
  <text x="175" y="97" class="val-label">0.1 ms (&lt;0.01%)</text>

  <!-- Bar 2: Cypher Graph Retrieval -->
  <text x="150" y="150" text-anchor="end" class="bar-label">Graph Subgraph Traversal</text>
  <rect x="160" y="135" width="10" height="25" fill="#10b981" rx="2" />
  <text x="185" y="152" class="val-label">11.8 ms (0.65%)</text>

  <!-- Bar 3: Financial Engine -->
  <text x="150" y="205" text-anchor="end" class="bar-label">Deterministic Math Engine</text>
  <rect x="160" y="190" width="2" height="25" fill="#6366f1" rx="2" />
  <text x="175" y="207" class="val-label">0.1 ms (&lt;0.01%)</text>

  <!-- Bar 4: Factual Verifier -->
  <text x="150" y="260" text-anchor="end" class="bar-label">Factual Verifier Audit</text>
  <rect x="160" y="245" width="2" height="25" fill="#f59e0b" rx="2" />
  <text x="175" y="262" class="val-label">0.2 ms (0.01%)</text>

  <!-- Bar 5: LLM Neural Inference -->
  <text x="150" y="315" text-anchor="end" class="bar-label">Groq LLM Generation</text>
  <rect x="160" y="300" width="440" height="25" fill="#8b5cf6" rx="2" />
  <text x="610" y="317" class="val-label">1,790.3 ms (99.3%)</text>

  <!-- Note -->
  <text x="350" y="370" text-anchor="middle" font-family="'Segoe UI', Arial" font-size="11" fill="#64748b">
    Symbolic pipeline (NLU + Graph + Engine + Verifier) completes in ~12 ms; Neural LLM dominates the turn.
  </text>
</svg>
"""

save_svg("evaluation", "figure_5_1_latency_breakdown.svg", svg_latency)

print("All SVG diagrams successfully created.")

