from backend.app.database.neo4j_service import Neo4jService

db = Neo4jService()
context = db.get_financial_context("U001")
print(context)
db.close()
