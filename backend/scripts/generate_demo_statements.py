"""
Generate 10 authentic Indian Bank Statement PDFs and 10 matching CSV files
for the Personal Finance AI project demonstration.

5 Diverse User Profiles:
1. Rahul Sharma (Software Engineer, Bengaluru) - HDFC Bank (High income, tech, investments)
2. Priya Nair (Homemaker & Family, Mumbai) - ICICI Bank (Family budgeting, groceries, utilities)
3. Arjun Mehta (Student / Intern, Pune) - State Bank of India (Micro UPI transactions, tight budget)
4. Sunita Devi (Freelance Designer, Jaipur) - Axis Bank (Irregular cash flow, business + personal)
5. Ramesh Iyer (Retired Pensioner, Chennai) - State Bank of India (Pension, healthcare, low debt)
"""

import os
import csv
import io
import random
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
import reportlab.pdfgen.canvas as pdf_canvas
import pypdf

# Base directory for demo statements
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo_statements"))
PDF_DIR = os.path.join(BASE_DIR, "pdfs")
CSV_DIR = os.path.join(BASE_DIR, "csvs")

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Profile Definitions & Transaction Templates
# ---------------------------------------------------------------------------

PROFILES = [
    {
        "id": "1_rahul_sharma",
        "name": "Rahul Sharma",
        "profession": "Lead Software Engineer",
        "city": "Bengaluru",
        "address": "Flat 402, Green Glen Layout, Bellandur, Bengaluru - 560103",
        "bank_name": "HDFC BANK LIMITED",
        "branch": "KORAMANGALA 4TH BLOCK (00234)",
        "ifsc": "HDFC0000234",
        "account_no": "xxxxxxxxxxxx4102",
        "cif_no": "xxxxxxxxxxxx891",
        "primary_color": colors.HexColor("#004c8f"),
        "accent_color": colors.HexColor("#06b6d4"),
        "pan": "RAHUL1234S",
        "initial_balance": 142500.00,
        "monthly_income": 95000.00,
        "income_desc": "NEFT*HDFC0001234*INFOSYS TECHNOLOGIES LTD*MONTHLY SALARY",
        "recurring_expenses": [
            ("01", "NEFT/HDFC00452/MANJUNATHA RENT/OCT-RENT", 28000.00, "Housing"),
            ("05", "ACH DR-ZERODHA BROKING LTD-MONTHLY SIP", 15000.00, "Investment"),
            ("07", "UPI/DR/603218765410/CRED/HDFC/cred.club@hdfc/CRED CC BILL", 12500.00, "Debt"),
            ("10", "UPI/DR/603245678901/BESCOM/UTIB/bescom.power@/UPI", 2150.00, "Utilities"),
            ("15", "UPI/DR/603289012345/ACT BROADBAND/ICIC/actbroadband@/UPI", 1199.00, "Utilities"),
        ],
        "variable_expense_pool": [
            ("UPI/DR/{rrn}/SWIGGY/{bank}/swiggyfood@/UPI", (240, 850), "Food"),
            ("UPI/DR/{rrn}/ZOMATO/{bank}/zomato.order@/UPI", (320, 950), "Food"),
            ("UPI/DR/{rrn}/UBER INDIA/{bank}/uber.ride@/UPI", (180, 560), "Transport"),
            ("UPI/DR/{rrn}/AMAZON/{bank}/amazonpay@/UPI", (499, 3499), "Shopping"),
            ("UPI/DR/{rrn}/MYNTRA/{bank}/myntra.pay@/UPI", (899, 2499), "Shopping"),
            ("UPI/DR/{rrn}/STARBUCKS/{bank}/starbucks.blr@/UPI", (350, 720), "Food"),
            ("UPI/DR/{rrn}/BLINKIT/{bank}/blinkit.groceries@/UPI", (350, 1450), "Food"),
            ("UPI/DR/{rrn}/NETFLIX/{bank}/netflix.sub@/UPI", (649, 649), "Entertainment"),
            ("UPI/DR/{rrn}/SPOTIFY/{bank}/spotify.music@/UPI", (119, 119), "Entertainment"),
            ("UPI/DR/{rrn}/CULT FIT/{bank}/cultfitness@/UPI", (1200, 1200), "Healthcare"),
        ]
    },
    {
        "id": "2_priya_nair",
        "name": "Priya Nair",
        "profession": "Homemaker & Family Budgeteer",
        "city": "Mumbai",
        "address": "B-304, Sea Breeze Towers, Powai, Mumbai - 400076",
        "bank_name": "ICICI BANK LIMITED",
        "branch": "POWAI CENTRAL (00142)",
        "ifsc": "ICIC0000142",
        "account_no": "xxxxxxxxxxxx7819",
        "cif_no": "xxxxxxxxxxxx429",
        "primary_color": colors.HexColor("#a52a2a"),
        "accent_color": colors.HexColor("#f59e0b"),
        "pan": "PRIYA1234N",
        "initial_balance": 48200.00,
        "monthly_income": 55000.00,
        "income_desc": "NEFT*ICIC0000142*VIKRAM NAIR*MONTHLY HOUSEHOLD EXP",
        "recurring_expenses": [
            ("02", "NEFT/ICIC00892/ORCHID INT SCHOOL/TERM FEES", 12500.00, "Education"),
            ("05", "ACH DR-ICICI PRUDENTIAL-RECURRING DEPOSIT", 10000.00, "Investment"),
            ("08", "UPI/DR/603299102456/MAHADISCOM/MSEDCL/msedcl@/UPI", 2850.00, "Utilities"),
            ("12", "UPI/DR/603345890123/JIO FIBER/JIOP/jiofiber.bill@/UPI", 999.00, "Utilities"),
            ("15", "UPI/DR/603399123456/ADANI GAS/ADAN/adanigas.mumbai@/UPI", 840.00, "Utilities"),
        ],
        "variable_expense_pool": [
            ("UPI/DR/{rrn}/DMART READY/{bank}/dmart.retail@/UPI", (1200, 3800), "Shopping"),
            ("UPI/DR/{rrn}/BIGBASKET/{bank}/bb.groceries@/UPI", (650, 2400), "Food"),
            ("UPI/DR/{rrn}/APOLLO PHARMACY/{bank}/apollopharmacy@/UPI", (250, 1150), "Healthcare"),
            ("UPI/DR/{rrn}/ZEPTO/{bank}/zepto.quick@/UPI", (180, 720), "Food"),
            ("UPI/DR/{rrn}/INDIAN OIL/{bank}/indianoil.fuel@/UPI", (500, 2000), "Transport"),
            ("UPI/DR/{rrn}/FIRSTCRY/{bank}/firstcry.retail@/UPI", (450, 1600), "Shopping"),
            ("UPI/DR/{rrn}/LOCAL VEGETABLES/{bank}/kirana.upi@/UPI", (80, 320), "Food"),
            ("UPI/DR/{rrn}/MILK BASKET/{bank}/milkbasket.dairy@/UPI", (60, 220), "Food"),
        ]
    },
    {
        "id": "3_arjun_mehta",
        "name": "Arjun Mehta",
        "profession": "MBA Student & Research Intern",
        "city": "Pune",
        "address": "Hostel Block C-14, Viman Nagar, Pune - 411014",
        "bank_name": "STATE BANK OF INDIA",
        "branch": "PUNE VIMAN NAGAR (06757)",
        "ifsc": "SBIN0006757",
        "account_no": "xxxxxxxxxxxx0982",
        "cif_no": "xxxxxxxxxxxx347",
        "primary_color": colors.HexColor("#0073b7"),
        "accent_color": colors.HexColor("#10b981"),
        "pan": "ARJUN1234M",
        "initial_balance": 8701.06,
        "monthly_income": 18000.00,
        "income_desc": "NEFT*SBIN0000123*TECH MAHINDRA LTD*INTERN STIPEND",
        "recurring_expenses": [
            ("01", "UPI/CR/100415802176/SANJAY MEHTA/SBIN/father@sbi/RENT AID", -3000.00, "Income"),
            ("04", "UPI/DR/603474682911/HOSTEL MESS/SBIN/messfees@/UPI", 4500.00, "Food"),
            ("08", "UPI/DR/603948259537/JIO MOBILITY/JIOP/prepaidrecharge@/UPI", 469.00, "Utilities"),
        ],
        "variable_expense_pool": [
            ("UPI/DR/{rrn}/ZOMATO/{bank}/zomatopune@/UPI", (120, 350), "Food"),
            ("UPI/DR/{rrn}/SWIGGY/{bank}/swiggy.camp@/UPI", (150, 380), "Food"),
            ("UPI/DR/{rrn}/RAPIDO BIKE/{bank}/rapidobike@/UPI", (35, 95), "Transport"),
            ("UPI/DR/{rrn}/NAGPUR METRO/{bank}/metrorail@/UPI", (15, 30), "Transport"),
            ("UPI/DR/{rrn}/CHAI POINT/{bank}/chaipoint@/UPI", (15, 45), "Food"),
            ("UPI/DR/{rrn}/CAMPUS CANTEEN/{bank}/canteenqr@/UPI", (25, 80), "Food"),
            ("UPI/DR/{rrn}/AMAZON BOOKS/{bank}/amazon.edu@/UPI", (299, 799), "Education"),
            ("UPI/DR/{rrn}/PHOTOCOPY SHOP/{bank}/xeroxcenter@/UPI", (10, 60), "Education"),
            ("UPI/DR/{rrn}/ZUDIO/{bank}/zudio.clothing@/UPI", (499, 999), "Shopping"),
            ("UPI/DR/{rrn}/BOOKMYSHOW/{bank}/bms.movies@/UPI", (180, 360), "Entertainment"),
        ]
    },
    {
        "id": "4_sunita_devi",
        "name": "Sunita Devi",
        "profession": "Freelance Fashion Designer & Boutique Owner",
        "city": "Jaipur",
        "address": "12, Rajputana Colony, C-Scheme, Jaipur - 302001",
        "bank_name": "AXIS BANK LIMITED",
        "branch": "JAIPUR C-SCHEME (00389)",
        "ifsc": "UTIB0000389",
        "account_no": "xxxxxxxxxxxx5561",
        "cif_no": "xxxxxxxxxxxx712",
        "primary_color": colors.HexColor("#861f41"),
        "accent_color": colors.HexColor("#06b6d4"),
        "pan": "SUNIT1234D",
        "initial_balance": 62400.00,
        "monthly_income": 35000.00,
        "income_desc": "UPI/CR/604512398765/FABINDIA CLIENT/HDFC/clientpay@/Payment",
        "recurring_expenses": [
            ("03", "NEFT/UTIB00192/JAIPUR TEXTILE HUB/FABRIC ROLL SUPPLY", 16500.00, "Shopping"),
            ("06", "UPI/DR/604812345678/BLUE DART COURIER/AIRP/bluedart@/UPI", 1499.00, "Transport"),
            ("10", "UPI/DR/605123456789/CANVA PTY LTD/UTIB/canva.sub@/UPI", 499.00, "Education"),
            ("14", "UPI/DR/605456789012/JVVNL ELECTRICITY/UTIB/jvvnl.power@/UPI", 2180.00, "Utilities"),
        ],
        "variable_expense_pool": [
            ("UPI/DR/{rrn}/LOCAL DYEING/{bank}/dyeworks@/UPI", (350, 1200), "Shopping"),
            ("UPI/DR/{rrn}/THREADS AND BUTTONS/{bank}/sewingstore@/UPI", (150, 650), "Shopping"),
            ("UPI/DR/{rrn}/IRCTC TRAIN TICKET/{bank}/irctc.travel@/UPI", (450, 1850), "Transport"),
            ("UPI/DR/{rrn}/FLIPKART/{bank}/flipkart.orders@/UPI", (650, 2200), "Shopping"),
            ("UPI/DR/{rrn}/SWIGGY/{bank}/swiggy.dine@/UPI", (220, 580), "Food"),
            ("UPI/DR/{rrn}/PETROL PUMP HPCL/{bank}/hpcl.fuel@/UPI", (500, 1500), "Transport"),
            ("UPI/DR/{rrn}/LOCAL BAKER/{bank}/bakeryqr@/UPI", (90, 250), "Food"),
        ]
    },
    {
        "id": "5_ramesh_iyer",
        "name": "Ramesh Iyer",
        "profession": "Retired Central Govt Officer",
        "city": "Chennai",
        "address": "No. 8, 4th Main Road, Gandhi Nagar, Adyar, Chennai - 600020",
        "bank_name": "STATE BANK OF INDIA",
        "branch": "CHENNAI ADYAR (00013)",
        "ifsc": "SBIN0000013",
        "account_no": "xxxxxxxxxxxx6642",
        "cif_no": "xxxxxxxxxxxx905",
        "primary_color": colors.HexColor("#0073b7"),
        "accent_color": colors.HexColor("#10b981"),
        "pan": "RAMES1234I",
        "initial_balance": 88400.00,
        "monthly_income": 38000.00,
        "income_desc": "PFM A032600574100 Credit Through PFMS/CENTRAL PENSION",
        "recurring_expenses": [
            ("02", "ACH DR-LIC OF INDIA-JEEVAN ANAND POLICY", 4250.00, "Investment"),
            ("05", "UPI/DR/606412345678/TNEB ELECTRICITY/SBIN/tneb.chennai@/UPI", 1680.00, "Utilities"),
            ("08", "UPI/DR/606823456789/AIRTEL BROADBAND/AIRP/airtelbroadband@/UPI", 799.00, "Utilities"),
            ("10", "UPI/DR/607134567890/APOLLO PHARMACY/SBIN/apollopharmacy@/UPI", 2850.00, "Healthcare"),
        ],
        "variable_expense_pool": [
            ("UPI/DR/{rrn}/DR LAL PATHLABS/{bank}/drlalpath@/UPI", (650, 1800), "Healthcare"),
            ("UPI/DR/{rrn}/AAVIN MILK BOOTH/{bank}/aavinmilk@/UPI", (45, 120), "Food"),
            ("UPI/DR/{rrn}/SARAVANA STORES/{bank}/saravanastores@/UPI", (450, 1600), "Shopping"),
            ("UPI/DR/{rrn}/SRI KRISHNA SWEETS/{bank}/krishnasweets@/UPI", (180, 450), "Food"),
            ("UPI/DR/{rrn}/LOCAL VEGETABLES/{bank}/kirana.qr@/UPI", (60, 240), "Food"),
            ("UPI/DR/{rrn}/AUTO RICKSHAW/{bank}/driver.upi@/UPI", (40, 110), "Transport"),
            ("UPI/DR/{rrn}/TEMPLE TRUST/{bank}/templedonation@/UPI", (101, 501), "General"),
        ]
    }
]


# ---------------------------------------------------------------------------
# Data Generation Helpers
# ---------------------------------------------------------------------------

def generate_transactions_for_profile(profile: Dict[str, Any], days: int = 90) -> List[Dict[str, Any]]:
    """
    Generate mathematically consistent chronological transactions ending today.
    """
    random.seed(profile["id"] + str(days))
    end_date = date(2026, 11, 20)
    start_date = end_date - timedelta(days=days)

    transactions = []
    current_balance = profile["initial_balance"]

    # Generate months within window
    current = start_date
    while current <= end_date:
        year = current.year
        month = current.month

        # 1. Monthly Primary Income (around 28th to 1st)
        income_day = 1 if profile["id"] in ("2_priya_nair", "5_ramesh_iyer") else 28
        try:
            inc_date = date(year, month, income_day)
            if start_date <= inc_date <= end_date:
                amount = profile["monthly_income"]
                current_balance += amount
                transactions.append({
                    "date": inc_date,
                    "desc": profile["income_desc"],
                    "debit": None,
                    "credit": amount,
                    "balance": current_balance,
                    "category": "Salary" if "SALARY" in profile["income_desc"] or "PENSION" in profile["income_desc"] else "Income"
                })
        except ValueError:
            pass

        # For Freelancer, add 2 additional mid-month client credits
        if profile["id"] == "4_sunita_devi":
            for extra_day, extra_amt in [(12, 22000.00), (22, 18500.00)]:
                try:
                    cdate = date(year, month, extra_day)
                    if start_date <= cdate <= end_date:
                        current_balance += extra_amt
                        transactions.append({
                            "date": cdate,
                            "desc": f"UPI/CR/{random.randint(600000000000, 699999999999)}/CLIENT BOUTIQUE/UTIB/client.pay@/Payment",
                            "debit": None,
                            "credit": extra_amt,
                            "balance": current_balance,
                            "category": "Income"
                        })
                except ValueError:
                    pass

        # 2. Recurring Monthly Expenses
        for day_str, desc, amt, cat in profile["recurring_expenses"]:
            try:
                rdate = date(year, month, int(day_str))
                if start_date <= rdate <= end_date:
                    if amt < 0:
                        # Negative means income credit
                        current_balance += abs(amt)
                        transactions.append({
                            "date": rdate,
                            "desc": desc,
                            "debit": None,
                            "credit": abs(amt),
                            "balance": current_balance,
                            "category": cat
                        })
                    else:
                        current_balance -= amt
                        transactions.append({
                            "date": rdate,
                            "desc": desc,
                            "debit": amt,
                            "credit": None,
                            "balance": current_balance,
                            "category": cat
                        })
            except ValueError:
                pass

        # Advance to next month
        if month == 12:
            current = date(year + 1, 1, 1)
        else:
            current = date(year, month + 1, 1)

    # 3. Variable Daily / Weekly Spends
    total_days = (end_date - start_date).days
    num_variable = int(total_days * 0.75)  # Roughly 1 transaction per 1.3 days

    for _ in range(num_variable):
        offset = random.randint(0, total_days)
        t_date = start_date + timedelta(days=offset)
        template, (min_amt, max_amt), cat = random.choice(profile["variable_expense_pool"])

        rrn = random.randint(603000000000, 649999999999)
        bank_code = random.choice(["YESB", "UTIB", "ICIC", "HDFC", "SBIN"])
        desc = template.format(rrn=rrn, bank=bank_code)

        amt = round(random.uniform(min_amt, max_amt), 2)
        if min_amt >= 100:
            amt = round(amt, -1)  # Nice rounded tens for larger amounts

        transactions.append({
            "date": t_date,
            "desc": desc,
            "debit": amt,
            "credit": None,
            "balance": 0.0,  # will be computed after sorting
            "category": cat
        })

    # Sort chronologically
    transactions.sort(key=lambda x: x["date"])

    # Re-calculate exact running balance from start
    running_bal = profile["initial_balance"]
    for t in transactions:
        if t["credit"]:
            running_bal += t["credit"]
        elif t["debit"]:
            running_bal -= t["debit"]
        t["balance"] = round(running_bal, 2)

    return transactions


# ---------------------------------------------------------------------------
# PDF Generation with ReportLab
# ---------------------------------------------------------------------------

class NumberedCanvas(pdf_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        footer_text = "**This is computer generated statement and does not require a signature.**"
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawCentredString(A4[0] / 2.0, 20, footer_text)
        self.drawRightString(A4[0] - 36, 20, page_str)
        self.restoreState()


def generate_pdf_statement(profile: Dict[str, Any], transactions: List[Dict[str, Any]], output_pdf_path: str):
    """
    Renders an authentic Indian bank statement PDF matching real e-statement layouts.
    """
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=28,
        rightMargin=28,
        topMargin=28,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    bank_title_style = ParagraphStyle(
        'BankTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=profile["primary_color"]
    )
    branch_style = ParagraphStyle(
        'BranchStyle',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#334155")
    )
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#1e293b")
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#334155")
    )
    cell_style = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor("#0f172a")
    )
    cell_desc_style = ParagraphStyle(
        'TableDescCell',
        fontName='Helvetica',
        fontSize=6.5,
        leading=8.0,
        textColor=colors.HexColor("#0f172a")
    )
    cell_amount_style = ParagraphStyle(
        'TableAmountCell',
        fontName='Helvetica',
        fontSize=6.8,
        leading=8.5,
        alignment=2,  # Right aligned
        textColor=colors.HexColor("#0f172a")
    )
    th_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9,
        textColor=colors.white
    )
    th_amount_style = ParagraphStyle(
        'TableHeaderAmount',
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9,
        alignment=2,
        textColor=colors.white
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph(f"<b>{profile['bank_name']}</b>", bank_title_style),
            Paragraph(f"<b>STATEMENT OF ACCOUNT</b><br/>{profile['branch']}", branch_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[320, 218])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    # 2. Account Metadata Box
    date_from = transactions[0]["date"].strftime("%d/%m/%Y")
    date_to = transactions[-1]["date"].strftime("%d/%m/%Y")
    closing_bal = transactions[-1]["balance"]

    account_info = [
        [
            Paragraph("<b>Account Name:</b>", meta_label_style),
            Paragraph(profile["name"], meta_val_style),
            Paragraph("<b>Statement Period:</b>", meta_label_style),
            Paragraph(f"{date_from} to {date_to}", meta_val_style),
        ],
        [
            Paragraph("<b>Account Number:</b>", meta_label_style),
            Paragraph(profile["account_no"], meta_val_style),
            Paragraph("<b>IFSC Code:</b>", meta_label_style),
            Paragraph(profile["ifsc"], meta_val_style),
        ],
        [
            Paragraph("<b>Customer Address:</b>", meta_label_style),
            Paragraph(profile["address"], meta_val_style),
            Paragraph("<b>Closing Balance:</b>", meta_label_style),
            Paragraph(f"<b>₹ {closing_bal:,.2f}</b>", meta_val_style),
        ],
        [
            Paragraph("<b>CIF No:</b>", meta_label_style),
            Paragraph(profile["cif_no"], meta_val_style),
            Paragraph("<b>Currency / Rate:</b>", meta_label_style),
            Paragraph("INR / 2.75% p.a.", meta_val_style),
        ]
    ]
    meta_table = Table(account_info, colWidths=[90, 180, 100, 168])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Transaction Table
    table_data = [
        [
            Paragraph("Txn Date", th_style),
            Paragraph("Value Date", th_style),
            Paragraph("Description", th_style),
            Paragraph("Debit (₹)", th_amount_style),
            Paragraph("Credit (₹)", th_amount_style),
            Paragraph("Balance (₹)", th_amount_style),
        ]
    ]

    for tx in transactions:
        d_str = tx["date"].strftime("%d/%m/%Y")
        debit_str = f"{tx['debit']:,.2f}" if tx["debit"] else ""
        credit_str = f"{tx['credit']:,.2f}" if tx["credit"] else ""
        bal_str = f"{tx['balance']:,.2f}"

        table_data.append([
            Paragraph(d_str, cell_style),
            Paragraph(d_str, cell_style),
            Paragraph(tx["desc"], cell_desc_style),
            Paragraph(debit_str, cell_amount_style),
            Paragraph(credit_str, cell_amount_style),
            Paragraph(bal_str, cell_amount_style),
        ])

    # Col widths sum to ~538 pt (matches A4 printable width with 28pt margins: 595 - 56 = 539)
    col_widths = [54, 54, 218, 68, 68, 76]
    txn_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    txn_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), profile["primary_color"]),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0, 1), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    story.append(txn_table)
    doc.build(story, canvasmaker=NumberedCanvas)


def encrypt_pdf(input_pdf_path: str, output_pdf_path: str, password: str):
    """
    Encrypts a generated PDF statement using standard AES-128 via pypdf.
    """
    reader = pypdf.PdfReader(input_pdf_path)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    with open(output_pdf_path, "wb") as f:
        writer.write(f)


def generate_csv_statement(transactions: List[Dict[str, Any]], output_csv_path: str):
    """
    Exports clean CSV compatible with csv_parser.py: Date,Description,Debit,Credit,Balance
    """
    with open(output_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Description", "Debit", "Credit", "Balance"])
        for tx in transactions:
            d_str = tx["date"].strftime("%d/%m/%Y")
            debit_val = f"{tx['debit']:.2f}" if tx["debit"] else ""
            credit_val = f"{tx['credit']:.2f}" if tx["credit"] else ""
            bal_val = f"{tx['balance']:.2f}"
            writer.writerow([d_str, tx["desc"], debit_val, credit_val, bal_val])


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("DEMO STATEMENT GENERATOR FOR PERSONAL FINANCE AI")
    print("Generating 10 Indian Bank Statement PDFs + 10 Matching CSVs")
    print("=" * 80)

    summary_rows = []

    for profile in PROFILES:
        pid = profile["id"]
        pname = profile["name"]
        bank = profile["bank_name"].split()[0]
        pan = profile["pan"]

        print(f"\n[+] Processing Profile: {pname} ({bank} - PAN: {pan})")

        # 1. Generate 90-day dataset (3 months)
        txs_90 = generate_transactions_for_profile(profile, days=90)
        
        # 2. Generate 60-day dataset (2 months - subset)
        txs_60 = [t for t in txs_90 if t["date"] >= (date(2026, 11, 20) - timedelta(days=60))]

        # File paths
        base_name_90 = f"{pid}_{bank.lower()}_3_months"
        base_name_60 = f"{pid}_{bank.lower()}_2_months"

        pdf_unencrypted = os.path.join(PDF_DIR, f"{base_name_90}.pdf")
        pdf_encrypted = os.path.join(PDF_DIR, f"{pid}_{bank.lower()}_password_protected.pdf")
        
        csv_90 = os.path.join(CSV_DIR, f"{base_name_90}.csv")
        csv_60 = os.path.join(CSV_DIR, f"{base_name_60}.csv")

        # Generate Unencrypted PDF
        generate_pdf_statement(profile, txs_90, pdf_unencrypted)
        print(f"    ✓ Generated PDF (Open): {os.path.basename(pdf_unencrypted)} ({len(txs_90)} txns)")

        # Generate Password-Protected PDF
        encrypt_pdf(pdf_unencrypted, pdf_encrypted, pan)
        print(f"    ✓ Generated PDF (Encrypted): {os.path.basename(pdf_encrypted)} (Password: {pan})")

        # Generate CSV files
        generate_csv_statement(txs_90, csv_90)
        generate_csv_statement(txs_60, csv_60)
        print(f"    ✓ Generated CSV (90-day): {os.path.basename(csv_90)} ({len(txs_90)} rows)")
        print(f"    ✓ Generated CSV (60-day): {os.path.basename(csv_60)} ({len(txs_60)} rows)")

        summary_rows.append({
            "Profile": pname,
            "Bank": bank,
            "Password (PAN)": pan,
            "90D Txns": len(txs_90),
            "60D Txns": len(txs_60),
            "Closing Balance": f"₹{txs_90[-1]['balance']:,.2f}"
        })

    # Create README reference for user and examiner
    readme_path = os.path.join(BASE_DIR, "README_DEMO_DATASETS.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# Demo Bank Statement Datasets & Profiles\n\n")
        f.write("Generated for Personal Finance AI project presentation and viva evaluation.\n\n")
        f.write("## 1. Profiles & Password Reference\n\n")
        f.write("| # | Profile Name | Bank | Lifestyle / Persona | PDF Password | 90-Day Txns | Closing Balance |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for i, s in enumerate(summary_rows, 1):
            f.write(f"| {i} | **{s['Profile']}** | {s['Bank']} | Lifestyle profile {i} | `{s['Password (PAN)']}` | {s['90D Txns']} | {s['Closing Balance']} |\n")
        f.write("\n## 2. Directory Structure\n\n")
        f.write("```\n")
        f.write("demo_statements/\n")
        f.write("├── pdfs/\n")
        f.write("│   ├── 1_rahul_sharma_hdfc_3_months.pdf (Unprotected)\n")
        f.write("│   ├── 1_rahul_sharma_hdfc_password_protected.pdf (Password: RAHUL1234S)\n")
        f.write("│   ├── 2_priya_nair_icici_3_months.pdf (Unprotected)\n")
        f.write("│   ├── 2_priya_nair_icici_password_protected.pdf (Password: PRIYA1234N)\n")
        f.write("│   ├── 3_arjun_mehta_sbi_3_months.pdf (Unprotected)\n")
        f.write("│   ├── 3_arjun_mehta_sbi_password_protected.pdf (Password: ARJUN1234M)\n")
        f.write("│   ├── 4_sunita_devi_axis_3_months.pdf (Unprotected)\n")
        f.write("│   ├── 4_sunita_devi_axis_password_protected.pdf (Password: SUNIT1234D)\n")
        f.write("│   ├── 5_ramesh_iyer_sbi_3_months.pdf (Unprotected)\n")
        f.write("│   └── 5_ramesh_iyer_sbi_password_protected.pdf (Password: RAMES1234I)\n")
        f.write("└── csvs/\n")
        f.write("    ├── 1_rahul_sharma_hdfc_3_months.csv\n")
        f.write("    ├── 1_rahul_sharma_hdfc_2_months.csv\n")
        f.write("    ├── 2_priya_nair_icici_3_months.csv\n")
        f.write("    ├── 2_priya_nair_icici_2_months.csv\n")
        f.write("    ├── 3_arjun_mehta_sbi_3_months.csv\n")
        f.write("    ├── 3_arjun_mehta_sbi_2_months.csv\n")
        f.write("    ├── 4_sunita_devi_axis_3_months.csv\n")
        f.write("    ├── 4_sunita_devi_axis_2_months.csv\n")
        f.write("    ├── 5_ramesh_iyer_sbi_3_months.csv\n")
        f.write("    └── 5_ramesh_iyer_sbi_2_months.csv\n")
        f.write("```\n")

    print("\n" + "=" * 80)
    print("SUCCESS: All 20 Files + README Generated in demo_statements/")
    print(f"Location: {BASE_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    main()
