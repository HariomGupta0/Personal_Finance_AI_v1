from backend.app.database.neo4j_service import Neo4jService

db = Neo4jService()
context = db.get_summary_context("U001")
print("\nSummary Context:")
print(context)
db.close()
