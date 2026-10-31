import uuid
import hashlib
import hmac
import secrets
import logging
from collections import Counter
from datetime import date, datetime, timedelta
from neo4j import GraphDatabase
from neo4j.time import Date
from backend.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

logger = logging.getLogger(__name__)

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return pwd_hash, salt

def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
    expected_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(pwd_hash, expected_hash)

def convert_dates(data):
    if isinstance(data, dict):
        return {
            key: convert_dates(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [
            convert_dates(item)
            for item in data
        ]

    if isinstance(data, Date):
        return data.iso_format()

    return data

class Neo4jService:

    def __init__(self, database=None, driver=None):
        self.database = database or NEO4J_DATABASE
        self.driver = driver or GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        try:
            self.init_schema_constraints(strict=False)
        except Exception as exc:
            logger.warning("Neo4j schema constraints initialization skipped or failed during startup: %s", exc)

    # ---------------------------------------------------------
    # Context Retrieval Methods
    # ---------------------------------------------------------

    def get_financial_context(self, user_id: str):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        query = """
        MATCH (u:User {id: $user_id})

        CALL (u) {
            OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)
            OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction)
            OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)

            RETURN collect(DISTINCT {
                id: a.id,
                bank: a.bank,
                type: a.account_type,
                balance: a.balance
            }) AS accounts,

            collect(DISTINCT {
                id: t.id,
                description: t.description,
                amount: t.amount,
                type: t.type,
                date: t.date,
                category: c.name
            }) AS transactions
        }

        CALL (u) {
            OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income)

            RETURN collect(DISTINCT {
                id: i.id,
                source: i.source,
                amount: i.amount,
                date: i.date
            }) AS incomes
        }

        CALL (u) {
            OPTIONAL MATCH (u)-[:HAS_LOAN]->(l:Loan)-[:HAS_EMI]->(e:EMI)

            RETURN collect(DISTINCT {
                loan_id: l.id,
                loan: l.name,
                outstanding: l.outstanding,
                emi_id: e.id,
                emi: e.amount,
                due_date: e.due_date,
                status: e.status
            }) AS loans
        }

        CALL (u) {
            OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal)

            RETURN collect(DISTINCT {
                id: g.id,
                name: g.name,
                target: g.target_amount,
                current: g.current_amount,
                target_date: g.target_date
            }) AS goals
        }

        RETURN {
            user: u.name,
            accounts: accounts,
            transactions: [t IN transactions WHERE t.id IS NOT NULL],
            incomes: [i IN incomes WHERE i.source IS NOT NULL],
            loans: [l IN loans WHERE l.loan IS NOT NULL],
            goals: [g IN goals WHERE g.name IS NOT NULL]
        } AS financial_context
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            record = result.single()

            if record:
                context = record["financial_context"]
                return convert_dates(context)

            return None

    def get_period_transactions(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
        category: str | None = None,
        merchant: str | None = None,
    ) -> list[dict]:
        """
        Retrieves eligible expense transactions for an explicit date period using parameterized Cypher.
        Guarantees strict user isolation and consistent expense and transfer filtering.
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        query = """
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
        OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)
        WHERE t.date >= $start_date AND t.date <= $end_date
          AND t.type = 'EXPENSE'
          AND t.amount > 0
          AND NOT (toLower(coalesce(t.description, '')) CONTAINS 'transfer' 
                   OR toLower(coalesce(c.name, '')) = 'transfer')
          AND ($category IS NULL OR toLower(coalesce(c.name, '')) = toLower($category))
        RETURN collect(DISTINCT {
            id: t.id,
            description: t.description,
            amount: t.amount,
            type: t.type,
            date: t.date,
            category: c.name,
            bank: a.bank
        }) AS transactions
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                user_id=user_id,
                start_date=str(start_date),
                end_date=str(end_date),
                category=category,
            )
            record = result.single()
            if record and record["transactions"]:
                txs = record["transactions"]
                if merchant:
                    m_lower = merchant.lower().strip()
                    txs = [
                        t for t in txs
                        if m_lower in str(t.get("description", "")).lower()
                        or m_lower in str(t.get("merchant", "")).lower()
                    ]
                return convert_dates(txs)
            return []

    def get_purchase_context(self, user_id: str):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        query = """
        MATCH (u:User {id: $user_id})

        OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)
        OPTIONAL MATCH (u)-[:HAS_LOAN]->(l:Loan)-[:HAS_EMI]->(e:EMI)
        OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a2:Account)-[:MADE_TRANSACTION]->(t:Transaction)
        OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)
        OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal)

        RETURN
            u.name AS user,

            collect(DISTINCT {
                account: a.id,
                balance: a.balance
            }) AS accounts,

            collect(DISTINCT {
                loan: l.name,
                emi: e.amount,
                due_date: e.due_date,
                status: e.status
            }) AS loans,

            collect(DISTINCT {
                transaction: t.description,
                amount: t.amount,
                type: t.type,
                category: c.name,
                date: t.date
            }) AS transactions,

            collect(DISTINCT {
                goal: g.name,
                target: g.target_amount,
                current: g.current_amount
            }) AS goals
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            record = result.single()

            if record:
                return convert_dates({
                    "user": record["user"],
                    "accounts": [a for a in record["accounts"] if a.get("account") is not None],
                    "loans": [l for l in record["loans"] if l.get("loan") is not None],
                    "transactions": [t for t in record["transactions"] if t.get("transaction") is not None],
                    "goals": [g for g in record["goals"] if g.get("goal") is not None]
                })

            return None

    def get_savings_context(self, user_id: str):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        query = """
        MATCH (u:User {id: $user_id})

        OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income)
        OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)

        RETURN
            u.name AS user,

            collect(DISTINCT {
                source: i.source,
                amount: i.amount,
                date: i.date
            }) AS incomes,

            collect(DISTINCT {
                transaction: t.description,
                amount: t.amount,
                type: t.type,
                date: t.date
            }) AS transactions
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            record = result.single()

            if record:
                return convert_dates({
                    "user": record["user"],
                    "incomes": [i for i in record["incomes"] if i.get("source") is not None],
                    "transactions": [t for t in record["transactions"] if t.get("transaction") is not None]
                })

            return None
        
    def get_emergency_fund_context(self, user_id: str):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        query = """
        MATCH (u:User {id: $user_id})

        OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
        OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal)

        RETURN
            u.name AS user,

            collect(DISTINCT {
                transaction: t.description,
                amount: t.amount,
                type: t.type,
                date: t.date
            }) AS transactions,

            collect(DISTINCT {
                goal: g.name,
                target: g.target_amount,
                current: g.current_amount,
                target_date: g.target_date
            }) AS goals
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            record = result.single()

            if record:
                return convert_dates({
                    "user": record["user"],
                    "transactions": [t for t in record["transactions"] if t.get("transaction") is not None],
                    "goals": [g for g in record["goals"] if g.get("goal") is not None]
                })

            return None

    def get_summary_context(self, user_id: str):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        query = """
        MATCH (u:User {id: $user_id})

        OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income)
        OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)
        OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction)
        OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal)

        RETURN
            u.name AS user,

            collect(DISTINCT {
                source: i.source,
                amount: i.amount,
                date: i.date
            }) AS incomes,

            collect(DISTINCT {
                account: a.id,
                balance: a.balance
            }) AS accounts,

            collect(DISTINCT {
                transaction: t.description,
                amount: t.amount,
                type: t.type,
                date: t.date
            }) AS transactions,

            collect(DISTINCT {
                goal: g.name,
                target: g.target_amount,
                current: g.current_amount,
                target_date: g.target_date
            }) AS goals
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            record = result.single()

            if record:
                return convert_dates({
                    "user": record["user"],
                    "incomes": [i for i in record["incomes"] if i.get("source") is not None],
                    "accounts": [a for a in record["accounts"] if a.get("account") is not None],
                    "transactions": [t for t in record["transactions"] if t.get("transaction") is not None],
                    "goals": [g for g in record["goals"] if g.get("goal") is not None]
                })

            return None

    # ---------------------------------------------------------
    # Grounded Subgraph Retrieval (Phase 2 Target Fact Queries)
    # ---------------------------------------------------------

    def retrieve_grounded_subgraph(self, user_id: str, intent: str, entities: dict | None = None) -> dict:
        """
        Grounded Graph Retrieval:
        Retrieves ONLY the authorized, relevant nodes, edges, and source identifiers
        needed to answer the specific financial intent, without broad database dumping.
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        entities = entities or {}
        reporting_date = entities.get("reporting_date")
        date_from = None
        date_to = None

        if reporting_date:
            from datetime import date
            if isinstance(reporting_date, str):
                try:
                    reporting_date = date.fromisoformat(reporting_date)
                except Exception:
                    reporting_date = None
            if isinstance(reporting_date, date):
                import calendar
                last_day = calendar.monthrange(reporting_date.year, reporting_date.month)[1]
                date_from = date(reporting_date.year, reporting_date.month, 1).isoformat()
                date_to = date(reporting_date.year, reporting_date.month, last_day).isoformat()

        target_category = entities.get("category")
        source_identifiers: list[str] = []
        graph_paths: list[str] = []
        grounded_data: dict = {
            "accounts": [],
            "transactions": [],
            "loans": [],
            "incomes": [],
            "goals": [],
        }

        # 1. CATEGORY_EXPENSE: Retrieve all period transactions to compute true relative proportion
        if intent == "CATEGORY_EXPENSE":
            query = """
            MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)-[:BELONGS_TO]->(c:Category)
            WHERE ($date_from IS NULL OR date(t.date) >= date($date_from))
              AND ($date_to IS NULL OR date(t.date) <= date($date_to))
            RETURN collect(DISTINCT {
                id: a.id,
                bank: a.bank,
                balance: a.balance
            }) AS accounts,
            collect(DISTINCT {
                id: t.id,
                description: t.description,
                amount: t.amount,
                type: t.type,
                date: t.date,
                category: c.name,
                category_id: c.id,
                account_id: a.id
            }) AS transactions,
            collect(DISTINCT {
                id: c.id,
                name: c.name
            }) AS categories
            """
            with self.driver.session(database=self.database) as session:
                rec = session.run(
                    query,
                    user_id=user_id,
                    date_from=date_from,
                    date_to=date_to,
                ).single()
                if rec:
                    accounts = convert_dates(rec["accounts"])
                    transactions = convert_dates([t for t in rec["transactions"] if t.get("id")])
                    categories = convert_dates(rec["categories"])
                    grounded_data["accounts"] = accounts
                    grounded_data["transactions"] = transactions

                    for a in accounts:
                        source_identifiers.append(f"Account:{a['id']}")
                        graph_paths.append(f"(User:{user_id})-[:HAS_ACCOUNT]->(Account:{a['id']})")
                    for c in categories:
                        if not target_category or (c.get("name") and c["name"].lower() == target_category.lower()):
                            source_identifiers.append(f"Category:{c.get('name') or c.get('id')}")
                    for t in transactions:
                        if not target_category or (t.get("category") and t["category"].lower() == target_category.lower()):
                            source_identifiers.append(f"Transaction:{t['id']}")
                            graph_paths.append(f"(Account:{t.get('account_id')})-[:MADE_TRANSACTION]->(Transaction:{t['id']})-[:BELONGS_TO]->(Category:{t.get('category')})")

        # 2. PURCHASE_SAFETY: Accounts (balance) + Pending EMIs + Recent Expenses
        elif intent == "PURCHASE_SAFETY":
            from datetime import date, timedelta
            ninety_days_ago = (date.today() - timedelta(days=90)).isoformat()

            query = """
            MATCH (u:User {id: $user_id})

            OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)
            OPTIONAL MATCH (u)-[:HAS_LOAN]->(l:Loan)-[:HAS_EMI]->(e:EMI)
            WHERE e.status = 'PENDING'

            OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(:Account)-[:MADE_TRANSACTION]->(t:Transaction {type: 'EXPENSE'})
            WHERE date(t.date) >= date($ninety_days_ago)
            OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)

            RETURN
                collect(DISTINCT {id: a.id, bank: a.bank, balance: a.balance}) AS accounts,
                collect(DISTINCT {loan_id: l.id, loan: l.name, emi_id: e.id, emi: e.amount, due_date: e.due_date, status: e.status}) AS loans,
                collect(DISTINCT {id: t.id, amount: t.amount, type: t.type, date: t.date, category: c.name}) AS transactions
            """
            with self.driver.session(database=self.database) as session:
                rec = session.run(query, user_id=user_id, ninety_days_ago=ninety_days_ago).single()
                if rec:
                    accounts = convert_dates([a for a in rec["accounts"] if a.get("id")])
                    loans = convert_dates([l for l in rec["loans"] if l.get("loan")])
                    transactions = convert_dates([t for t in rec["transactions"] if t.get("id")])
                    grounded_data["accounts"] = accounts
                    grounded_data["loans"] = loans
                    grounded_data["transactions"] = transactions

                    for a in accounts:
                        source_identifiers.append(f"Account:{a['id']}")
                        graph_paths.append(f"(User:{user_id})-[:HAS_ACCOUNT]->(Account:{a['id']})")
                    for l in loans:
                        source_identifiers.append(f"Loan:{l.get('loan_id')}")
                        if l.get("emi_id"):
                            source_identifiers.append(f"EMI:{l.get('emi_id')}")
                            graph_paths.append(f"(User:{user_id})-[:HAS_LOAN]->(Loan:{l.get('loan_id')})-[:HAS_EMI]->(EMI:{l.get('emi_id')})")

        # 3. DEBT_ANALYSIS: Loans + EMIs + Incomes (for DTI ratio)
        elif intent == "DEBT_ANALYSIS":
            query = """
            MATCH (u:User {id: $user_id})
            OPTIONAL MATCH (u)-[:HAS_LOAN]->(l:Loan)-[:HAS_EMI]->(e:EMI)
            OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income)
            RETURN
                collect(DISTINCT {
                    loan_id: l.id,
                    loan: l.name,
                    outstanding: l.outstanding,
                    emi_id: e.id,
                    emi: e.amount,
                    due_date: e.due_date,
                    status: e.status
                }) AS loans,
                collect(DISTINCT {
                    id: i.id,
                    source: i.source,
                    amount: i.amount,
                    date: i.date
                }) AS incomes
            """
            with self.driver.session(database=self.database) as session:
                rec = session.run(query, user_id=user_id).single()
                if rec:
                    loans = convert_dates([l for l in rec["loans"] if l.get("loan")])
                    incomes = convert_dates([i for i in rec["incomes"] if i.get("id") or i.get("source")])
                    grounded_data["loans"] = loans
                    grounded_data["incomes"] = incomes

                    for l in loans:
                        source_identifiers.append(f"Loan:{l.get('loan_id')}")
                        if l.get("emi_id"):
                            source_identifiers.append(f"EMI:{l.get('emi_id')}")
                            graph_paths.append(f"(User:{user_id})-[:HAS_LOAN]->(Loan:{l.get('loan_id')})-[:HAS_EMI]->(EMI:{l.get('emi_id')})")
                    for i in incomes:
                        source_identifiers.append(f"Income:{i.get('id') or i.get('source')}")
                        graph_paths.append(f"(User:{user_id})-[:RECEIVED_INCOME]->(Income:{i.get('source')})")

        # 4. SAVINGS_ANALYSIS: Incomes & Expenses for target period
        elif intent == "SAVINGS_ANALYSIS":
            query = """
            MATCH (u:User {id: $user_id})
            OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income)
            WHERE ($date_from IS NULL OR date(i.date) >= date($date_from))
              AND ($date_to IS NULL OR date(i.date) <= date($date_to))

            OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
            WHERE ($date_from IS NULL OR date(t.date) >= date($date_from))
              AND ($date_to IS NULL OR date(t.date) <= date($date_to))
            OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)

            RETURN
                collect(DISTINCT {
                    id: i.id,
                    source: i.source,
                    amount: i.amount,
                    date: i.date
                }) AS incomes,
                collect(DISTINCT {
                    id: t.id,
                    description: t.description,
                    amount: t.amount,
                    type: t.type,
                    date: t.date,
                    category: c.name
                }) AS transactions
            """
            with self.driver.session(database=self.database) as session:
                rec = session.run(query, user_id=user_id, date_from=date_from, date_to=date_to).single()
                if rec:
                    incomes = convert_dates([i for i in rec["incomes"] if i.get("id") or i.get("source")])
                    transactions = convert_dates([t for t in rec["transactions"] if t.get("id")])
                    grounded_data["incomes"] = incomes
                    grounded_data["transactions"] = transactions

                    for i in incomes:
                        source_identifiers.append(f"Income:{i.get('id') or i.get('source')}")
                    for t in transactions:
                        source_identifiers.append(f"Transaction:{t['id']}")

        # 5. MERCHANT_EXPENSE: Historical & Period matching for requested merchant
        elif intent == "MERCHANT_EXPENSE":
            merchant = entities.get("merchant") or ""
            query = """
            MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
            WHERE t.type = 'EXPENSE'
              AND (toLower(t.description) CONTAINS toLower($merchant)
                   OR (t.merchant IS NOT NULL AND toLower(t.merchant) CONTAINS toLower($merchant)))
            OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)
            RETURN
              count(t) AS total_historical,
              collect(DISTINCT {id: a.id, bank: a.bank, balance: a.balance}) AS accounts,
              collect({
                  id: t.id,
                  description: t.description,
                  amount: t.amount,
                  type: t.type,
                  date: t.date,
                  merchant: t.merchant,
                  category: c.name,
                  account_id: a.id,
                  bank: a.bank
              }) AS transactions
            """
            with self.driver.session(database=self.database) as session:
                rec = session.run(query, user_id=user_id, merchant=merchant).single()
                if rec:
                    accounts = convert_dates([a for a in rec["accounts"] if a.get("id")])
                    all_matching_txs = convert_dates([t for t in rec["transactions"] if t.get("id")])
                    historical_count = rec["total_historical"]

                    if date_from and date_to:
                        period_txs = [
                            t for t in all_matching_txs
                            if t.get("date") and date_from <= str(t["date"])[:10] <= date_to
                        ]
                    else:
                        period_txs = all_matching_txs

                    grounded_data["accounts"] = accounts
                    grounded_data["transactions"] = period_txs
                    grounded_data["historical_match_count"] = historical_count

                    for a in accounts:
                        source_identifiers.append(f"Account:{a['id']}")
                        graph_paths.append(f"(User:{user_id})-[:HAS_ACCOUNT]->(Account:{a['id']})")
                    for t in period_txs:
                        source_identifiers.append(f"Transaction:{t['id']}")
                        graph_paths.append(f"(Account:{t.get('account_id')})-[:MADE_TRANSACTION]->(Transaction:{t['id']})")

        # 6. TOP_TRANSACTIONS: Filtered expenses ordered by amount
        elif intent == "TOP_TRANSACTIONS":
            amount_min = entities.get("amount_min")
            amount_max = entities.get("amount_max")
            query = """
            MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
            WHERE t.type = 'EXPENSE'
              AND ($date_from IS NULL OR date(t.date) >= date($date_from))
              AND ($date_to IS NULL OR date(t.date) <= date($date_to))
              AND ($amount_min IS NULL OR t.amount >= $amount_min)
              AND ($amount_max IS NULL OR t.amount <= $amount_max)
            OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)
            RETURN
              collect(DISTINCT {id: a.id, bank: a.bank, balance: a.balance}) AS accounts,
              collect({
                  id: t.id,
                  description: t.description,
                  amount: t.amount,
                  type: t.type,
                  date: t.date,
                  merchant: t.merchant,
                  category: c.name,
                  account_id: a.id,
                  bank: a.bank
              }) AS transactions
            """
            with self.driver.session(database=self.database) as session:
                rec = session.run(
                    query,
                    user_id=user_id,
                    date_from=date_from,
                    date_to=date_to,
                    amount_min=amount_min,
                    amount_max=amount_max,
                ).single()
                if rec:
                    accounts = convert_dates([a for a in rec["accounts"] if a.get("id")])
                    transactions = convert_dates([t for t in rec["transactions"] if t.get("id")])
                    grounded_data["accounts"] = accounts
                    grounded_data["transactions"] = transactions

                    for a in accounts:
                        source_identifiers.append(f"Account:{a['id']}")
                        graph_paths.append(f"(User:{user_id})-[:HAS_ACCOUNT]->(Account:{a['id']})")
                    for t in transactions:
                        source_identifiers.append(f"Transaction:{t['id']}")
                        graph_paths.append(f"(Account:{t.get('account_id')})-[:MADE_TRANSACTION]->(Transaction:{t['id']})")

        # 7. General Fallback (Expenses Breakdown, Health, Summary)
        else:
            ctx = self.get_financial_context(user_id)
            if ctx:
                grounded_data = ctx
                for a in ctx.get("accounts", []):
                    if a.get("id"):
                        source_identifiers.append(f"Account:{a['id']}")
                for l in ctx.get("loans", []):
                    if l.get("loan_id"):
                        source_identifiers.append(f"Loan:{l['loan_id']}")
                for i in ctx.get("incomes", []):
                    if i.get("id") or i.get("source"):
                        source_identifiers.append(f"Income:{i.get('id') or i.get('source')}")

        return {
            "user_id": user_id,
            "intent": intent,
            "grounded_entities": grounded_data,
            "source_identifiers": sorted(list(set(source_identifiers))),
            "graph_paths": sorted(list(set(graph_paths))),
            "context": grounded_data,
        }

    # ---------------------------------------------------------
    # Helper & Inquiry Methods
    # ---------------------------------------------------------

    def get_user_accounts(self, user_id: str):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        query = """
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)
        RETURN a.id AS id, a.bank AS bank, a.account_type AS account_type, a.balance AS balance
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            return [dict(record) for record in result]

    def get_all_transactions(self, user_id: str, limit=100):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        limit = max(1, min(1000, int(limit)))
        query = """
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
        OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)
        RETURN t.id AS id, t.description AS description, t.amount AS amount,
               t.type AS type, t.date AS date, c.name AS category, a.id AS account_id, a.bank AS bank
        ORDER BY t.date DESC
        LIMIT $limit
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id, limit=limit)
            return convert_dates([dict(record) for record in result])

    def get_categories(self):
        query = """
        MATCH (c:Category)
        RETURN c.id AS id, c.name AS name
        ORDER BY c.name ASC
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            return [dict(record) for record in result]

    # ---------------------------------------------------------
    # Dynamic Knowledge Graph CRUD Operations (Phase 1)
    # ---------------------------------------------------------

    def add_transaction(self, user_id: str, account_id=None, amount=0, description="", category_name="General", transaction_type="EXPENSE", date_str=None, fingerprint=None):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        if amount <= 0:
            raise ValueError(f"Transaction amount must be positive. Received: {amount}")

        if not date_str:
            date_str = date.today().isoformat()

        if not account_id:
            accounts = self.get_user_accounts(user_id)
            if not accounts:
                raise ValueError(f"No account found for user {user_id}")
            account_id = accounts[0]["id"]

        category_name = category_name.strip().title() if category_name else "General"
        transaction_id = f"T_{uuid.uuid4().hex[:8].upper()}"
        category_id = f"C_{uuid.uuid4().hex[:6].upper()}"

        if not fingerprint:
            from backend.app.services.fingerprint import compute_transaction_fingerprint
            fingerprint = compute_transaction_fingerprint(
                account_id=account_id,
                date_str=date_str,
                amount=amount,
                tx_type=transaction_type,
                description=description,
                occurrence_index=int(datetime.utcnow().timestamp() * 1000) % 1000000,
            )

        query = """
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account {id: $account_id})
        MERGE (c:Category {name: $category_name})
          ON CREATE SET c.id = $category_id

        CREATE (t:Transaction {
            id: $transaction_id,
            fingerprint: $fingerprint,
            description: $description,
            amount: $amount,
            type: $transaction_type,
            date: date($date_str)
        })

        CREATE (a)-[:MADE_TRANSACTION]->(t)
        CREATE (t)-[:BELONGS_TO]->(c)

        SET a.balance = a.balance + (CASE WHEN $transaction_type = 'INCOME' THEN $amount ELSE -$amount END)

        RETURN t.id AS transaction_id,
               t.fingerprint AS fingerprint,
               t.description AS description,
               t.amount AS amount,
               t.type AS type,
               t.date AS date,
               c.name AS category,
               a.id AS account_id,
               a.balance AS new_balance
        """

        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                user_id=user_id,
                account_id=account_id,
                category_name=category_name,
                category_id=category_id,
                transaction_id=transaction_id,
                fingerprint=fingerprint,
                description=description,
                amount=amount,
                transaction_type=transaction_type,
                date_str=date_str
            )
            record = result.single()
            if not record:
                raise ValueError(f"Failed to add transaction for user {user_id} and account {account_id}")

            return convert_dates(dict(record))

    def update_transaction(self, user_id, transaction_id, amount=None, description=None, category_name=None, date_str=None):
        find_query = """
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction {id: $transaction_id})
        OPTIONAL MATCH (t)-[r:BELONGS_TO]->(c:Category)
        RETURN t.amount AS old_amount, t.type AS type, a.id AS account_id, c.name AS old_category
        """
        with self.driver.session(database=self.database) as session:
            res = session.run(find_query, user_id=user_id, transaction_id=transaction_id).single()
            if not res:
                raise ValueError(f"Transaction with id '{transaction_id}' not found")
            old_amount = res["old_amount"]
            tx_type = res["type"]
            account_id = res["account_id"]

        amount_diff = 0
        if amount is not None:
            if amount <= 0:
                raise ValueError(f"Updated amount must be positive. Received: {amount}")
            amount_diff = amount - old_amount

        category_id = f"C_{uuid.uuid4().hex[:6].upper()}"

        update_query = """
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account {id: $account_id})-[:MADE_TRANSACTION]->(t:Transaction {id: $transaction_id})
        
        SET t.amount = CASE WHEN $amount IS NOT NULL THEN $amount ELSE t.amount END,
            t.description = CASE WHEN $description IS NOT NULL THEN $description ELSE t.description END,
            t.date = CASE WHEN $date_str IS NOT NULL THEN date($date_str) ELSE t.date END

        SET a.balance = a.balance - (CASE WHEN $tx_type = 'EXPENSE' THEN $amount_diff ELSE -$amount_diff END)

        WITH t, a
        CALL (t) {
            WITH t
            WHERE $category_name IS NOT NULL
            OPTIONAL MATCH (t)-[old_rel:BELONGS_TO]->(:Category)
            DELETE old_rel
            WITH t
            MERGE (new_c:Category {name: $category_name})
              ON CREATE SET new_c.id = $category_id
            MERGE (t)-[:BELONGS_TO]->(new_c)
            RETURN new_c.name AS final_category
        }

        OPTIONAL MATCH (t)-[:BELONGS_TO]->(c_current:Category)
        RETURN t.id AS transaction_id,
               t.description AS description,
               t.amount AS amount,
               t.type AS type,
               t.date AS date,
               c_current.name AS category,
               a.id AS account_id,
               a.balance AS new_balance
        """

        category_clean = category_name.strip().title() if category_name else None

        with self.driver.session(database=self.database) as session:
            result = session.run(
                update_query,
                transaction_id=transaction_id,
                user_id=user_id,
                account_id=account_id,
                amount=amount,
                amount_diff=amount_diff,
                tx_type=tx_type,
                description=description,
                date_str=date_str,
                category_name=category_clean,
                category_id=category_id
            )
            record = result.single()
            return convert_dates(dict(record))

    def delete_transaction(self, user_id, transaction_id):
        query = """
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction {id: $transaction_id})
        WITH a, t, t.amount AS amount, t.type AS type
        SET a.balance = a.balance + (CASE WHEN type = 'EXPENSE' THEN amount ELSE -amount END)
        DETACH DELETE t
        RETURN a.id AS account_id, a.balance AS restored_balance
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id, transaction_id=transaction_id)
            record = result.single()
            if not record:
                raise ValueError(f"Transaction with id '{transaction_id}' not found")
            return dict(record)

    def add_income(self, user_id: str, source="Salary", amount=0, date_str=None, account_id=None):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        if amount <= 0:
            raise ValueError(f"Income amount must be positive. Received: {amount}")

        if not date_str:
            date_str = date.today().isoformat()

        if not account_id:
            accounts = self.get_user_accounts(user_id)
            if accounts:
                account_id = accounts[0]["id"]

        income_id = f"I_{uuid.uuid4().hex[:8].upper()}"

        query = """
        MATCH (u:User {id: $user_id})
        CREATE (i:Income {
            id: $income_id,
            source: $source,
            amount: $amount,
            date: date($date_str)
        })
        CREATE (u)-[:RECEIVED_INCOME]->(i)

        WITH u, i
        OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account {id: $account_id})
        FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
            SET a.balance = a.balance + $amount
        )

        RETURN i.id AS income_id, i.source AS source, i.amount AS amount, i.date AS date
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                user_id=user_id,
                income_id=income_id,
                source=source,
                amount=amount,
                date_str=date_str,
                account_id=account_id
            )
            record = result.single()
            return convert_dates(dict(record))

    def add_or_update_goal(self, user_id: str, name="Emergency Fund", target_amount=100000, current_amount=None, target_date=None):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        goal_id = f"G_{uuid.uuid4().hex[:8].upper()}"
        query = """
        MATCH (u:User {id: $user_id})
        MERGE (u)-[:HAS_GOAL]->(g:Goal {name: $name})
          ON CREATE SET g.id = $goal_id,
                        g.target_amount = $target_amount,
                        g.current_amount = coalesce($current_amount, 0),
                        g.target_date = CASE WHEN $target_date IS NOT NULL THEN date($target_date) ELSE date('2027-01-01') END
          ON MATCH SET g.target_amount = $target_amount,
                       g.current_amount = CASE WHEN $current_amount IS NOT NULL THEN $current_amount ELSE g.current_amount END,
                       g.target_date = CASE WHEN $target_date IS NOT NULL THEN date($target_date) ELSE g.target_date END
        RETURN g.id AS id, g.name AS name, g.target_amount AS target_amount, g.current_amount AS current_amount, g.target_date AS target_date
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                user_id=user_id,
                goal_id=goal_id,
                name=name,
                target_amount=target_amount,
                current_amount=current_amount,
                target_date=target_date
            )
            record = result.single()
            return convert_dates(dict(record))

    def delete_goal(self, user_id: str, name="Emergency Fund"):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        query = """
        MATCH (u:User {id: $user_id})-[r:HAS_GOAL]->(g:Goal)
        WHERE toLower(g.name) = toLower($name)
        DELETE r, g
        RETURN count(g) AS deleted_count
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id, name=name)
            record = result.single()
            return {"deleted": record["deleted_count"] > 0 if record else False}

    def add_loan(self, user_id: str, name="Personal Loan", principal=0, outstanding=0):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        loan_id = f"L_{uuid.uuid4().hex[:8].upper()}"
        query = """
        MATCH (u:User {id: $user_id})
        CREATE (l:Loan {
            id: $loan_id,
            name: $name,
            principal: $principal,
            outstanding: $outstanding
        })
        CREATE (u)-[:HAS_LOAN]->(l)
        RETURN l.id AS id, l.name AS name, l.principal AS principal, l.outstanding AS outstanding
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                user_id=user_id,
                loan_id=loan_id,
                name=name,
                principal=principal,
                outstanding=outstanding
            )
            record = result.single()
            return dict(record)

    def add_emi(self, loan_id, amount=0, due_date=None, status="PENDING", user_id=None):
        emi_id = f"E_{uuid.uuid4().hex[:8].upper()}"
        if not due_date:
            due_date = date.today().isoformat()

        query = """
        MATCH (l:Loan {id: $loan_id})
        WHERE $user_id IS NULL OR EXISTS {
            MATCH (:User {id: $user_id})-[:HAS_LOAN]->(l)
        }
        CREATE (e:EMI {
            id: $emi_id,
            amount: $amount,
            due_date: date($due_date),
            status: $status
        })
        CREATE (l)-[:HAS_EMI]->(e)
        RETURN e.id AS id, e.amount AS amount, e.due_date AS due_date, e.status AS status
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query,
                loan_id=loan_id,
                emi_id=emi_id,
                amount=amount,
                due_date=due_date,
                status=status,
                user_id=user_id,
            )
            record = result.single()
            if not record:
                raise ValueError(f"Loan '{loan_id}' not found or unauthorized for user")
            return convert_dates(dict(record))

    def update_emi_status(self, emi_id, status="PAID", account_id=None, user_id=None):
        query = """
        MATCH (e:EMI {id: $emi_id})
        WHERE $user_id IS NULL OR EXISTS {
            MATCH (:User {id: $user_id})-[:HAS_LOAN]->(:Loan)-[:HAS_EMI]->(e)
        }
        SET e.status = $status
        WITH e
        OPTIONAL MATCH (a:Account {id: $account_id})
        WHERE $user_id IS NULL OR EXISTS {
            MATCH (:User {id: $user_id})-[:HAS_ACCOUNT]->(a)
        }
        FOREACH (_ IN CASE WHEN a IS NOT NULL AND $status = 'PAID' THEN [1] ELSE [] END |
            SET a.balance = a.balance - e.amount
        )
        RETURN e.id AS id, e.amount AS amount, e.status AS status
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, emi_id=emi_id, status=status, account_id=account_id, user_id=user_id)
            record = result.single()
            if not record:
                raise ValueError(f"EMI '{emi_id}' not found or unauthorized for user")
            return dict(record)

    def update_account_balance(self, account_id, new_balance, user_id=None):
        query = """
        MATCH (a:Account {id: $account_id})
        WHERE $user_id IS NULL OR EXISTS {
            MATCH (:User {id: $user_id})-[:HAS_ACCOUNT]->(a)
        }
        SET a.balance = $new_balance
        RETURN a.id AS id, a.bank AS bank, a.balance AS balance
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, account_id=account_id, new_balance=new_balance, user_id=user_id)
            record = result.single()
            if not record:
                raise ValueError(f"Account '{account_id}' not found or unauthorized for user")
            return dict(record)

    def create_user(self, username, password, name=None, initial_balance=0.0, bank_name="Primary Bank"):
        clean_username = username.strip().lower()
        display_name = name.strip() if name and name.strip() else clean_username.capitalize()
        pwd_hash, salt = hash_password(password)
        user_id = f"U_{uuid.uuid4().hex[:8].upper()}"
        account_id = f"A_{uuid.uuid4().hex[:8].upper()}"

        check_query = "MATCH (u:User) WHERE toLower(u.username) = $username RETURN u.id AS id"
        with self.driver.session(database=self.database) as session:
            existing = session.run(check_query, username=clean_username).single()
            if existing:
                raise ValueError("Username already exists")

            create_query = """
            CREATE (u:User {
                id: $user_id,
                username: $username,
                name: $name,
                password_hash: $pwd_hash,
                salt: $salt,
                created_at: date()
            })
            CREATE (a:Account {
                id: $account_id,
                bank: $bank_name,
                account_type: 'Savings',
                balance: $initial_balance
            })
            CREATE (u)-[:HAS_ACCOUNT]->(a)

            MERGE (c1:Category {name: 'Housing'}) ON CREATE SET c1.id = 'C001'
            MERGE (c2:Category {name: 'Food'}) ON CREATE SET c2.id = 'C002'
            MERGE (c3:Category {name: 'Transport'}) ON CREATE SET c3.id = 'C003'
            MERGE (c4:Category {name: 'Utilities'}) ON CREATE SET c4.id = 'C004'
            MERGE (c5:Category {name: 'Shopping'}) ON CREATE SET c5.id = 'C005'
            MERGE (c6:Category {name: 'Healthcare'}) ON CREATE SET c6.id = 'C006'
            MERGE (c7:Category {name: 'Entertainment'}) ON CREATE SET c7.id = 'C007'

            RETURN u.id AS user_id, u.username AS username, u.name AS name, a.id AS account_id, a.balance AS balance
            """
            result = session.run(
                create_query,
                user_id=user_id,
                username=clean_username,
                name=display_name,
                pwd_hash=pwd_hash,
                salt=salt,
                account_id=account_id,
                bank_name=bank_name,
                initial_balance=float(initial_balance)
            )
            record = result.single()
            return dict(record)

    def authenticate_user(self, username, password):
        clean_username = username.strip().lower()
        query = """
        MATCH (u:User)
        WHERE toLower(u.username) = $username OR toLower(u.name) = $username
        RETURN u.id AS user_id, u.username AS username, u.name AS name, u.password_hash AS password_hash, u.salt AS salt
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, username=clean_username)
            record = result.single()
            if not record:
                return None
            user = dict(record)
            if user.get("password_hash") and user.get("salt"):
                if verify_password(password, user["password_hash"], user["salt"]):
                    return {
                        "user_id": user["user_id"],
                        "username": user.get("username") or user["name"],
                        "name": user["name"]
                    }
                return None
            return None

    def get_user_by_id(self, user_id):
        query = """
        MATCH (u:User {id: $user_id})
        RETURN u.id AS user_id, u.username AS username, u.name AS name
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id)
            record = result.single()
            if record:
                return dict(record)
            return None

    def init_schema_constraints(self, strict: bool = False) -> dict[str, str]:
        """
        Idempotently ensure unique constraints and performance indexes exist.

        Parameters
        ----------
        strict : bool, default False
            If True, re-raises any unexpected Neo4j execution error so callers
            (such as migration scripts or test suites) fail fast.
            If False, logs detailed errors and returns a status dictionary.

        Returns
        -------
        dict[str, str]
            Map of query string to outcome status ('CREATED_OR_EXISTS' or 'FAILED: <reason>').
        """
        queries = [
            "CREATE CONSTRAINT txn_fp IF NOT EXISTS FOR (t:Transaction) REQUIRE t.fingerprint IS UNIQUE",
            "CREATE CONSTRAINT txn_id_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT merchant_norm IF NOT EXISTS FOR (m:Merchant) REQUIRE m.normalized IS UNIQUE",
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT user_username_unique IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
            "CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
            "CREATE INDEX txn_date_idx IF NOT EXISTS FOR (t:Transaction) ON (t.date)",
            "CREATE INDEX txn_amount_idx IF NOT EXISTS FOR (t:Transaction) ON (t.amount)",
        ]
        results: dict[str, str] = {}
        with self.driver.session(database=self.database) as session:
            for q in queries:
                try:
                    session.run(q)
                    results[q] = "CREATED_OR_EXISTS"
                    logger.debug("Schema constraint/index verified: %s", q)
                except Exception as exc:
                    err_msg = str(exc)
                    results[q] = f"FAILED: {err_msg}"
                    logger.error("Failed to apply schema constraint/index '%s': %s", q, err_msg)
                    if strict:
                        raise
        return results

    def batch_check_duplicates(self, user_id: str, candidate_rows: list[dict]) -> dict[int, list[dict]]:
        """
        Batch-check candidate rows against existing transactions in Neo4j.
        Runs ONE single Cypher query with UNWIND instead of N queries in a loop.
        """
        if not candidate_rows:
            return {}

        query = """
        UNWIND $candidates AS c
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(:Account)-[:MADE_TRANSACTION]->(t:Transaction)
        WHERE (t.fingerprint IS NOT NULL AND t.fingerprint = c.fingerprint)
           OR (c.source_ref IS NOT NULL AND t.source_ref = c.source_ref)
           OR (
                c.amount > 0
                AND abs(t.amount - c.amount) < 0.001
                AND t.type = c.type
                AND date(t.date) >= date(c.date_from)
                AND date(t.date) <= date(c.date_to)
           )
        RETURN c.row_index AS row_index,
               t.id AS id,
               t.description AS description,
               t.amount AS amount,
               t.date AS date,
               t.source_ref AS source_ref,
               (CASE WHEN t.fingerprint IS NOT NULL AND t.fingerprint = c.fingerprint THEN 'EXACT_FINGERPRINT'
                     WHEN c.source_ref IS NOT NULL AND t.source_ref = c.source_ref THEN 'EXACT_REF'
                     ELSE 'HEURISTIC' END) AS match_reason
        """
        candidates = []
        for i, r in enumerate(candidate_rows):
            d_str = r.get("date") or date.today().isoformat()
            try:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                d_from = (d_obj - timedelta(days=2)).isoformat()
                d_to = (d_obj + timedelta(days=2)).isoformat()
            except Exception:
                d_from, d_to = d_str, d_str

            amt = float(r.get("amount") or 0.0)
            candidates.append({
                "row_index": i,
                "fingerprint": r.get("fingerprint"),
                "source_ref": r.get("source_ref"),
                "amount": amt,
                "type": (r.get("type") or "EXPENSE").upper(),
                "date_from": d_from,
                "date_to": d_to,
            })

        matches_by_row: dict[int, list[dict]] = {}
        with self.driver.session(database=self.database) as session:
            result = session.run(query, user_id=user_id, candidates=candidates)
            for rec in result:
                idx = rec["row_index"]
                d = dict(rec)
                if isinstance(d.get("date"), Date):
                    d["date"] = d["date"].iso_format()
                matches_by_row.setdefault(idx, []).append(d)

        return matches_by_row

    def batch_add_transactions(
        self,
        user_id: str,
        account_id: str | None = None,
        rows: list[dict] | None = None,
        import_id: str | None = None,
    ) -> dict:
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        """
        Idempotent bulk transaction ingestion via Cypher UNWIND and managed transactions.
        
        Guarantees:
        1. Repeated imports of the same batch or transaction will NEVER create duplicates
           or double-apply balance changes.
        2. In-batch duplicate rows (same fingerprint) are deduplicated so balance is updated
           only once per unique transaction.
        3. Only genuinely newly created transactions contribute to net_balance_delta and
           account balance updates.
        4. Atomic execution: all graph writes and balance updates commit together in a single
           managed write transaction, preventing partial state corruption.
        5. Concurrency safety: acquires an exclusive write lock on the target account node
           to serialize concurrent balance updates.
        6. Missing fingerprints are computed deterministically rather than generating random UUIDs.
        """
        if not rows:
            return {
                "import_id": import_id or f"IMP_{uuid.uuid4().hex[:8].upper()}",
                "total": 0,
                "inserted": 0,
                "skipped": 0,
                "net_balance_delta": 0.0,
                "new_balance": 0.0,
            }

        if not account_id:
            accounts = self.get_user_accounts(user_id)
            if not accounts:
                raise ValueError(f"No account found for user {user_id}")
            account_id = accounts[0]["id"]

        import_id = import_id or f"IMP_{uuid.uuid4().hex[:8].upper()}"

        from backend.app.services.fingerprint import compute_transaction_fingerprint
        from backend.app.services.merchant_normalizer import normalize_narration

        occurrence_counter: Counter = Counter()
        seen_fingerprints: set[str] = set()
        prepared = []

        for r in rows:
            tx_type = (r.get("type") or "EXPENSE").upper()
            amt = round(float(r["amount"]), 2)
            desc = r.get("description") or "Imported transaction"
            date_str = str(r["date"])
            source_ref = r.get("source_ref")

            merchant_raw = r.get("clean_merchant")
            if not merchant_raw:
                try:
                    norm = normalize_narration(desc, tx_type)
                    merchant_raw = norm.clean_merchant
                except Exception:
                    merchant_raw = desc or "Unknown"
            merchant_norm = merchant_raw.strip().lower()

            fp = r.get("fingerprint")
            if not fp:
                tuple_key = (date_str, amt, tx_type, merchant_raw.lower(), str(source_ref or "").lower())
                occ = occurrence_counter[tuple_key]
                occurrence_counter[tuple_key] += 1
                fp = compute_transaction_fingerprint(
                    account_id=account_id,
                    date_str=date_str,
                    amount=amt,
                    tx_type=tx_type,
                    description=merchant_raw,
                    source_ref=source_ref,
                    occurrence_index=occ,
                )

            # Deduplicate rows with identical fingerprints within the batch
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)

            prepared.append({
                "id": r.get("id") or f"T_{uuid.uuid4().hex[:8].upper()}",
                "fingerprint": fp,
                "date": date_str,
                "amount": amt,
                "type": tx_type,
                "description": desc,
                "category": (r.get("category") or "General").strip().title(),
                "category_id": f"C_{uuid.uuid4().hex[:6].upper()}",
                "category_source": r.get("category_source") or "default",
                "merchant_raw": merchant_raw,
                "merchant_norm": merchant_norm,
                "source_ref": source_ref,
                "source_type": r.get("source_type") or "csv",
            })

        query = """
        MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account {id: $account_id})

        // Acquire exclusive write lock on account node to serialize concurrent imports for this account
        SET a._lock = true
        REMOVE a._lock

        MERGE (imp:ImportBatch {id: $import_id})
          ON CREATE SET imp.created_at = datetime(), imp.row_count = size($rows)

        UNWIND $rows AS r
        MERGE (c:Category {name: r.category})
          ON CREATE SET c.id = r.category_id

        MERGE (m:Merchant {normalized: r.merchant_norm})
          ON CREATE SET m.name = r.merchant_raw

        MERGE (t:Transaction {fingerprint: r.fingerprint})
          ON CREATE SET
            t.id = r.id,
            t.amount = r.amount,
            t.date = date(r.date),
            t.type = r.type,
            t.description = r.description,
            t.category_source = r.category_source,
            t.source_ref = r.source_ref,
            t.source_type = r.source_type,
            t.import_id = $import_id,
            t.created_at = datetime(),
            t._batch_id = $import_id
          ON MATCH SET
            t._batch_id = null

        MERGE (a)-[:MADE_TRANSACTION]->(t)
        MERGE (t)-[:BELONGS_TO]->(c)
        MERGE (t)-[:AT]->(m)
        MERGE (imp)-[:INCLUDES]->(t)

        WITH a, collect(DISTINCT t) AS all_distinct_txns
        WITH a, [t IN all_distinct_txns WHERE t._batch_id = $import_id] AS new_txns
        FOREACH (t IN new_txns | REMOVE t._batch_id)

        WITH a, size(new_txns) AS inserted_count,
             reduce(s = 0.0, nt IN new_txns | s + (CASE WHEN nt.type = 'INCOME' THEN nt.amount ELSE -nt.amount END)) AS net_delta

        SET a.balance = a.balance + net_delta
        RETURN inserted_count, net_delta, a.balance AS new_balance
        """

        def _execute_write_tx(tx):
            res = tx.run(
                query,
                user_id=user_id,
                account_id=account_id,
                import_id=import_id,
                rows=prepared,
            )
            rec = res.single()
            if not rec:
                raise ValueError(
                    f"Account '{account_id}' for user '{user_id}' was not found; import aborted."
                )
            return rec

        with self.driver.session(database=self.database) as session:
            if hasattr(session, "execute_write"):
                record = session.execute_write(_execute_write_tx)
            else:
                record = _execute_write_tx(session)

            inserted = record["inserted_count"] if record else len(prepared)
            net_delta = record["net_delta"] if record else 0.0
            new_balance = record["new_balance"] if record else 0.0

        total_rows = len(rows)
        skipped = total_rows - inserted

        return {
            "import_id": import_id,
            "total": total_rows,
            "inserted": inserted,
            "skipped": skipped,
            "net_balance_delta": round(float(net_delta), 2),
            "new_balance": round(float(new_balance), 2),
        }

    def close(self):
        self.driver.close()


_shared_service_instance: Neo4jService | None = None


def get_neo4j_service(database: str | None = None) -> Neo4jService:
    """
    Lazy-initialized singleton Neo4jService instance for dependency injection.
    Eliminates redundant connection handshakes and enables mocking.
    """
    global _shared_service_instance
    if _shared_service_instance is None:
        _shared_service_instance = Neo4jService(database=database)
    return _shared_service_instance


def close_neo4j_service():
    """Cleanly close the shared Neo4j driver connection."""
    global _shared_service_instance
    if _shared_service_instance is not None:
        try:
            _shared_service_instance.close()
        except Exception:
            pass
        _shared_service_instance = None

