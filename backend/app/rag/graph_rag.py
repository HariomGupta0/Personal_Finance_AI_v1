import logging
import time
from datetime import date

from backend.app.database.neo4j_service import Neo4jService
from backend.app.nlu.question_parser import parse_question
from backend.app.engine.financial_engine import (
    check_purchase_safety,
    calculate_savings_rate,
    calculate_emergency_fund,
    calculate_emergency_runway,
    calculate_category_expenses,
    calculate_debt_burden,
    calculate_comprehensive_health,
    generate_financial_summary,
    calculate_merchant_expenses,
    calculate_top_transactions,
    calculate_period_comparison,
    calculate_spending_trends,
)

from backend.config import DEFAULT_PROMPT_VERSION
from backend.app.services.prompt_builder import build_financial_explanation_prompt
from backend.app.services.llm_service import ask_llm, ask_llm_async
from backend.app.services.verifier import verify_explanation, build_retry_feedback, VerificationResult
from backend.app.services.response_generator import build_deterministic_fallback

logger = logging.getLogger(__name__)



class GraphRAG:

    def __init__(self, db=None):
        self.db = db or Neo4jService()

    def retrieve_subgraph(self, user_id: str, intent: str, entities: dict | None = None) -> dict:
        """
        Targeted retrieval of the exact subgraphs needed for a given intent.
        Retrieves authorized, relevant nodes, relationships, and source identifiers.
        """
        entities = entities or {}

        # 1. Prefer grounded subgraph retrieval via Cypher if supported
        if hasattr(self.db, "retrieve_grounded_subgraph"):
            try:
                grounded = self.db.retrieve_grounded_subgraph(user_id, intent, entities)
                if isinstance(grounded, dict) and ("grounded_entities" in grounded or "context" in grounded):
                    return grounded
            except Exception as exc:
                logger.warning("retrieve_grounded_subgraph failed (%s); falling back to context query", exc)

        # 2. Legacy fallback for mock DBs or monolithic retrieval
        if intent == "PURCHASE_SAFETY":
            raw_ctx = self.db.get_purchase_context(user_id)
        elif intent == "SAVINGS_ANALYSIS":
            raw_ctx = self.db.get_savings_context(user_id)
        elif intent in ["EMERGENCY_FUND_ANALYSIS", "EMERGENCY_RUNWAY_ANALYSIS"]:
            raw_ctx = self.db.get_emergency_fund_context(user_id)
        elif intent in ["EXPENSE_BREAKDOWN", "CATEGORY_EXPENSE", "MERCHANT_EXPENSE", "TOP_TRANSACTIONS", "PERIOD_COMPARISON", "SPENDING_TREND"]:
            raw_ctx = self.db.get_financial_context(user_id)
        elif intent == "DEBT_ANALYSIS":
            raw_ctx = self.db.get_purchase_context(user_id)
        elif intent in ["FINANCIAL_HEALTH", "FINANCIAL_SUMMARY"]:
            raw_ctx = self.db.get_summary_context(user_id)
        else:
            raw_ctx = self.db.get_financial_context(user_id)

        return {
            "user_id": user_id,
            "intent": intent,
            "grounded_entities": raw_ctx,
            "source_identifiers": [],
            "graph_paths": [],
            "context": raw_ctx,
        }

    def execute_reasoning(self, intent: str, context: dict, entities: dict | None = None) -> dict:
        """
        Executes deterministic mathematical reasoning over the retrieved subgraph.
        """
        entities = entities or {}
        reporting_date = entities.get("reporting_date")
        clean_context = context.get("context", context) if isinstance(context, dict) else context

        if intent == "PURCHASE_SAFETY":
            amount = entities.get("amount") or 0.0
            return check_purchase_safety(clean_context, amount)

        elif intent == "SAVINGS_ANALYSIS":
            return calculate_savings_rate(clean_context, reporting_date=reporting_date)

        elif intent == "EMERGENCY_FUND_ANALYSIS":
            return calculate_emergency_fund(clean_context, reporting_date=reporting_date)

        elif intent == "EMERGENCY_RUNWAY_ANALYSIS":
            return calculate_emergency_runway(clean_context)

        elif intent == "EXPENSE_BREAKDOWN":
            return calculate_category_expenses(clean_context, reporting_date=reporting_date)

        elif intent == "CATEGORY_EXPENSE":
            target_cat = entities.get("category", "General")
            all_cat_stats = calculate_category_expenses(clean_context, reporting_date=reporting_date)
            matching_cat = next(
                (c for c in all_cat_stats["categories"] if c["category"].lower() == target_cat.lower()),
                None,
            )
            cat_spent = matching_cat["amount"] if matching_cat else 0.0
            total_exp = clean_context.get("total_expenses") or clean_context.get("period_total_expenses") or all_cat_stats["total_expenses"]
            pct = round((cat_spent / total_exp * 100), 2) if total_exp > 0 else 0.0

            return {
                "requested_category": target_cat,
                "category_spent": cat_spent,
                "percentage_of_total": pct,
                "total_expenses": total_exp,
                "all_categories": all_cat_stats["categories"],
                "reporting_period": all_cat_stats.get("reporting_period"),
            }

        elif intent == "MERCHANT_EXPENSE":
            target_merchant = entities.get("merchant") or ""
            return calculate_merchant_expenses(clean_context, merchant_name=target_merchant, reporting_date=reporting_date)

        elif intent == "TOP_TRANSACTIONS":
            limit = entities.get("limit") or 5
            amount_min = entities.get("amount_min")
            amount_max = entities.get("amount_max")
            return calculate_top_transactions(
                clean_context,
                limit=limit,
                amount_min=amount_min,
                amount_max=amount_max,
                reporting_date=reporting_date,
            )

        elif intent == "PERIOD_COMPARISON":
            plan = entities.get("query_plan")
            p_a_start = None
            p_a_end = None
            p_b_start = None
            p_b_end = None
            if plan and getattr(plan, "date_range", None) and plan.date_range.start_date:
                p_a_start = plan.date_range.start_date
                p_a_end = plan.date_range.end_date
            elif entities.get("reporting_date"):
                p_a_start = entities.get("reporting_date")

            if plan and getattr(plan, "comparison_date_range", None) and plan.comparison_date_range.start_date:
                p_b_start = plan.comparison_date_range.start_date
                p_b_end = plan.comparison_date_range.end_date
            elif entities.get("comparison_reporting_date"):
                p_b_start = entities.get("comparison_reporting_date")

            return calculate_period_comparison(
                clean_context,
                period_a_start=p_a_start,
                period_a_end=p_a_end,
                period_b_start=p_b_start,
                period_b_end=p_b_end,
                category=entities.get("category"),
                merchant=entities.get("merchant"),
                first_mentioned=entities.get("first_mentioned"),
                second_mentioned=entities.get("second_mentioned"),
            )

        elif intent == "SPENDING_TREND":
            trend_m = entities.get("trend_months") or 6
            return calculate_spending_trends(clean_context, num_months=trend_m)

        elif intent == "DEBT_ANALYSIS":
            return calculate_debt_burden(clean_context)


        elif intent == "FINANCIAL_HEALTH":
            return calculate_comprehensive_health(clean_context)

        elif intent == "FINANCIAL_SUMMARY":
            return generate_financial_summary(clean_context, reporting_date=reporting_date)

        else:
            return generate_financial_summary(clean_context, reporting_date=reporting_date)

    def construct_evidence_payload(self, intent: str, reasoning_result: dict, context: dict) -> dict:
        """
        Builds a verifiable evidence structure linking facts, calculations, and recommendations
        directly to their grounded graph nodes, calculation formulas, and missing-data caveats.
        """
        sym = "₹"
        evidence_items = []
        source_ids = context.get("source_identifiers", []) if isinstance(context, dict) else []
        graph_paths = context.get("graph_paths", []) if isinstance(context, dict) else []
        clean_context = context.get("context", context) if isinstance(context, dict) else context

        def _fmt_money(val) -> str:
            if val is None:
                return f"{sym}0"
            try:
                f = float(val)
                if f.is_integer():
                    return f"{sym}{int(f):,}"
                return f"{sym}{f:,.2f}"
            except (ValueError, TypeError):
                return f"{sym}{val}"

        acc_ids = []
        for a in clean_context.get("accounts", []):
            if isinstance(a, dict):
                if a.get("id"):
                    acc_ids.append(f"Account:{a['id']}")
                if a.get("bank"):
                    acc_ids.append(f"Account:{a['bank']}")

        loan_ids = []
        emi_ids = []
        for l in clean_context.get("loans", []):
            if isinstance(l, dict):
                if l.get("loan_id"):
                    loan_ids.append(f"Loan:{l['loan_id']}")
                if l.get("loan") and l.get("loan") != l.get("loan_id"):
                    loan_ids.append(f"Loan:{l['loan']}")
                if l.get("emi_id"):
                    emi_ids.append(f"EMI:{l['emi_id']}")

        inc_ids = []
        for i in clean_context.get("incomes", []):
            if isinstance(i, dict):
                if i.get("id"):
                    inc_ids.append(f"Income:{i['id']}")
                if i.get("source"):
                    inc_ids.append(f"Income:{i['source']}")

        txn_ids = [f"Transaction:{t['id']}" for t in clean_context.get("transactions", []) if isinstance(t, dict) and t.get("id")]

        goal_ids = []
        for g in clean_context.get("goals", []):
            if isinstance(g, dict):
                if g.get("id"):
                    goal_ids.append(f"Goal:{g['id']}")
                if g.get("name") and g.get("name") != g.get("id"):
                    goal_ids.append(f"Goal:{g['name']}")

        # 1. Reporting period & Data Freshness
        reporting_period = (
            reasoning_result.get("reporting_period")
            if isinstance(reasoning_result, dict) and reasoning_result.get("reporting_period")
            else f"{date.today().year}-{date.today().month:02d}"
        )

        all_dates = []
        for t in clean_context.get("transactions", []):
            if isinstance(t, dict) and t.get("date"):
                all_dates.append(str(t["date"])[:10])
        for i in clean_context.get("incomes", []):
            if isinstance(i, dict) and i.get("date"):
                all_dates.append(str(i["date"])[:10])
        for l in clean_context.get("loans", []):
            if isinstance(l, dict) and l.get("due_date"):
                all_dates.append(str(l["due_date"])[:10])

        if all_dates:
            latest_date = max(all_dates)
            data_freshness = f"Verified through latest transaction ({latest_date})"
        else:
            data_freshness = f"As of {date.today().isoformat()} (No historical records)"

        caveats: list[str] = []
        methodology_formula = ""
        calculation_method = ""

        # 2. Intent-specific evidence mapping
        if intent == "PURCHASE_SAFETY":
            ev = reasoning_result.get("evidence", {})
            methodology_formula = "Post-Purchase Balance = Current Balance - Pending EMIs - Purchase Cost (Safe if remainder >= 3 × Monthly Expenses)"
            calculation_method = "Deterministic liquidity stress test verifying emergency reserve preservation."

            if ev.get("monthly_expenses", 0) == 0:
                caveats.append("Zero monthly expenses recorded; baseline 3-month living reserve requirement could not be verified from transactions.")
            if not acc_ids:
                caveats.append("No active bank accounts linked; balance assumed as ₹0.")
            if not reasoning_result.get("is_sufficient_data", True) and ev.get("monthly_expenses", 0) > 0:
                caveats.append("Partial transaction history; expenditure baseline may be incomplete.")

            evidence_items = [
                {"label": "Current Account Balance", "value": _fmt_money(ev.get('current_balance', 0)), "source": "Account.balance", "formula": "Sum of verified liquid account balances", "source_node_ids": acc_ids},
                {"label": "Pending EMI Obligations", "value": _fmt_money(ev.get('pending_emi', 0)), "source": "EMI.amount", "formula": "Pending EMIs due in period", "source_node_ids": emi_ids},
                {"label": "Purchase Cost", "value": _fmt_money(ev.get('purchase_amount', 0)), "source": "User Query", "formula": "Requested purchase transaction", "source_node_ids": []},
                {"label": "Post-Purchase Remaining Balance", "value": _fmt_money(ev.get('balance_after_purchase', 0)), "source": "Deterministic Math", "formula": "Current Balance - Pending EMIs - Purchase Cost", "source_node_ids": acc_ids + emi_ids},
                {"label": "Recommended 3-Month Emergency Buffer", "value": _fmt_money(ev.get('emergency_requirement', 0)), "source": "Emergency Fund Formula", "formula": "3 × Monthly Living Expenses", "source_node_ids": txn_ids},
                {"label": "Decision & Safety Rating", "value": f"{reasoning_result.get('decision', 'UNKNOWN')} ({reasoning_result.get('risk_level', 'LOW')} Risk)", "source": "Financial Engine", "formula": "Safe if Remaining Balance >= 3-Month Buffer", "source_node_ids": []},
            ]

        elif intent == "SAVINGS_ANALYSIS":
            methodology_formula = "Savings Rate = ((Total Monthly Income - Total Monthly Expenses) / Total Monthly Income) × 100"
            calculation_method = "Cash flow delta analysis across verified income & ledger expenses."

            if not reasoning_result.get("has_income", True):
                caveats.append("Zero income recorded for this reporting period; savings rate is nominal 0%.")
            if not txn_ids:
                caveats.append("Zero expense transactions recorded in this reporting period.")
            if not reasoning_result.get("is_sufficient_data", True):
                caveats.append("Insufficient data recorded to determine accurate monthly savings.")

            evidence_items = [
                {"label": "Total Monthly Income", "value": _fmt_money(reasoning_result.get('total_income', 0)), "source": "Income.amount", "formula": "Sum of recorded income for period", "source_node_ids": inc_ids},
                {"label": "Total Monthly Expenses", "value": _fmt_money(reasoning_result.get('total_expenses', 0)), "source": "Transaction.amount", "formula": "Sum of expense transactions for period", "source_node_ids": txn_ids},
                {"label": "Net Monthly Savings", "value": _fmt_money(reasoning_result.get('savings', 0)), "source": "Deterministic Math", "formula": "Total Income - Total Expenses", "source_node_ids": inc_ids + txn_ids},
                {"label": "Savings Rate", "value": f"{reasoning_result.get('savings_rate', 0)}%", "source": "Savings Formula", "formula": "(Net Savings / Total Income) × 100", "source_node_ids": inc_ids + txn_ids},
            ]

        elif intent == "EMERGENCY_RUNWAY_ANALYSIS":
            methodology_formula = "Runway Months = Liquid Account Balance / Monthly Living Expenses"
            calculation_method = "Depletion horizon calculation based on liquid reserves and recurring monthly burn."

            if reasoning_result.get("monthly_expenses", 0) == 0:
                caveats.append(reasoning_result.get("data_note") or "Zero recorded expenses in period; runway is nominally capped but true living expenses are unverified.")
            if not acc_ids:
                caveats.append("No active bank accounts linked; balance assumed as ₹0.")

            evidence_items = [
                {"label": "Current Liquid Balance", "value": _fmt_money(reasoning_result.get('current_balance', 0)), "source": "Account.balance", "formula": "Sum of liquid bank accounts", "source_node_ids": acc_ids},
                {"label": "Monthly Expenses", "value": _fmt_money(reasoning_result.get('monthly_expenses', 0)), "source": "Transaction.amount", "formula": "Sum of living expense transactions", "source_node_ids": txn_ids},
                {"label": "Months of Runway", "value": f"{reasoning_result.get('runway_months', 0)} months", "source": "Runway Formula", "formula": "Liquid Balance / Monthly Expenses", "source_node_ids": acc_ids + txn_ids},
                {"label": "Buffer Health Status", "value": reasoning_result.get("status", "INSUFFICIENT"), "source": "Health Classifier", "formula": ">= 3.0m (Strong), >= 1.0m (Moderate), < 1.0m (Critical)", "source_node_ids": acc_ids + txn_ids},
            ]

        elif intent == "EMERGENCY_FUND_ANALYSIS":
            methodology_formula = "Emergency Fund Shortfall = Max(0, 3 × Monthly Expenses - Current Fund Reserve)"
            calculation_method = "Advisory living reserve target comparison against designated emergency savings goals."

            if not goal_ids:
                caveats.append("No designated 'Emergency Fund' goal found in your financial plan; current reserve is counted as ₹0.")
            if reasoning_result.get("monthly_expenses", 0) == 0:
                caveats.append("Zero monthly expenses recorded; recommended 3-month target is calculated with ₹0 expense baseline.")

            evidence_items = [
                {"label": "Monthly Expenses", "value": _fmt_money(reasoning_result.get('monthly_expenses', 0)), "source": "Transaction.amount", "formula": "Sum of monthly living expenses", "source_node_ids": txn_ids},
                {"label": "Recommended 3-Month Fund", "value": _fmt_money(reasoning_result.get('recommended_fund', 0)), "source": "Advisory Standard", "formula": "3 × Monthly Living Expenses", "source_node_ids": txn_ids},
                {"label": "Current Fund Reserve", "value": _fmt_money(reasoning_result.get('current_fund', 0)), "source": "Goal.current_amount", "formula": "Current balance in Emergency Fund goal", "source_node_ids": goal_ids},
                {"label": "Reserve Shortfall", "value": _fmt_money(reasoning_result.get('shortfall', 0)), "source": "Deterministic Math", "formula": "Max(0, Recommended Reserve - Current Reserve)", "source_node_ids": goal_ids + txn_ids},
            ]

        elif intent == "EXPENSE_BREAKDOWN":
            methodology_formula = "Top Category Share = (Top Category Amount / Total Expenses) × 100"
            calculation_method = "Categorical aggregation and proportional share computation across all ledger expenses."

            if not txn_ids:
                caveats.append("No expense transactions found for the reporting period.")

            evidence_items = [
                {"label": "Total Monthly Expenses", "value": _fmt_money(reasoning_result.get('total_expenses', 0)), "source": "Ledger Sum", "formula": "Sum of all debit transactions", "source_node_ids": txn_ids},
                {"label": "Highest Spending Category", "value": f"{reasoning_result.get('top_category', 'None')} ({_fmt_money(reasoning_result.get('top_amount', 0))})", "source": "Category Analytics", "formula": "Category with maximum expenditure", "source_node_ids": txn_ids},
            ]

        elif intent == "CATEGORY_EXPENSE":
            cat = reasoning_result.get("requested_category", "General")
            spent = reasoning_result.get("category_spent", 0.0)
            pct = reasoning_result.get("percentage_of_total", 0.0)
            methodology_formula = "Category Proportion = (Category Spend / Total Expenses) × 100"
            calculation_method = "Specific category expenditure filter and proportional share computation."

            if not txn_ids:
                caveats.append(f"No transactions recorded for category '{cat}' in this period.")

            evidence_items = [
                {"label": f"Spend on {cat}", "value": _fmt_money(spent), "source": f"Category({cat})", "formula": f"Sum of transactions for category {cat}", "source_node_ids": txn_ids},
                {"label": "Share of Expenses", "value": f"{pct}%", "source": "Deterministic Math", "formula": "(Category Spend / Total Expenses) × 100", "source_node_ids": txn_ids},
                {"label": "Total Expenses", "value": _fmt_money(reasoning_result.get('total_expenses', 0)), "source": "Ledger Sum", "formula": "Sum of all monthly expenses", "source_node_ids": txn_ids},
            ]

        elif intent == "MERCHANT_EXPENSE":
            merchant = reasoning_result.get("merchant", "Merchant")
            total_spent = reasoning_result.get("total_spent", 0.0)
            count = reasoning_result.get("transaction_count", 0)
            avg_spend = reasoning_result.get("average_spend", 0.0)
            is_found = reasoning_result.get("is_found", False)
            historical_count = reasoning_result.get("historical_count", 0)
            methodology_formula = "Merchant Spend = Sum of matching debit transactions (t.type == 'EXPENSE')"
            calculation_method = "Normalized merchant matching and deterministic transaction summation."

            if not is_found:
                caveats.append(f"No transactions matching merchant '{merchant}' were found in your transaction history.")
                evidence_items = [
                    {"label": f"Spend on {merchant}", "value": _fmt_money(0), "source": f"Merchant({merchant})", "formula": "Sum of matching merchant transactions", "source_node_ids": []},
                    {"label": "Matching Transactions", "value": "0", "source": "Graph Search", "formula": "Count of transactions matching merchant name", "source_node_ids": []},
                    {"label": "Status", "value": "Merchant Not Found", "source": "Audit Check", "formula": "Historical merchant presence check", "source_node_ids": []},
                ]
            elif count == 0:
                period_str = reasoning_result.get("reporting_period", "selected period")
                caveats.append(f"Confirmed zero spending on '{merchant}' for {period_str} ({historical_count} past transaction(s) found in other periods).")
                evidence_items = [
                    {"label": f"Spend on {merchant} ({period_str})", "value": _fmt_money(0), "source": f"Merchant({merchant})", "formula": "Sum of matching merchant transactions in period", "source_node_ids": []},
                    {"label": "Period Transactions", "value": "0", "source": "Ledger Count", "formula": "Count of transactions in selected period", "source_node_ids": []},
                    {"label": "Historical Record", "value": f"Verified ({historical_count} past transactions)", "source": "Graph History", "formula": "Total historical transactions for merchant", "source_node_ids": txn_ids},
                ]
            else:
                evidence_items = [
                    {"label": f"Total Spent on {merchant}", "value": _fmt_money(total_spent), "source": f"Merchant({merchant})", "formula": "Sum of matching debit transactions", "source_node_ids": txn_ids},
                    {"label": "Transaction Count", "value": f"{count} transactions", "source": "Transaction Ledger", "formula": "Count of verified transactions", "source_node_ids": txn_ids},
                    {"label": "Average Spend per Transaction", "value": _fmt_money(avg_spend), "source": "Deterministic Math", "formula": "Total Spend / Transaction Count", "source_node_ids": txn_ids},
                    {"label": "Reporting Period", "value": reasoning_result.get("reporting_period", "All Time"), "source": "Temporal Scope", "formula": "Active reporting filter", "source_node_ids": []},
                ]

        elif intent == "TOP_TRANSACTIONS":
            txs = reasoning_result.get("transactions", [])
            total_sel = reasoning_result.get("total_selected_amount", 0.0)
            limit_applied = reasoning_result.get("limit_applied")
            methodology_formula = "Ranked Transactions = Filter(t.type == 'EXPENSE', amount_bounds) ORDER BY amount DESC LIMIT N"
            calculation_method = "Deterministic numeric ranking and threshold filtering."

            if not txs:
                caveats.append("No expense transactions matched the specified criteria.")
                evidence_items = [
                    {"label": "Selected Transactions", "value": "0", "source": "Transaction Ledger", "formula": "Count of matching expenses", "source_node_ids": []},
                    {"label": "Total Amount", "value": _fmt_money(0), "source": "Deterministic Math", "formula": "Sum of matching expenses", "source_node_ids": []},
                ]
            else:
                evidence_items = []
                for idx, t in enumerate(txs):
                    tid = t.get("id")
                    node_id_list = [f"Transaction:{tid}"] if tid else []
                    desc = t.get("description") or "Expense"
                    date_str = t.get("date") or "N/A"
                    cat_str = t.get("category") or "General"
                    evidence_items.append({
                        "label": f"#{idx + 1} {desc}",
                        "value": _fmt_money(t.get("amount", 0)),
                        "source": f"Transaction:{tid or idx + 1}",
                        "formula": f"Date: {date_str} | Category: {cat_str}",
                        "source_node_ids": node_id_list,
                    })
                evidence_items.append({
                    "label": "Total of Selected Transactions",
                    "value": _fmt_money(total_sel),
                    "source": "Deterministic Math",
                    "formula": f"Sum of {len(txs)} selected transactions",
                    "source_node_ids": txn_ids,
                })
                if limit_applied:
                    evidence_items.append({
                        "label": "Result Limit",
                        "value": f"Top {limit_applied} transactions",
                        "source": "Query Plan",
                        "formula": "User requested transaction limit",
                        "source_node_ids": [],
                    })

        elif intent == "PERIOD_COMPARISON":
            methodology_formula = "Absolute Change = Period B Total - Period A Total; % Change = ((B - A) / A) × 100"
            calculation_method = "Deterministic multi-period expense comparison and category variance attribution."

            p_a = reasoning_result.get("period_a", {})
            p_b = reasoning_result.get("period_b", {})
            cat_vars = reasoning_result.get("category_variances", [])

            for cav in reasoning_result.get("caveats", []):
                caveats.append(cav)

            evidence_items = [
                {
                    "label": f"Baseline Total ({p_a.get('name', 'Period A')})",
                    "value": _fmt_money(p_a.get("total_spent", 0)),
                    "source": "Period A Transactions",
                    "formula": f"Sum of {p_a.get('transaction_count', 0)} eligible expenses ({p_a.get('start_date')} to {p_a.get('end_date')})",
                    "source_node_ids": [f"Transaction:{tid}" for tid in reasoning_result.get("period_a_tx_ids", [])[:5]],
                },
                {
                    "label": f"Comparison Total ({p_b.get('name', 'Period B')})",
                    "value": _fmt_money(p_b.get("total_spent", 0)),
                    "source": "Period B Transactions",
                    "formula": f"Sum of {p_b.get('transaction_count', 0)} eligible expenses ({p_b.get('start_date')} to {p_b.get('end_date')})",
                    "source_node_ids": [f"Transaction:{tid}" for tid in reasoning_result.get("period_b_tx_ids", [])[:5]],
                },
                {
                    "label": "Absolute Change",
                    "value": f"{'+' if reasoning_result.get('absolute_change', 0) > 0 else ''}{_fmt_money(reasoning_result.get('absolute_change', 0))}",
                    "source": "Deterministic Math",
                    "formula": "Period B Total - Period A Total",
                    "source_node_ids": [],
                },
                {
                    "label": "Percentage Change",
                    "value": reasoning_result.get("percentage_change_display", "N/A"),
                    "source": "Deterministic Math",
                    "formula": "((Period B - Period A) / Period A) × 100" if reasoning_result.get("percentage_change") is not None else "Baseline Zero",
                    "source_node_ids": [],
                },
            ]

            if reasoning_result.get("category"):
                evidence_items.append({
                    "label": "Filtered Category",
                    "value": str(reasoning_result.get("category")),
                    "source": "Query Plan",
                    "formula": "Category filter applied across both comparison periods",
                    "source_node_ids": [],
                })
            elif reasoning_result.get("merchant"):
                evidence_items.append({
                    "label": "Filtered Merchant",
                    "value": str(reasoning_result.get("merchant")),
                    "source": "Query Plan",
                    "formula": "Merchant filter applied across both comparison periods",
                    "source_node_ids": [],
                })

            for v in cat_vars[:3]:
                sign = "+" if v.get("absolute_difference", 0) > 0 else ""
                diff_val = _fmt_money(v.get("absolute_difference", 0))
                evidence_items.append({
                    "label": f"Category Variance: {v.get('category')}",
                    "value": f"{sign}{diff_val} ({v.get('percentage_change_display')})",
                    "source": "Variance Attribution",
                    "formula": v.get("mathematical_contribution_note", ""),
                    "source_node_ids": [f"Transaction:{tx['id']}" for tx in v.get("supporting_transactions", []) if tx.get("id")],
                })

        elif intent == "SPENDING_TREND":
            methodology_formula = "Monthly Spending Trend = Chronological aggregation of eligible monthly expenses"
            calculation_method = "Deterministic monthly expense aggregation with statement coverage evaluation."

            for cav in reasoning_result.get("caveats", []):
                caveats.append(cav)

            evidence_items = [
                {
                    "label": "Average Monthly Spend",
                    "value": _fmt_money(reasoning_result.get("average_monthly_spend", 0)),
                    "source": "Deterministic Math",
                    "formula": "Sum(Covered Months) / Count(Covered Months)",
                    "source_node_ids": [],
                },
                {
                    "label": "Coverage Range",
                    "value": f"{reasoning_result.get('coverage_start', '')} to {reasoning_result.get('coverage_end', '')}",
                    "source": "Statement Range",
                    "formula": "Evaluated chronological window",
                    "source_node_ids": [],
                },
                {
                    "label": "Data Completeness",
                    "value": f"{reasoning_result.get('available_months_count', 0)} / {reasoning_result.get('total_months_evaluated', 0)} months verified",
                    "source": "Coverage Evaluator",
                    "formula": "Months with confirmed statement data",
                    "source_node_ids": [],
                },
                {
                    "label": "Trend Direction",
                    "value": str(reasoning_result.get("trend_direction", "STABLE")),
                    "source": "Trend Engine",
                    "formula": "Comparison of initial covered month to latest covered month",
                    "source_node_ids": [],
                },
            ]

            for pt in reasoning_result.get("trend_points", [])[-3:]:
                if pt.get("status") == "DATA_UNAVAILABLE":
                    val_str = "Data Unavailable"
                else:
                    val_str = f"{_fmt_money(pt.get('total_spent', 0))} ({pt.get('transaction_count', 0)} txns)"
                evidence_items.append({
                    "label": f"{pt.get('month_name')} Spend",
                    "value": val_str,
                    "source": pt.get("status"),
                    "formula": pt.get("coverage_note", ""),
                    "source_node_ids": [f"Transaction:{tid}" for tid in pt.get("transaction_ids", [])[:3]],
                })

        elif intent == "DEBT_ANALYSIS":
            methodology_formula = "Debt-to-Income (DTI) = (Monthly Pending EMIs / Total Monthly Income) × 100"
            calculation_method = "Fixed debt obligation burden analysis against recurring monthly inflow."

            if not reasoning_result.get("has_income", True) and reasoning_result.get("monthly_emi", 0) > 0:
                caveats.append("Critical debt risk: Active monthly EMI obligations with zero recorded income.")
            if not loan_ids:
                caveats.append("No active loan obligations or outstanding balances found in your graph.")
            if not reasoning_result.get("is_sufficient_data", True):
                caveats.append("Debt assessment computed with incomplete financial records.")

            evidence_items = [
                {"label": "Total Outstanding Loan Principal", "value": _fmt_money(reasoning_result.get('total_outstanding_debt', 0)), "source": "Loan.outstanding", "formula": "Sum of outstanding balances on all loans", "source_node_ids": loan_ids},
                {"label": "Pending Monthly EMI", "value": _fmt_money(reasoning_result.get('monthly_emi', 0)), "source": "EMI.amount", "formula": "Pending EMIs due in reporting month", "source_node_ids": emi_ids},
                {"label": "Debt-to-Income (DTI) Ratio", "value": f"{reasoning_result.get('dti_ratio', 0)}%", "source": "DTI Formula", "formula": "(Monthly Pending EMIs / Total Monthly Income) × 100", "source_node_ids": emi_ids + inc_ids},
                {"label": "Debt Risk Assessment", "value": reasoning_result.get("assessment", "Healthy"), "source": "Risk Classifier", "formula": "DTI <= 20% (Low), <= 35% (Moderate), <= 50% (High), > 50% (Critical)", "source_node_ids": loan_ids + emi_ids},
            ]


        elif intent == "FINANCIAL_HEALTH":
            methodology_formula = "Health Score = Savings Score (max 35) + Runway Score (max 35) + Debt Score (max 30)"
            calculation_method = "Multi-pillar weighted scoring model bounded strictly in [0.0, 100.0]."

            if not reasoning_result.get("is_sufficient_data", True):
                caveats.append("Financial health score computed with partial data (unverified expense or income baseline).")

            evidence_items = [
                {"label": "Overall Financial Health Score", "value": f"{reasoning_result.get('health_score', 0)} / 100", "source": "Composite Scoring Model", "formula": "Savings (35) + Runway (35) + Debt (30)", "source_node_ids": acc_ids + loan_ids + inc_ids},
                {"label": "Financial Grade", "value": f"Grade {reasoning_result.get('grade', 'B')}", "source": "Grading Engine", "formula": ">=85 (A), >=70 (B), >=50 (C), <50 (D)", "source_node_ids": acc_ids + loan_ids + inc_ids},
                {"label": "Savings Rate Pillar", "value": f"{reasoning_result.get('savings_rate', 0)}%", "source": "Savings Model", "formula": "(Savings / Income) × 100", "source_node_ids": inc_ids + txn_ids},
                {"label": "Emergency Runway Pillar", "value": f"{reasoning_result.get('runway_months', 0)} months", "source": "Runway Model", "formula": "Balance / Monthly Expenses", "source_node_ids": acc_ids + txn_ids},
                {"label": "DTI Ratio Pillar", "value": f"{reasoning_result.get('dti_ratio', 0)}%", "source": "Debt Model", "formula": "EMIs / Income × 100", "source_node_ids": emi_ids + inc_ids},
            ]

        else:
            methodology_formula = "Comprehensive financial summary aggregation"
            calculation_method = "Synthesis of liquidity, recurring burn, debt burden, and savings."
            if not txn_ids and not inc_ids:
                caveats.append("No transactions or income records found for this period.")

        return {
            "intent": intent,
            "facts": evidence_items,
            "source_identifiers": sorted(list(set(source_ids + goal_ids))),
            "graph_paths": graph_paths,
            "raw_result": reasoning_result,
            "reporting_period": reporting_period,
            "data_freshness": data_freshness,
            "methodology_formula": methodology_formula,
            "calculation_method": calculation_method,
            "caveats": caveats,
            "is_sufficient_data": reasoning_result.get("is_sufficient_data", True) if isinstance(reasoning_result, dict) else True,
        }


    def process_query(
        self,
        question: str,
        user_id: str = "U001",
        conversation_history: list[dict] | None = None,
        prompt_version: str | None = None,
    ) -> dict:
        """
        Complete GraphRAG pipeline:
        NLU → Targeted Subgraph Retrieval → Deterministic Math → Grounded Evidence → LLM Explanation.

        Returns a response dict that includes:
          - explanation        : LLM-generated natural language explanation
          - intent             : Classified intent string
          - math_result        : Raw deterministic calculation result
          - evidence           : List of evidence cards (label/value/source/node_ids)
          - source_identifiers : Grounded node IDs retrieved from Neo4j
          - graph_paths        : Explicit graph relationship paths traversed
          - latency_breakdown  : Per-stage latency in milliseconds
          - tokens             : LLM token usage (prompt / completion / total)
        """
        pipeline_start = time.perf_counter()

        # ── Stage 1: NLU ─────────────────────────────────────────────────────
        nlu_t0 = time.perf_counter()
        parsed = parse_question(question, conversation_history=conversation_history)
        intent = parsed["intent"]
        nlu_ms = (time.perf_counter() - nlu_t0) * 1000

        logger.info("pipeline_start | user=%s | intent=%s | question=%r", user_id, intent, question[:80])

        if parsed.get("needs_clarification"):
            total_ms = (time.perf_counter() - pipeline_start) * 1000
            clarification_msg = parsed.get("clarification_message") or "Could you please clarify your request?"
            logger.info("clarification_required | user=%s | type=%s", user_id, parsed.get("clarification_type"))
            return {
                "query": question,
                "intent": intent,
                "decision": "NEEDS_CLARIFICATION",
                "math_result": {
                    "decision": "NEEDS_CLARIFICATION",
                    "reason": clarification_msg,
                    "clarification_type": parsed.get("clarification_type"),
                },
                "evidence": [],
                "evidence_metadata": {
                    "reporting_period": None,
                    "data_freshness": f"As of {date.today().isoformat()}",
                    "methodology_formula": None,
                    "calculation_method": None,
                    "caveats": [clarification_msg],
                    "is_sufficient_data": False,
                },
                "source_identifiers": [],
                "graph_paths": [],
                "explanation": clarification_msg,
                "prompt_version": prompt_version or DEFAULT_PROMPT_VERSION,
                "is_followup": parsed.get("is_followup", False),
                "turn_type": parsed.get("turn_type", "NEW_TOPIC"),
                "needs_clarification": True,
                "clarification_type": parsed.get("clarification_type"),
                "clarification_message": clarification_msg,
                "recalculated_fresh": True,
                "latency_breakdown": {"nlu_ms": round(nlu_ms, 1), "graph_ms": 0, "engine_ms": 0, "llm_ms": 0, "total_ms": round(total_ms, 1)},
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
            }

        if intent == "UNKNOWN":
            total_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.info("pipeline_done | user=%s | intent=UNKNOWN | total_ms=%.0f", user_id, total_ms)
            return {
                "query": question,
                "intent": "UNKNOWN",
                "decision": None,
                "math_result": None,
                "evidence": [],
                "evidence_metadata": {
                    "reporting_period": None,
                    "data_freshness": f"As of {date.today().isoformat()}",
                    "methodology_formula": None,
                    "calculation_method": None,
                    "caveats": ["Unrecognized intent; query could not be routed to financial engine."],
                    "is_sufficient_data": False,
                },
                "source_identifiers": [],
                "graph_paths": [],
                "explanation": (
                    "I'm sorry, I couldn't understand that financial question. "
                    "You can ask about purchase affordability (e.g. 'Can I spend ₹15000 on a phone?'), "
                    "savings rate, emergency runway, expenses breakdown, or financial health."
                ),
                "is_followup": parsed.get("is_followup", False),
                "turn_type": parsed.get("turn_type", "NEW_TOPIC"),
                "needs_clarification": False,
                "clarification_type": None,
                "recalculated_fresh": True,
                "latency_breakdown": {"nlu_ms": round(nlu_ms, 1), "graph_ms": 0, "engine_ms": 0, "llm_ms": 0, "total_ms": round(total_ms, 1)},
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
            }

        # ── Stage 2: Graph retrieval ──────────────────────────────────────────
        graph_t0 = time.perf_counter()
        context = self.retrieve_subgraph(user_id, intent, entities=parsed)
        graph_ms = (time.perf_counter() - graph_t0) * 1000
        logger.info("graph_retrieved | user=%s | intent=%s | graph_ms=%.0f", user_id, intent, graph_ms)

        # ── Stage 3: Deterministic engine ────────────────────────────────────
        engine_t0 = time.perf_counter()
        math_result = self.execute_reasoning(intent, context, entities=parsed)
        engine_ms = (time.perf_counter() - engine_t0) * 1000

        evidence_payload = self.construct_evidence_payload(intent, math_result, context)

        # ── Stage 4: LLM explanation ──────────────────────────────────────────
        llm_t0 = time.perf_counter()
        used_version = prompt_version or DEFAULT_PROMPT_VERSION

        evidence_for_prompt = dict(math_result)
        evidence_for_prompt["_source_identifiers"] = evidence_payload.get("source_identifiers", [])[:10]
        evidence_for_prompt["_graph_paths"] = evidence_payload.get("graph_paths", [])
        evidence_for_prompt["_grounded_facts"] = [
            {"label": item["label"], "value": item["value"], "source": item["source"], "node_ids": item.get("source_node_ids", [])[:3]}
            for item in evidence_payload.get("facts", [])
        ]

        prompt = build_financial_explanation_prompt(
            evidence_for_prompt,
            question=question,
            conversation_history=conversation_history,
            version=used_version,
        )
        llm_result = ask_llm(prompt)
        is_llm_error = bool(
            llm_result.get("is_fallback")
            or (isinstance(llm_result.get("content"), str) and "AI explanation temporarily unavailable" in llm_result["content"])
        )

        if is_llm_error:
            logger.warning(
                "LLM service returned fallback text after exhausted retries for intent %s",
                intent,
            )
            verification = VerificationResult({
                "verified": False,
                "violations": [{
                    "type": "LLM_ERROR",
                    "found": "_DEFAULT_FALLBACK_TEXT",
                    "section": "ALL",
                    "reason": "LLM service failed after exhausted retries; fallback text returned",
                }],
                "advisory": [],
                "advisory_count": 0,
                "scope": "claims in Quick Take/Numbers/Insights and all status labels; numbers in next-steps advice are listed as advisory, not blocked",
                "llm_error": True,
            })
            first_attempt_blocking = 1
            first_attempt_advisory = 0
            attempts = 1
            fallback_used = True
        else:
            # Numeric & Factual Verifier Check
            verification = verify_explanation(llm_result["content"], evidence_for_prompt, intent=intent)
            first_attempt_blocking = len(verification["violations"])
            first_attempt_advisory = len(verification["advisory"])
            attempts = 1
            fallback_used = False

            if not verification.verified:
                logger.warning(
                    "Verifier detected %d blocking violations on attempt 1 for intent %s: %s",
                    first_attempt_blocking,
                    intent,
                    verification["violations"],
                )
                retry_feedback = build_retry_feedback(verification["violations"])
                retry_prompt = prompt + "\n\n" + retry_feedback
                llm_result_retry = ask_llm(retry_prompt)
                retry_is_llm_error = bool(
                    llm_result_retry.get("is_fallback")
                    or (isinstance(llm_result_retry.get("content"), str) and "AI explanation temporarily unavailable" in llm_result_retry["content"])
                )

                if retry_is_llm_error:
                    logger.warning("LLM service returned fallback text on retry for intent %s", intent)
                    verification = VerificationResult({
                        "verified": False,
                        "violations": [{
                            "type": "LLM_ERROR",
                            "found": "_DEFAULT_FALLBACK_TEXT",
                            "section": "ALL",
                            "reason": "LLM service failed on retry after exhausted retries",
                        }],
                        "advisory": [],
                        "advisory_count": 0,
                        "scope": "claims in Quick Take/Numbers/Insights and all status labels; numbers in next-steps advice are listed as advisory, not blocked",
                        "llm_error": True,
                    })
                    attempts = 2
                    fallback_used = True
                    llm_result = {
                        "content": llm_result_retry["content"],
                        "prompt_tokens": llm_result.get("prompt_tokens", 0) + llm_result_retry.get("prompt_tokens", 0),
                        "completion_tokens": llm_result.get("completion_tokens", 0) + llm_result_retry.get("completion_tokens", 0),
                        "tokens_used": llm_result.get("tokens_used", 0) + llm_result_retry.get("tokens_used", 0),
                        "model": llm_result_retry.get("model") or llm_result.get("model", ""),
                    }
                else:
                    verification_retry = verify_explanation(
                        llm_result_retry["content"], evidence_for_prompt, intent=intent
                    )
                    attempts = 2

                    if verification_retry.verified:
                        logger.info("Verifier retry succeeded on attempt 2 for intent %s", intent)
                        llm_result = {
                            "content": llm_result_retry["content"],
                            "prompt_tokens": llm_result.get("prompt_tokens", 0) + llm_result_retry.get("prompt_tokens", 0),
                            "completion_tokens": llm_result.get("completion_tokens", 0) + llm_result_retry.get("completion_tokens", 0),
                            "tokens_used": llm_result.get("tokens_used", 0) + llm_result_retry.get("tokens_used", 0),
                            "model": llm_result_retry.get("model") or llm_result.get("model", ""),
                        }
                        verification = verification_retry
                    else:
                        logger.warning(
                            "Verifier retry failed on attempt 2 for intent %s; triggering safe fallback",
                            intent,
                        )
                        fallback_text = build_deterministic_fallback(math_result)
                        fallback_used = True
                        llm_result = {
                            "content": fallback_text,
                            "prompt_tokens": llm_result.get("prompt_tokens", 0) + llm_result_retry.get("prompt_tokens", 0),
                            "completion_tokens": llm_result.get("completion_tokens", 0) + llm_result_retry.get("completion_tokens", 0),
                            "tokens_used": llm_result.get("tokens_used", 0) + llm_result_retry.get("tokens_used", 0),
                            "model": llm_result_retry.get("model") or llm_result.get("model", ""),
                        }
                        verification = verify_explanation(fallback_text, evidence_for_prompt, intent=intent)

        llm_ms = (time.perf_counter() - llm_t0) * 1000

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(
            "pipeline_done | user=%s | intent=%s | nlu_ms=%.0f | graph_ms=%.0f | engine_ms=%.0f | llm_ms=%.0f | total_ms=%.0f",
            user_id, intent, nlu_ms, graph_ms, engine_ms, llm_ms, total_ms,
        )

        return {
            "query": question,
            "intent": intent,
            "entities": parsed,
            "math_result": math_result,
            "evidence": evidence_payload["facts"],
            "evidence_metadata": {
                "reporting_period": evidence_payload.get("reporting_period"),
                "data_freshness": evidence_payload.get("data_freshness"),
                "methodology_formula": evidence_payload.get("methodology_formula"),
                "calculation_method": evidence_payload.get("calculation_method"),
                "caveats": evidence_payload.get("caveats", []),
                "is_sufficient_data": evidence_payload.get("is_sufficient_data", True),
            },
            "source_identifiers": evidence_payload.get("source_identifiers", []),
            "graph_paths": evidence_payload.get("graph_paths", []),
            "explanation": llm_result["content"],
            "verified": bool(verification.verified),
            "verification": dict(verification),
            "llm_error": bool(verification.get("llm_error", False)),
            "first_attempt_blocking": first_attempt_blocking,
            "first_attempt_advisory": first_attempt_advisory,
            "attempts": attempts,
            "fallback_used": fallback_used,
            "prompt_version": used_version,
            "is_followup": parsed.get("is_followup", False),
            "turn_type": parsed.get("turn_type", "NEW_TOPIC"),
            "needs_clarification": False,
            "clarification_type": None,
            "recalculated_fresh": True,
            "latency_breakdown": {
                "nlu_ms": round(nlu_ms, 1),
                "graph_ms": round(graph_ms, 1),
                "engine_ms": round(engine_ms, 1),
                "llm_ms": round(llm_ms, 1),
                "total_ms": round(total_ms, 1),
            },
            "tokens": {
                "prompt": llm_result["prompt_tokens"],
                "completion": llm_result["completion_tokens"],
                "total": llm_result["tokens_used"],
            },
            "model": llm_result.get("model", ""),
        }

    async def process_query_async(
        self,
        question: str,
        user_id: str = "U001",
        conversation_history: list[dict] | None = None,
        prompt_version: str | None = None,
    ) -> dict:
        """
        Asynchronous GraphRAG pipeline:
        NLU → Targeted Subgraph Retrieval → Deterministic Math → Grounded Evidence → Non-blocking Async LLM.
        """
        pipeline_start = time.perf_counter()

        # ── Stage 1: NLU ─────────────────────────────────────────────────────
        nlu_t0 = time.perf_counter()
        parsed = parse_question(question, conversation_history=conversation_history)
        intent = parsed["intent"]
        nlu_ms = (time.perf_counter() - nlu_t0) * 1000

        logger.info("async_pipeline_start | user=%s | intent=%s | question=%r", user_id, intent, question[:80])

        if parsed.get("needs_clarification"):
            total_ms = (time.perf_counter() - pipeline_start) * 1000
            clarification_msg = parsed.get("clarification_message") or "Could you please clarify your request?"
            logger.info("async_clarification_required | user=%s | type=%s", user_id, parsed.get("clarification_type"))
            return {
                "query": question,
                "intent": intent,
                "decision": "NEEDS_CLARIFICATION",
                "math_result": {
                    "decision": "NEEDS_CLARIFICATION",
                    "reason": clarification_msg,
                    "clarification_type": parsed.get("clarification_type"),
                },
                "evidence": [],
                "evidence_metadata": {
                    "reporting_period": None,
                    "data_freshness": f"As of {date.today().isoformat()}",
                    "methodology_formula": None,
                    "calculation_method": None,
                    "caveats": [clarification_msg],
                    "is_sufficient_data": False,
                },
                "source_identifiers": [],
                "graph_paths": [],
                "explanation": clarification_msg,
                "prompt_version": prompt_version or DEFAULT_PROMPT_VERSION,
                "is_followup": parsed.get("is_followup", False),
                "turn_type": parsed.get("turn_type", "NEW_TOPIC"),
                "needs_clarification": True,
                "clarification_type": parsed.get("clarification_type"),
                "clarification_message": clarification_msg,
                "recalculated_fresh": True,
                "latency_breakdown": {"nlu_ms": round(nlu_ms, 1), "graph_ms": 0, "engine_ms": 0, "llm_ms": 0, "total_ms": round(total_ms, 1)},
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
            }

        if intent == "UNKNOWN":
            total_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.info("async_pipeline_done | user=%s | intent=UNKNOWN | total_ms=%.0f", user_id, total_ms)
            return {
                "query": question,
                "intent": "UNKNOWN",
                "decision": None,
                "math_result": None,
                "evidence": [],
                "evidence_metadata": {
                    "reporting_period": None,
                    "data_freshness": f"As of {date.today().isoformat()}",
                    "methodology_formula": None,
                    "calculation_method": None,
                    "caveats": ["Unrecognized intent; query could not be routed to financial engine."],
                    "is_sufficient_data": False,
                },
                "source_identifiers": [],
                "graph_paths": [],
                "explanation": (
                    "I'm sorry, I couldn't understand that financial question. "
                    "You can ask about purchase affordability (e.g. 'Can I spend ₹15000 on a phone?'), "
                    "savings rate, emergency runway, expenses breakdown, or financial health."
                ),
                "is_followup": parsed.get("is_followup", False),
                "turn_type": parsed.get("turn_type", "NEW_TOPIC"),
                "needs_clarification": False,
                "clarification_type": None,
                "recalculated_fresh": True,
                "latency_breakdown": {"nlu_ms": round(nlu_ms, 1), "graph_ms": 0, "engine_ms": 0, "llm_ms": 0, "total_ms": round(total_ms, 1)},
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
            }

        # ── Stage 2: Graph retrieval ──────────────────────────────────────────
        graph_t0 = time.perf_counter()
        context = self.retrieve_subgraph(user_id, intent, entities=parsed)
        graph_ms = (time.perf_counter() - graph_t0) * 1000
        logger.info("async_graph_retrieved | user=%s | intent=%s | graph_ms=%.0f", user_id, intent, graph_ms)

        # ── Stage 3: Deterministic engine ────────────────────────────────────
        engine_t0 = time.perf_counter()
        math_result = self.execute_reasoning(intent, context, entities=parsed)
        engine_ms = (time.perf_counter() - engine_t0) * 1000

        evidence_payload = self.construct_evidence_payload(intent, math_result, context)

        # ── Stage 4: Non-blocking Async LLM explanation ───────────────────────
        llm_t0 = time.perf_counter()
        used_version = prompt_version or DEFAULT_PROMPT_VERSION

        evidence_for_prompt = dict(math_result)
        evidence_for_prompt["_source_identifiers"] = evidence_payload.get("source_identifiers", [])[:10]
        evidence_for_prompt["_graph_paths"] = evidence_payload.get("graph_paths", [])
        evidence_for_prompt["_grounded_facts"] = [
            {"label": item["label"], "value": item["value"], "source": item["source"], "node_ids": item.get("source_node_ids", [])[:3]}
            for item in evidence_payload.get("facts", [])
        ]

        prompt = build_financial_explanation_prompt(
            evidence_for_prompt,
            question=question,
            conversation_history=conversation_history,
            version=used_version,
        )
        llm_result = await ask_llm_async(prompt)
        is_llm_error = bool(
            llm_result.get("is_fallback")
            or (isinstance(llm_result.get("content"), str) and "AI explanation temporarily unavailable" in llm_result["content"])
        )

        if is_llm_error:
            logger.warning(
                "LLM service returned fallback text after exhausted retries for intent %s",
                intent,
            )
            verification = VerificationResult({
                "verified": False,
                "violations": [{
                    "type": "LLM_ERROR",
                    "found": "_DEFAULT_FALLBACK_TEXT",
                    "section": "ALL",
                    "reason": "LLM service failed after exhausted retries; fallback text returned",
                }],
                "advisory": [],
                "advisory_count": 0,
                "scope": "claims in Quick Take/Numbers/Insights and all status labels; numbers in next-steps advice are listed as advisory, not blocked",
                "llm_error": True,
            })
            first_attempt_blocking = 1
            first_attempt_advisory = 0
            attempts = 1
            fallback_used = True
        else:
            # Numeric & Factual Verifier Check
            verification = verify_explanation(llm_result["content"], evidence_for_prompt, intent=intent)
            first_attempt_blocking = len(verification["violations"])
            first_attempt_advisory = len(verification["advisory"])
            attempts = 1
            fallback_used = False

            if not verification.verified:
                logger.warning(
                    "Verifier detected %d blocking violations on attempt 1 for intent %s: %s",
                    first_attempt_blocking,
                    intent,
                    verification["violations"],
                )
                # Retry with feedback listing blocking items only
                retry_feedback = build_retry_feedback(verification["violations"])
                retry_prompt = prompt + "\n\n" + retry_feedback
                llm_result_retry = await ask_llm_async(retry_prompt)
                retry_is_llm_error = bool(
                    llm_result_retry.get("is_fallback")
                    or (isinstance(llm_result_retry.get("content"), str) and "AI explanation temporarily unavailable" in llm_result_retry["content"])
                )

                if retry_is_llm_error:
                    logger.warning("LLM service retry failed with fallback text for intent %s", intent)
                    verification = VerificationResult({
                        "verified": False,
                        "violations": [{
                            "type": "LLM_ERROR",
                            "found": "_DEFAULT_FALLBACK_TEXT",
                            "section": "ALL",
                            "reason": "LLM service failed on retry after exhausted retries",
                        }],
                        "advisory": [],
                        "advisory_count": 0,
                        "scope": "claims in Quick Take/Numbers/Insights and all status labels; numbers in next-steps advice are listed as advisory, not blocked",
                        "llm_error": True,
                    })
                    attempts = 2
                    fallback_used = True
                    llm_result = {
                        "content": llm_result_retry["content"],
                        "prompt_tokens": llm_result.get("prompt_tokens", 0) + llm_result_retry.get("prompt_tokens", 0),
                        "completion_tokens": llm_result.get("completion_tokens", 0) + llm_result_retry.get("completion_tokens", 0),
                        "tokens_used": llm_result.get("tokens_used", 0) + llm_result_retry.get("tokens_used", 0),
                        "model": llm_result_retry.get("model") or llm_result.get("model", ""),
                    }
                else:
                    verification_retry = verify_explanation(
                        llm_result_retry["content"], evidence_for_prompt, intent=intent
                    )
                    attempts = 2

                    if verification_retry.verified:
                        logger.info("Verifier retry succeeded on attempt 2 for intent %s", intent)
                        llm_result = {
                            "content": llm_result_retry["content"],
                            "prompt_tokens": llm_result.get("prompt_tokens", 0) + llm_result_retry.get("prompt_tokens", 0),
                            "completion_tokens": llm_result.get("completion_tokens", 0) + llm_result_retry.get("completion_tokens", 0),
                            "tokens_used": llm_result.get("tokens_used", 0) + llm_result_retry.get("tokens_used", 0),
                            "model": llm_result_retry.get("model") or llm_result.get("model", ""),
                        }
                        verification = verification_retry
                    else:
                        logger.warning(
                            "Verifier retry failed on attempt 2 for intent %s; triggering safe fallback",
                            intent,
                        )
                        fallback_text = build_deterministic_fallback(math_result)
                        fallback_used = True
                        llm_result = {
                            "content": fallback_text,
                            "prompt_tokens": llm_result.get("prompt_tokens", 0) + llm_result_retry.get("prompt_tokens", 0),
                            "completion_tokens": llm_result.get("completion_tokens", 0) + llm_result_retry.get("completion_tokens", 0),
                            "tokens_used": llm_result.get("tokens_used", 0) + llm_result_retry.get("tokens_used", 0),
                            "model": llm_result_retry.get("model") or llm_result.get("model", ""),
                        }
                        verification = verify_explanation(fallback_text, evidence_for_prompt, intent=intent)

        llm_ms = (time.perf_counter() - llm_t0) * 1000

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(
            "async_pipeline_done | user=%s | intent=%s | nlu_ms=%.0f | graph_ms=%.0f | engine_ms=%.0f | llm_ms=%.0f | total_ms=%.0f",
            user_id, intent, nlu_ms, graph_ms, engine_ms, llm_ms, total_ms,
        )

        return {
            "query": question,
            "intent": intent,
            "entities": parsed,
            "math_result": math_result,
            "evidence": evidence_payload["facts"],
            "evidence_metadata": {
                "reporting_period": evidence_payload.get("reporting_period"),
                "data_freshness": evidence_payload.get("data_freshness"),
                "methodology_formula": evidence_payload.get("methodology_formula"),
                "calculation_method": evidence_payload.get("calculation_method"),
                "caveats": evidence_payload.get("caveats", []),
                "is_sufficient_data": evidence_payload.get("is_sufficient_data", True),
            },
            "source_identifiers": evidence_payload.get("source_identifiers", []),
            "graph_paths": evidence_payload.get("graph_paths", []),
            "explanation": llm_result["content"],
            "verified": bool(verification.verified),
            "verification": dict(verification),
            "llm_error": bool(verification.get("llm_error", False)),
            "first_attempt_blocking": first_attempt_blocking,
            "first_attempt_advisory": first_attempt_advisory,
            "attempts": attempts,
            "fallback_used": fallback_used,
            "prompt_version": used_version,
            "is_followup": parsed.get("is_followup", False),
            "turn_type": parsed.get("turn_type", "NEW_TOPIC"),
            "needs_clarification": False,
            "clarification_type": None,
            "recalculated_fresh": True,
            "latency_breakdown": {
                "nlu_ms": round(nlu_ms, 1),
                "graph_ms": round(graph_ms, 1),
                "engine_ms": round(engine_ms, 1),
                "llm_ms": round(llm_ms, 1),
                "total_ms": round(total_ms, 1),
            },
            "tokens": {
                "prompt": llm_result["prompt_tokens"],
                "completion": llm_result["completion_tokens"],
                "total": llm_result["tokens_used"],
            },
            "model": llm_result.get("model", ""),
        }

