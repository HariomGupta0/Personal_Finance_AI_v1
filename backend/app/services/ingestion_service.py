from backend.app.database.neo4j_service import Neo4jService
from backend.app.nlu.transaction_extractor import extract_transaction
from backend.app.engine.financial_engine import (
    calculate_savings_rate,
    calculate_emergency_fund,
    generate_financial_summary
)

class IngestionService:

    def __init__(self, db=None):
        self.db = db or Neo4jService()

    def ingest_transaction_from_text(self, text, user_id="U001", account_id=None):
        extracted = extract_transaction(text)
        if not extracted:
            raise ValueError(f"Could not parse a valid transaction from input: '{text}'")

        if extracted["type"] == "INCOME":
            return self.ingest_income(
                user_id=user_id,
                source=extracted["description"],
                amount=extracted["amount"],
                date_str=extracted["date"],
                account_id=account_id,
            )

        return self.ingest_transaction(
            user_id=user_id,
            account_id=account_id,
            amount=extracted["amount"],
            description=extracted["description"],
            category_name=extracted["category"],
            transaction_type=extracted["type"],
            date_str=extracted["date"]
        )

    def ingest_transaction(self, user_id="U001", account_id=None, amount=0, description="", category_name="General", transaction_type="EXPENSE", date_str=None):
        if transaction_type.upper() == "INCOME":
            return self.ingest_income(
                user_id=user_id,
                source=description or category_name or "Income",
                amount=amount,
                date_str=date_str,
                account_id=account_id,
            )
        before_ctx = self.db.get_financial_context(user_id)
        before_summary = generate_financial_summary(before_ctx) if before_ctx else None

        tx_record = self.db.add_transaction(
            user_id=user_id,
            account_id=account_id,
            amount=amount,
            description=description,
            category_name=category_name,
            transaction_type=transaction_type,
            date_str=date_str
        )

        after_ctx = self.db.get_financial_context(user_id)
        after_summary = generate_financial_summary(after_ctx)

        curr_bal = tx_record["new_balance"]
        sym = "₹"
        impact_summary = (
            f"Successfully recorded {tx_record['type']} of {sym}{tx_record['amount']:,.2f} "
            f"({tx_record['category']} - '{tx_record['description']}'). "
            f"Updated Account Balance: {sym}{curr_bal:,.2f}. "
            f"Savings Rate: {after_summary['savings_rate']}% (was {before_summary['savings_rate'] if before_summary else 0}%). "
            f"Monthly Expenses: {sym}{after_summary['monthly_expenses']:,}. "
            f"Emergency Reserve Needed: {sym}{after_summary['recommended_emergency_fund']:,} "
            f"(Shortfall: {sym}{after_summary['emergency_fund_shortfall']:,})."
        )

        return {
            "status": "SUCCESS",
            "transaction": tx_record,
            "before_metrics": before_summary,
            "after_metrics": after_summary,
            "impact_summary": impact_summary
        }

    def ingest_income(self, user_id="U001", source="Salary", amount=0, date_str=None, account_id=None):
        before_ctx = self.db.get_financial_context(user_id)
        before_summary = generate_financial_summary(before_ctx) if before_ctx else None

        income_record = self.db.add_income(
            user_id=user_id,
            source=source,
            amount=amount,
            date_str=date_str,
            account_id=account_id
        )

        after_ctx = self.db.get_financial_context(user_id)
        after_summary = generate_financial_summary(after_ctx)

        sym = "₹"
        impact_summary = (
            f"Recorded Income of {sym}{amount:,.2f} from '{source}'. "
            f"Total Income: {sym}{after_summary['income']:,}. "
            f"Updated Savings Rate: {after_summary['savings_rate']}%."
        )

        return {
            "status": "SUCCESS",
            "income": income_record,
            "before_metrics": before_summary,
            "after_metrics": after_summary,
            "impact_summary": impact_summary
        }

    def ingest_goal(self, user_id="U001", name="Emergency Fund", target_amount=100000, current_amount=None, target_date=None):
        goal_record = self.db.add_or_update_goal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date
        )
        after_ctx = self.db.get_financial_context(user_id)
        after_summary = generate_financial_summary(after_ctx)

        return {
            "status": "SUCCESS",
            "goal": goal_record,
            "metrics": after_summary
        }
