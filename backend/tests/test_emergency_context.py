from backend.app.database.neo4j_service import Neo4jService

db = Neo4jService()
context = db.get_emergency_fund_context("U001")
print("\nEmergency Fund Context:")
print(context)
db.close()
