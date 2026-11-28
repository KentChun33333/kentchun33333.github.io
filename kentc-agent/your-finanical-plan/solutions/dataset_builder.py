"""
Generates complementary edge-case test fixtures in `dataset/` alongside the
real web-downloaded public financial PDFs so every system constraint is verified:

  1. personal_wealth_multisheet.xlsx   -> Multi-sheet cell-only Excel (no embedded images)
  2. highres_brokerage_2048px.png      -> 2048x2560 high-res image (tests 2048 -> 1024 resize + OCR)
  3. mixed_financial_bundle.pdf        -> Mixed doc types in one PDF (bank + investment + funding + insurance)
  4. scanned_insurance_65pages.pdf     -> 65-page scanned image-only insurance PDF (tests PaddleOCR triage <50s)

Run:
  .venv/bin/python -m solutions.dataset_builder
"""

from __future__ import annotations

import io
from pathlib import Path

import openpyxl
import pymupdf
from openpyxl.styles import Font, PatternFill
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"


def build_personal_excel(out_path: Path) -> None:
    wb = openpyxl.Workbook()

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

    def _populate(ws, rows):
        for r_idx, row in enumerate(rows, start=1):
            for c_idx, val in enumerate(row, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                if r_idx == 1:
                    cell.font = header_font
                    cell.fill = header_fill

    # Sheet 1: Public Equity & ETF Investments
    ws_inv = wb.active
    ws_inv.title = "Investments"
    _populate(
        ws_inv,
        [
            ["Ticker", "Asset Name", "Account", "Shares", "Avg Cost (USD)", "Market Price (USD)", "Market Value (USD)", "Unrealized P&L (USD)", "As Of Date"],
            ["NVDA", "NVIDIA Corp.", "Interactive Brokers", 420, 92.50, 141.80, 59556.00, 20706.00, "2026-10-31"],
            ["MSFT", "Microsoft Corp.", "Interactive Brokers", 160, 380.00, 448.25, 71720.00, 10920.00, "2026-10-31"],
            ["VOO", "Vanguard S&P 500 ETF", "Charles Schwab", 350, 462.10, 545.40, 190890.00, 29155.00, "2026-10-31"],
            ["QQQ", "Invesco QQQ Trust", "Charles Schwab", 210, 415.00, 512.00, 107520.00, 20370.00, "2026-10-31"],
            ["0700.HK", "Tencent Holdings Ltd.", "Futu HK", 1200, 345.00, 428.00, 513600.00, 99600.00, "2026-10-31"],
            ["TOTAL_USD_EQUITIES", "Total US Portfolio", "Consolidated", "", "", "", 429686.00, 81151.00, "2026-10-31"],
        ],
    )

    # Sheet 2: Private Startup Fundings & LP Commitments
    ws_fund = wb.create_sheet("Startup_Fundings")
    _populate(
        ws_fund,
        [
            ["Company / Fund", "Round / Vehicle", "Investment Amount", "Currency", "Pre-Money Valuation", "Ownership %", "Investment Date", "Status"],
            ["NovaAI Labs Inc.", "Series A Preferred", 150000, "USD", 24000000, "0.62%", "2025-06-15", "Active"],
            ["Helios Robotics", "Seed SAFE", 75000, "USD", 12000000, "0.63%", "2025-11-20", "Active"],
            ["Sequoia Asia Venture VII", "LP Capital Commitment", 500000, "USD", "", "", "2024-03-01", "60% Called ($300,000)"],
            ["QuantumGrid Energy", "Series B Co-Invest", 200000, "USD", 110000000, "0.18%", "2026-04-10", "Active"],
        ],
    )

    # Sheet 3: Bank Accounts
    ws_bank = wb.create_sheet("Bank_Accounts")
    _populate(
        ws_bank,
        [
            ["Bank Name", "Account Type", "Account Last 4", "Currency", "Ending Balance", "Monthly Interest", "APY %", "Statement Date"],
            ["HSBC Premier HK", "Multi-Currency Savings", "8821", "HKD", 1485200.50, 4210.30, "3.40%", "2026-10-31"],
            ["JPMorgan Chase", "Private Client Checking", "4419", "USD", 128450.75, 12.50, "0.12%", "2026-10-31"],
            ["DBS Treasures", "Fixed Deposit 6M", "3104", "SGD", 220000.00, 586.67, "3.20%", "2026-10-31"],
        ],
    )

    # Sheet 4: Insurance Policies
    ws_ins = wb.create_sheet("Insurance_Policies")
    _populate(
        ws_ins,
        [
            ["Insurer", "Policy Number", "Plan Type", "Currency", "Sum Assured", "Annual Premium", "Cash Value", "Surrender Value", "Maturity Year"],
            ["AIA Hong Kong", "AIA-99284710", "Whole Life Savings", "USD", 1000000, 18500, 142300, 136800, 2065],
            ["Prudential", "PRU-55192034", "Critical Illness", "HKD", 3500000, 28400, 195000, 182000, 2059],
            ["Chubb Global", "CHB-7741029", "Medical High-End", "USD", 5000000, 6200, 0, 0, 2027],
        ],
    )

    wb.save(out_path)


def build_highres_image_2048px(out_path: Path) -> None:
    """Create a 2048x2560 high-resolution brokerage & funding screenshot."""
    w, h = 2048, 2560
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 64)
        font_h2 = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 46)
        font_body = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 36)
    except Exception:
        font_title = ImageFont.load_default()
        font_h2 = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # Header banner
    draw.rectangle([(0, 0), (w, 190)], fill=(18, 42, 76))
    draw.text((80, 45), "APEX WEALTH BROKERAGE & PRIVATE HOLDINGS", fill=(255, 255, 255), font=font_title)
    draw.text((80, 125), "Statement Date: 2026-10-31  |  Account: APX-8842-910  |  Currency: USD", fill=(200, 220, 245), font=font_body)

    y = 250
    draw.text((80, y), "1. ACCOUNT SUMMARY", fill=(18, 42, 76), font=font_h2)
    y += 75
    summary_lines = [
        "Total Portfolio Market Value :  $1,248,920.00",
        "Total Cost Basis             :  $965,400.00",
        "Net Unrealized Gain          :  +$283,520.00 (+29.37%)",
        "Cash & Money Market Sweep    :  $84,320.00",
        "YTD Dividends Received       :  $14,680.50",
    ]
    for line in summary_lines:
        draw.text((100, y), line, fill=(25, 25, 25), font=font_body)
        y += 58

    y += 60
    draw.line([(80, y), (w - 80, y)], fill=(180, 190, 205), width=3)
    y += 50
    draw.text((80, y), "2. PUBLIC EQUITY & ETF POSITIONS", fill=(18, 42, 76), font=font_h2)
    y += 80

    eq_rows = [
        "TICKER    SHARES      PRICE       MARKET VALUE     COST BASIS",
        "---------------------------------------------------------------",
        "AAPL      600       $232.50       $139,500.00      $108,000.00",
        "GOOGL     850       $184.20       $156,570.00      $119,000.00",
        "TSM       900       $198.00       $178,200.00      $126,000.00",
        "BRK.B     400       $462.50       $185,000.00      $144,000.00",
        "TLT      1200        $96.50       $115,800.00      $122,400.00",
    ]
    for line in eq_rows:
        draw.text((100, y), line, fill=(20, 20, 20), font=font_body)
        y += 58

    y += 70
    draw.line([(80, y), (w - 80, y)], fill=(180, 190, 205), width=3)
    y += 50
    draw.text((80, y), "3. PRIVATE FUNDING ALLOCATIONS", fill=(18, 42, 76), font=font_h2)
    y += 80

    fund_rows = [
        "ENTITY               ROUND          INVESTED        VALUATION",
        "---------------------------------------------------------------",
        "Aether BioTech       Series B       $250,000.00    $85,000,000",
        "Strata Compute AI    Series A       $139,530.00    $32,000,000",
        "Total Private Funding Committed  :  $389,530.00",
    ]
    for line in fund_rows:
        draw.text((100, y), line, fill=(20, 20, 20), font=font_body)
        y += 58

    y += 120
    draw.text((80, y), "Image Resolution Verification: 2048 x 2560 px (downscaled to <=1024px in pipeline)", fill=(110, 110, 110), font=font_body)
    img.save(out_path, format="PNG")


def build_mixed_financial_pdf(out_path: Path) -> None:
    """Create a 4-page PDF mixing Bank Statement, Investments, Fundings, and Insurance."""
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out_path), pagesize=letter)
    story = []

    def _tbl(data):
        t = Table(data, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return t

    # Page 1: Bank Statement
    story.append(Paragraph("Page 1 — PACIFIC COMMERCIAL BANK STATEMENT", styles["Title"]))
    story.append(Paragraph("Statement Period: 2026-10-01 to 2026-10-31 | Account: Checking #5509-21", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(
        _tbl(
            [
                ["Account Metric", "Amount (USD)", "Notes"],
                ["Beginning Balance", "$64,210.40", "As of 2026-10-01"],
                ["Total Deposits & Credits", "$38,500.00", "Salary + Dividend Sweep"],
                ["Total Withdrawals & Debits", "$19,420.15", "Mortgage + Living Expenses"],
                ["Interest Earned", "$42.85", "APY 0.75%"],
                ["Ending Balance", "$83,333.10", "As of 2026-10-31"],
            ]
        )
    )
    story.append(PageBreak())

    # Page 2: Brokerage Investments
    story.append(Paragraph("Page 2 — GLOBAL SECURITIES INVESTMENT HOLDINGS", styles["Title"]))
    story.append(Paragraph("Portfolio Summary as of 2026-10-31 | Account: GS-77210", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(
        _tbl(
            [
                ["Ticker", "Security Name", "Shares", "Market Value (USD)", "Cost Basis (USD)"],
                ["AMZN", "Amazon.com Inc.", "300", "$63,900.00", "$48,600.00"],
                ["META", "Meta Platforms Inc.", "120", "$70,800.00", "$51,200.00"],
                ["BND", "Vanguard Total Bond ETF", "1,000", "$73,400.00", "$75,000.00"],
                ["TOTAL", "Total Investment Portfolio", "-", "$208,100.00", "$174,800.00"],
            ]
        )
    )
    story.append(PageBreak())

    # Page 3: Venture & Private Funding
    story.append(Paragraph("Page 3 — PRIVATE CAPITAL & STARTUP FUNDING SCHEDULE", styles["Title"]))
    story.append(Paragraph("Reporting Quarter: Q3 2026", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(
        _tbl(
            [
                ["Startup / Fund", "Round", "Investment Amount (USD)", "Post-Money Valuation", "Ownership"],
                ["DeepCore Silicon", "Series A", "$100,000.00", "$40,000,000.00", "0.25%"],
                ["Veridian Climate Fund II", "LP Commitment", "$250,000.00", "N/A (50% Called: $125,000)", "0.50%"],
            ]
        )
    )
    story.append(PageBreak())

    # Page 4: Insurance Policy Schedule
    story.append(Paragraph("Page 4 — METROPOLITAN LIFE INSURANCE POLICY SCHEDULE", styles["Title"]))
    story.append(Paragraph("Policy Number: ML-2024-88412 | Policy Effective Date: 2024-01-15", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(
        _tbl(
            [
                ["Benefit / Metric", "Amount (USD)", "Schedule Details"],
                ["Sum Assured (Death Benefit)", "$1,500,000.00", "Whole Life Core Coverage"],
                ["Annual Premium", "$14,200.00", "20-Year Payment Term"],
                ["Guaranteed Cash Value (Year 3)", "$24,600.00", "As of 2026-10-31"],
                ["Total Surrender Value", "$28,150.00", "Includes Non-Guaranteed Dividend"],
                ["Accidental Death Rider", "$500,000.00", "Additional Benefit"],
            ]
        )
    )

    doc.build(story)


def build_scanned_insurance_65pages(out_path: Path) -> None:
    """
    Create a realistic 65-page SCANNED (image-only, zero embedded text layer) insurance PDF:
      - Pages 1, 2, 3: Policy Schedule, Benefit Summary, Premium Schedule (high value)
      - Pages 4..59: Legal clauses, definitions, exclusions, general provisions (boilerplate)
      - Pages 60..62: Guaranteed & Non-Guaranteed Cash Value / Surrender Value Illustration Tables (high value)
      - Pages 63..65: Endorsements & Privacy Notice (boilerplate)
    """
    out_doc = pymupdf.open()

    try:
        font_h = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
        font_b = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 20)
    except Exception:
        font_h = ImageFont.load_default()
        font_b = ImageFont.load_default()

    # Pre-render 3 reusable boilerplate legal page JPEGs so generation is instant (<1s)
    boilerplate_jpegs = []
    boilerplate_topics = [
        ("SECTION: GENERAL PROVISIONS & LEGAL DEFINITIONS", "This policy contract constitutes the entire agreement between the insurer and the policyholder. Terms such as insured, owner, beneficiary, grace period, reinstatement, incontestability, and governing law are defined herein without monetary schedules."),
        ("SECTION: EXCLUSIONS, ARBITRATION & CLAIMS PROCEDURE", "No benefit shall be payable under circumstances excluded by statutory provisions. Written notice of claim must be submitted within the prescribed period. Any dispute arising under this contract shall be resolved in accordance with applicable jurisdiction regulations."),
        ("SECTION: POLICY ADMINISTRATION & PRIVACY NOTICE", "Personal data is collected solely for underwriting, administration, and regulatory compliance. Address changes, beneficiary designations, and assignment notices must be filed in writing at the home office. This section contains no financial benefit schedules."),
    ]
    for title, body in boilerplate_topics:
        im = Image.new("RGB", (800, 1024), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        dr.text((40, 45), title, fill=(30, 30, 30), font=font_h)
        y = 110
        for para in range(12):
            dr.text((40, y), f"Clause {para + 1}. {body[:72]}", fill=(60, 60, 60), font=font_b)
            dr.text((40, y + 26), f"          {body[72:144]}", fill=(60, 60, 60), font=font_b)
            y += 68
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=75)
        boilerplate_jpegs.append(buf.getvalue())

    def _render_key_page(title: str, lines: list[str]) -> bytes:
        im = Image.new("RGB", (850, 1024), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        dr.rectangle([(0, 0), (850, 95)], fill=(20, 52, 92))
        dr.text((35, 30), title, fill=(255, 255, 255), font=font_h)
        y = 135
        for ln in lines:
            dr.text((40, y), ln, fill=(15, 15, 15), font=font_b)
            y += 42
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    key_pages = {
        1: _render_key_page(
            "POLICY SCHEDULE — PACIFIC GUARDIAN LIFE",
            [
                "Policy Number         : PGL-2025-770912",
                "Policy Effective Date : 2025-03-01",
                "Maturity Date         : 2065-03-01",
                "Policy Currency       : USD",
                "Basic Sum Assured     : $2,000,000.00",
                "Annual Premium        : $24,800.00",
                "Premium Payment Term  : 15 Years",
                "Total Planned Premium : $372,000.00",
                "Policy Fee (Annual)   : $120.00",
            ],
        ),
        2: _render_key_page(
            "SCHEDULE OF BENEFITS & RIDERS",
            [
                "Benefit / Rider                      Coverage Limit    Annual Cost",
                "------------------------------------------------------------------",
                "Core Whole Life Death Benefit        $2,000,000.00     $21,500.00",
                "Critical Illness Accelerator Rider     $500,000.00      $2,100.00",
                "Accidental Death & Dismemberment       $750,000.00        $650.00",
                "Hospitalization Daily Cash Benefit         $400/day       $550.00",
                "Annual Deductible (Medical Rider)        $2,500.00          $0.00",
                "Total Combined Annual Premium                          $24,800.00",
            ],
        ),
        60: _render_key_page(
            "TABLE OF VALUES — GUARANTEED & SURRENDER VALUES",
            [
                "Policy Yr | Cumul. Premium | Guaranteed Cash | Total Surrender Value",
                "--------------------------------------------------------------------",
                "Year 5    |   $124,000.00  |    $78,400.00   |       $89,200.00",
                "Year 10   |   $248,000.00  |   $212,500.00   |      $264,800.00",
                "Year 15   |   $372,000.00  |   $388,000.00   |      $512,400.00",
                "Year 20   |   $372,000.00  |   $456,000.00   |      $718,900.00",
                "Year 30   |   $372,000.00  |   $610,000.00   |    $1,245,000.00",
            ],
        ),
        61: _render_key_page(
            "CURRENT POLICY VALUE STATEMENT (AS OF 2026-10-31)",
            [
                "Policy Number                 : PGL-2025-770912",
                "Total Premiums Paid To Date   : $49,600.00",
                "Current Guaranteed Cash Value : $18,250.00",
                "Accumulated Dividends         : $1,940.00",
                "Current Total Surrender Value : $20,190.00",
                "Outstanding Policy Loan       : $0.00",
                "Net Death Benefit             : $2,001,940.00",
            ],
        ),
    }

    for p_num in range(1, 66):
        jpeg = key_pages.get(p_num, boilerplate_jpegs[p_num % len(boilerplate_jpegs)])
        page = out_doc.new_page(width=612, height=792)
        page.insert_image(page.rect, stream=jpeg)

    out_doc.save(out_path, deflate=True)
    out_doc.close()


def build_messy_mixed_excel(out_path: Path) -> None:
    """
    Create a realistic MESSY personal Excel workbook:
      - Sheet 1 ('Master_Overview'): 3 mixed tables on ONE sheet!
          * Title banner at B2
          * Table 1 (B4:G9): Investments (Equities & ETFs)
          * Table 2 (I4:N8): SIDE-BY-SIDE Insurance Policies (separated by blank column H)
          * Table 3 (B13:G18): STACKED BELOW Private Fundings + Bank Balances
      - Sheet 2 ('Loans_And_Tax'): Offset liability table (C4:G7) + stacked Tax Summary (C11:E15)
    """
    wb = openpyxl.Workbook()
    hdr_font = Font(bold=True, color="FFFFFF")
    inv_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    ins_fill = PatternFill(start_color="8B1E24", end_color="8B1E24", fill_type="solid")
    mix_fill = PatternFill(start_color="1E6B52", end_color="1E6B52", fill_type="solid")

    def _write_block(ws, start_row: int, start_col: int, rows: list[list], fill):
        for r_off, row in enumerate(rows):
            for c_off, val in enumerate(row):
                cell = ws.cell(row=start_row + r_off, column=start_col + c_off, value=val)
                if r_off == 0:
                    cell.font = hdr_font
                    cell.fill = fill

    ws1 = wb.active
    ws1.title = "Master_Overview"
    ws1.cell(row=2, column=2, value="Kent Personal Wealth Tracker — As of 2026-10-31 (Mixed Sheet)")

    # Table 1 (B4:G9): Public Investments
    _write_block(
        ws1,
        4,
        2,
        [
            ["Ticker", "Broker", "Shares", "Avg Cost", "Market Value (USD)", "Unrealized P&L"],
            ["TSLA", "IBKR", 250, 210.00, 65750.00, 13250.00],
            ["AMZN", "IBKR", 400, 165.00, 85200.00, 19200.00],
            ["SPY", "Schwab", 300, 495.00, 177600.00, 29100.00],
            ["2800.HK", "Futu HK", 5000, 21.40, 124500.00, 17500.00],
            ["TOTAL_EQUITIES", "All Brokers", "", "", 453050.00, 79050.00],
        ],
        inv_fill,
    )

    # Table 2 (I4:N8): SIDE-BY-SIDE Insurance Policies (blank col H separates them!)
    _write_block(
        ws1,
        4,
        9,
        [
            ["Policy Number", "Insurer", "Currency", "Sum Assured", "Annual Premium", "Cash Value"],
            ["ML-884012", "Manulife", "USD", 1200000, 16400, 118500],
            ["AIA-772190", "AIA HK", "HKD", 4000000, 32000, 265000],
            ["SL-551029", "SunLife", "USD", 800000, 9800, 54200],
            ["TOTAL_INSURANCE_USD", "USD Policies", "USD", 2000000, 26200, 172700],
        ],
        ins_fill,
    )

    # Table 3 (B13:G18): STACKED BELOW — Private Fundings & Bank Accounts mixed together
    _write_block(
        ws1,
        13,
        2,
        [
            ["Category", "Institution / Startup", "Round / Account", "Currency", "Amount / Ending Balance", "Notes"],
            ["Funding", "Anthropic SPV II", "Series D SPV", "USD", 120000, "Post-money valuation $60B"],
            ["Funding", "Stripe Secondary", "Pre-IPO", "USD", 180000, "Valuation $70B"],
            ["Bank", "Citigold Private", "USD Checking #9041", "USD", 94320.50, "APY 0.50%"],
            ["Bank", "HSBC Premier HK", "HKD Savings #3310", "HKD", 860400.00, "APY 3.15%"],
            ["Bank", "UBS Singapore", "SGD Fixed Deposit", "SGD", 150000.00, "6M Term 3.25%"],
        ],
        mix_fill,
    )

    # Sheet 2: Offset Liability + Tax tables
    ws2 = wb.create_sheet("Loans_And_Tax")
    _write_block(
        ws2,
        4,
        3,
        [
            ["Liability", "Lender", "Currency", "Principal Balance", "Interest Rate %"],
            ["Home Mortgage", "HSBC HK", "HKD", 5420000, "3.625%"],
            ["Margin Facility", "IBKR", "USD", 42500, "5.83%"],
            ["Amex Centurion", "American Express", "USD", 8920.40, "0% (Auto-pay)"],
        ],
        ins_fill,
    )
    _write_block(
        ws2,
        11,
        3,
        [
            ["Tax Year 2025 Metric", "Currency", "Amount"],
            ["Gross Income", "HKD", 4850000],
            ["Taxable Income", "HKD", 4420000],
            ["Tax Paid", "HKD", 663000],
        ],
        inv_fill,
    )

    wb.save(out_path)


def main() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    build_personal_excel(DATASET_DIR / "personal_wealth_multisheet.xlsx")
    build_messy_mixed_excel(DATASET_DIR / "messy_mixed_tables_single_sheet.xlsx")
    build_highres_image_2048px(DATASET_DIR / "highres_brokerage_2048px.png")
    build_mixed_financial_pdf(DATASET_DIR / "mixed_financial_bundle.pdf")
    build_scanned_insurance_65pages(DATASET_DIR / "scanned_insurance_65pages.pdf")
    print("Generated 5 edge-case fixtures in:", DATASET_DIR)


if __name__ == "__main__":
    main()
