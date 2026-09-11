from backend.app.database.neo4j_service import Neo4jService

db = Neo4jService()
context = db.get_savings_context("U001")
print("\nSavings Context:")
print(context)
db.close()
