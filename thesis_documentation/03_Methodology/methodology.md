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

