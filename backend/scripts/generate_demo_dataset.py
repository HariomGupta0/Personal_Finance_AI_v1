"""
Script to generate a realistic 3-month synthetic bank statement with 100+ transactions
specifically tailored for demonstrations of the Personal Finance AI Assistant.

Covers: August 2026, September 2026, and October 2026.
Contains:
- Monthly Salary Credits (₹65,000) & Freelance Income
- Essential Living: Sharma Housing Rent, BESCOM Electricity, ACT Fibernet, LPG Gas
- Daily Life: Swiggy, Zomato, Blinkit, Instamart, Zepto, BigBasket
- Commute: Uber, Ola, Bangalore Metro SmartCard, HPCL Petrol Pump
- Subscriptions: Netflix, Spotify, Amazon Prime, YouTube Premium
- Shopping & Discretionary: Amazon India, Flipkart, Myntra, Decathlon, Zara
- Healthcare: Apollo Pharmacy, Tata 1mg, Dr. Batra Clinic
- Loans & EMIs: HDFC Loan EMI (₹10,000 on the 10th of each month)
- Investment Dividends & Interest Credits
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

# Deterministic seed for reproducible demo data
random.seed(42)

START_BALANCE = 52400.00

# Fixed Recurring Monthly Events
RECURRING_MONTHLY = [
    # (day, desc, type, amount, category, ref_prefix)
    (1, "TechCorp Solutions Monthly Salary", "CREDIT", 68000.00, "Salary", "SAL"),
    (5, "Sharma Apartments Monthly House Rent", "DEBIT", 14000.00, "Housing", "NEFT"),
    (7, "ACT Fibernet High-Speed Broadband", "DEBIT", 1199.00, "Utilities", "BILL"),
    (8, "Airtel Postpaid Family Plan", "DEBIT", 999.00, "Utilities", "UPI"),
    (10, "HDFC Bank Personal Loan EMI", "DEBIT", 10000.00, "Loan", "ACH"),
    (12, "BESCOM Electricity Bill Payment", "DEBIT", 2340.00, "Utilities", "BILL"),
    (20, "Netflix Premium 4K Subscription", "DEBIT", 649.00, "Entertainment", "AUTO"),
    (22, "Spotify Individual Subscription", "DEBIT", 119.00, "Entertainment", "AUTO"),
    (28, "Indane LPG Gas Cylinder Booking", "DEBIT", 920.00, "Utilities", "BPAY"),
]

# Randomizable Daily Expense Pool
DAILY_TEMPLATES = [
    # Food & Dining
    ("Zomato Online Food Delivery", (280, 850), "Food"),
    ("Swiggy Gourmet Dinner", (350, 1100), "Food"),
    ("Blinkit Quick Grocery Delivery", (320, 1250), "Food"),
    ("Swiggy Instamart Daily Essentials", (250, 950), "Food"),
    ("Zepto 10-Min Grocery Store", (180, 650), "Food"),
    ("BigBasket Weekly Supermarket", (1800, 3400), "Food"),
    ("Starbucks Coffee & Snacks", (380, 750), "Food"),
    ("Blue Tokai Coffee Roasters", (260, 520), "Food"),
    ("Dominos Pizza Weekend Order", (550, 1200), "Food"),
    ("Third Wave Coffee Indiranagar", (290, 620), "Food"),
    ("Local Organic Vegetable Market", (250, 600), "Food"),
    
    # Transport & Commute
    ("Uber Auto / Cab Commute", (120, 480), "Transport"),
    ("Ola Cabs Airport Ride", (650, 1250), "Transport"),
    ("Bangalore Metro SmartCard Auto-Recharge", (500, 500), "Transport"),
    ("HPCL Petrol Pump Fuel Fill", (1500, 2800), "Transport"),
    ("Shell Fuel Station Premium Petrol", (1800, 3200), "Transport"),
    
    # Shopping
    ("Amazon India Marketplace Order", (450, 2800), "Shopping"),
    ("Flipkart Electronics & Gadgets", (890, 4200), "Shopping"),
    ("Myntra Fashion Apparel Order", (1200, 3600), "Shopping"),
    ("Decathlon Sports Gear", (750, 2400), "Shopping"),
    ("Uniqlo Casual Clothing", (1990, 4500), "Shopping"),
    ("Nykaa Personal Care & Grooming", (650, 1850), "Shopping"),
    
    # Healthcare
    ("Apollo Pharmacy Prescriptions", (320, 1450), "Healthcare"),
    ("Tata 1mg Diagnostic Tests", (700, 1800), "Healthcare"),
    ("MedPlus Wellness Medicines", (240, 850), "Healthcare"),
    
    # Entertainment & Social
    ("BookMyShow IMAX Movie Tickets", (600, 1400), "Entertainment"),
    ("Steam Game Digital Purchase", (499, 1999), "Entertainment"),
    ("Cult.fit Gym & Fitness Membership", (1800, 2200), "Healthcare"),
]

# Occasional Credits (Freelance, Cashback, Dividends)
OCCASIONAL_CREDITS = [
    ("Upwork Freelance UI Design Project", (12000, 22000), "Income"),
    ("Zerodha Stock Portfolio Dividend", (850, 2400), "Income"),
    ("Cred App Reward Cashback", (50, 250), "Income"),
    ("Mutual Fund Quarterly Capital Gains", (3500, 7500), "Income"),
]


def generate_dataset(output_path: Path):
    months = [
        (2026, 8, 31),  # August 2026
        (2026, 9, 30),  # September 2026
        (2026, 10, 16), # October 2026 (up to today)
    ]

    all_txs = []
    ref_counter = 1000

    for year, month, max_day in months:
        # 1. Add fixed recurring monthly events
        for day, desc, tx_type, amount, cat, ref_pref in RECURRING_MONTHLY:
            if day <= max_day:
                tx_date = date(year, month, day)
                ref_counter += 1
                all_txs.append({
                    "date": tx_date,
                    "description": desc,
                    "type": tx_type,
                    "amount": round(amount, 2),
                    "category": cat,
                    "ref": f"{ref_pref}{year}{month:02d}{ref_counter}",
                })

        # 2. Add occasional credits (1-2 per month)
        num_credits = random.randint(1, 2)
        credit_days = sorted(random.sample(range(12, max_day), num_credits))
        for c_day in credit_days:
            cred_template = random.choice(OCCASIONAL_CREDITS)
            tx_date = date(year, month, c_day)
            amt = round(random.uniform(cred_template[1][0], cred_template[1][1]), 2)
            ref_counter += 1
            all_txs.append({
                "date": tx_date,
                "description": cred_template[0],
                "type": "CREDIT",
                "amount": amt,
                "category": cred_template[2],
                "ref": f"REV{year}{month:02d}{ref_counter}",
            })

        # 3. Add realistic daily expenses (around 28-34 per month)
        num_daily = 30 if max_day >= 30 else 18
        for _ in range(num_daily):
            d_day = random.randint(1, max_day)
            tx_date = date(year, month, d_day)
            template = random.choice(DAILY_TEMPLATES)
            min_a, max_a = template[1]
            amt = round(random.uniform(min_a, max_a), 2)
            ref_counter += 1
            all_txs.append({
                "date": tx_date,
                "description": template[0],
                "type": "DEBIT",
                "amount": amt,
                "category": template[2],
                "ref": f"UPI{year}{month:02d}{ref_counter}",
            })

    # Sort chronologically
    all_txs.sort(key=lambda x: (x["date"], x["type"] == "CREDIT"))

    # Compute running balance
    curr_balance = START_BALANCE
    rows = []
    for tx in all_txs:
        if tx["type"] == "CREDIT":
            curr_balance += tx["amount"]
            debit_val = ""
            credit_val = f"{tx['amount']:.2f}"
        else:
            curr_balance -= tx["amount"]
            debit_val = f"{tx['amount']:.2f}"
            credit_val = ""

        rows.append({
            "Date": tx["date"].isoformat(),
            "Description": tx["description"],
            "Debit": debit_val,
            "Credit": credit_val,
            "Balance": f"{curr_balance:.2f}",
            "Reference": tx["ref"],
        })

    # Write CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance", "Reference"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} transactions across 3 months in: {output_path}")
    print(f"Starting Balance: Rs. {START_BALANCE:.2f} | Final Balance: Rs. {curr_balance:.2f}")
    return len(rows)



if __name__ == "__main__":
    root_dir = Path(__file__).resolve().parent.parent.parent
    demo_file = root_dir / "demo_bank_statement_3_months.csv"
    test_data_file = root_dir / "backend" / "tests" / "test-data" / "demo_bank_statement_3_months.csv"
    
    count = generate_dataset(demo_file)
    generate_dataset(test_data_file)
