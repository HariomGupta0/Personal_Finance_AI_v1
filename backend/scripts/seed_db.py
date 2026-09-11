from neo4j import GraphDatabase
from backend.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

def seed_database():
    print(f"Connecting to Neo4j URI: {NEO4J_URI} on database: {NEO4J_DATABASE}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
    seed_cypher = """
    // Clean up existing data in this isolated database
    MATCH (n) DETACH DELETE n;
    """

    create_graph_cypher = """
    // Create User
    CREATE (u:User {id: 'U001', name: 'Rahul'})

    // Create Account
    CREATE (a:Account {
        id: 'A001',
        bank: 'Demo Bank',
        account_type: 'Savings',
        balance: 45000
    })
    CREATE (u)-[:HAS_ACCOUNT]->(a)

    // Create Categories
    CREATE (c1:Category {id: 'C001', name: 'Housing'})
    CREATE (c2:Category {id: 'C002', name: 'Food'})
    CREATE (c3:Category {id: 'C003', name: 'Transport'})
    CREATE (c4:Category {id: 'C004', name: 'Utilities'})

    // Create Transactions
    CREATE (t1:Transaction {
        id: 'T001',
        description: 'September Rent',
        amount: 12000,
        type: 'EXPENSE',
        date: date('2026-09-05')
    })
    CREATE (t2:Transaction {
        id: 'T002',
        description: 'Grocery Shopping',
        amount: 4000,
        type: 'EXPENSE',
        date: date('2026-09-07')
    })
    CREATE (t3:Transaction {
        id: 'T003',
        description: 'Bus/Auto Travel',
        amount: 2000,
        type: 'EXPENSE',
        date: date('2026-09-08')
    })
    CREATE (t4:Transaction {
        id: 'T004',
        description: 'Electricity Bill',
        amount: 3000,
        type: 'EXPENSE',
        date: date('2026-09-09')
    })

    // Link Transactions to Account and Categories
    CREATE (a)-[:MADE_TRANSACTION]->(t1)
    CREATE (t1)-[:BELONGS_TO]->(c1)

    CREATE (a)-[:MADE_TRANSACTION]->(t2)
    CREATE (t2)-[:BELONGS_TO]->(c2)

    CREATE (a)-[:MADE_TRANSACTION]->(t3)
    CREATE (t3)-[:BELONGS_TO]->(c3)

    CREATE (a)-[:MADE_TRANSACTION]->(t4)
    CREATE (t4)-[:BELONGS_TO]->(c4)

    // Create Income
    CREATE (i:Income {
        id: 'I001',
        source: 'Salary',
        amount: 60000,
        date: date('2026-09-01')
    })
    CREATE (u)-[:RECEIVED_INCOME]->(i)

    // Create Loan and EMI
    CREATE (l:Loan {
        id: 'L001',
        name: 'Personal Loan',
        principal: 200000,
        outstanding: 150000
    })
    CREATE (e:EMI {
        id: 'E001',
        amount: 10000,
        due_date: date('2026-09-10'),
        status: 'PENDING'
    })
    CREATE (u)-[:HAS_LOAN]->(l)
    CREATE (l)-[:HAS_EMI]->(e)

    // Create Goal
    CREATE (g:Goal {
        id: 'G001',
        name: 'Emergency Fund',
        target_amount: 100000,
        current_amount: 30000,
        target_date: date('2027-03-01')
    })
    CREATE (u)-[:HAS_GOAL]->(g)
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(seed_cypher)
        session.run(create_graph_cypher)
        print(f"Successfully seeded demo financial graph into database: '{NEO4J_DATABASE}'")

    driver.close()

if __name__ == "__main__":
    seed_database()
