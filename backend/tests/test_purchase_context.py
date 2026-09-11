from backend.app.database.neo4j_service import Neo4jService

db = Neo4jService()
context = db.get_purchase_context("U001")
print("\nPurchase Context:")
print(context)
db.close()
