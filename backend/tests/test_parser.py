from backend.app.nlu.question_parser import parse_question

questions = [
    "Can I spend ₹15,000 on a phone?",
    "Can I buy a laptop for 50000?",
    "How much am I saving?",
    "What is my savings rate?",
    "How much should my emergency fund be?",
    "How much emergency reserve do I need?",
    "Tell me something about my finances",
    "How is my financial health?",
    "What is my financial situation?",
    "Give me a financial summary",
    "How are my overall finances?"
]

for question in questions:
    result = parse_question(question)
    print("\nQuestion:", question)
    print("Parsed:", result)
