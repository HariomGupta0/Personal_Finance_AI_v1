from backend.app.database.neo4j_service import Neo4jService
from backend.app.engine.financial_engine import generate_financial_summary

db = Neo4jService()
context = db.get_financial_context("U001")
summary = generate_financial_summary(context)
print("\nFinancial Summary:")
print(summary)
db.close()
