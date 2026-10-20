"""Synthetic evidence for the bundled workflows (all names, accounts and numbers are fictional).

    uv run python examples/make_samples.py            # writes examples/ter-case/ and examples/rm-case/

ter-case/  a Trigger Event Report case (trade-based money-laundering pattern), as in ter-bank-multi-agent-flow-v15
rm-case/   a relationship-management wealth question (shared entities, liquidity, next-gen), as in AURA v3-3
"""

from __future__ import annotations

import csv
from email.message import EmailMessage
from pathlib import Path

import docx
import openpyxl
import pymupdf

HERE = Path(__file__).resolve().parent


def pdf(path: Path, title: str, body: str) -> None:
    doc = pymupdf.open()
    for i, chunk in enumerate(body.split("\f")):
        page = doc.new_page()
        html = (f"<h2>{title}</h2>" if i == 0 else "") + chunk
        page.insert_htmlbox(pymupdf.Rect(50, 50, 545, 790), html, css="* {font-family: sans-serif; font-size: 10pt}")
    doc.save(path)


def word(path: Path, title: str, sections: list[tuple[str, list[str]]], table: list[list[str]] | None = None) -> None:
    d = docx.Document()
    d.add_heading(title, 0)
    for heading, paras in sections:
        d.add_heading(heading, 1)
        for p in paras:
            d.add_paragraph(p[2:], style="List Bullet") if p.startswith("- ") else d.add_paragraph(p)
    if table:
        t = d.add_table(rows=0, cols=len(table[0]))
        for row in table:
            cells = t.add_row().cells
            for c, v in zip(cells, row):
                c.text = v
    d.save(path)


def workbook(path: Path, sheets: dict[str, list[list]]) -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    wb.save(path)


def mail(path: Path, sender: str, to: str, subject: str, date: str, body: str,
         attachments: list[Path] = ()) -> None:
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Date"] = sender, to, subject, date
    m.set_content(body)
    for a in attachments:
        sub = {"pdf": ("application", "pdf"), "docx": ("application",
               "vnd.openxmlformats-officedocument.wordprocessingml.document")}[a.suffix.lstrip(".")]
        m.add_attachment(a.read_bytes(), maintype=sub[0], subtype=sub[1], filename=a.name)
    path.write_bytes(bytes(m))


# ---------------------------------------------------------------------- TER case
def ter_case(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    word(d / "kyc_cdd_profile.docx", "KYC / CDD Customer Profile", [
        ("Customer", ["Customer name: Orchid Meridian Trading Pte. Ltd.", "Customer CIF: CIF-8842197",
                      "Incorporated: Singapore, 2019. Status: live company.",
                      "Sole director and shareholder: Elena Tan", "Ultimate beneficial owner: Tan Wei Ming"]),
        ("Nature of business", ["Declared nature of business: office stationery wholesaler (paper, toner, "
                                "filing products) serving retail chains in Singapore and Malaysia.",
                                "Expected activity: USD 45,000 per month, mainly domestic receipts from retailers.",
                                "Expected counterparties: Northstar Retail, Bright Arc Pte."]),
        ("Accounts", ["- SGD operating account 5952757454001, opened 18 Mar 2021",
                      "- LNS account 5012261745, opened 22 Sep 2022"]),
        ("Risk rating", ["Customer risk rating: Medium. Last periodic review: 14 Jan 2026."]),
    ])
    pdf(d / "commercial_invoice_OM-771.pdf", "COMMERCIAL INVOICE OM-771",
        "<p>Seller: Orchid Meridian Trading Pte. Ltd., 18 Kallang Way, Singapore<br>"
        "Buyer: Aster Peak FZE, Jebel Ali Free Zone, Dubai, UAE<br>Invoice date: 02 Jul 2026<br>"
        "Project reference: CNC-LINE-4</p>"
        "<table border='1'><tr><th>Description</th><th>Qty</th><th>Unit</th><th>Amount USD</th></tr>"
        "<tr><td>Premium copy paper A4 80gsm</td><td>8,100</td><td>cartons</td><td>486,000.00</td></tr></table>"
        "<p><b>Total: USD 486,000.00</b><br>Payment terms: see supply contract.</p>")
    pdf(d / "bill_of_lading_SG-9381.pdf", "BILL OF LADING SG-9381",
        "<p>Shipper: Orchid Meridian Trading Pte. Ltd.<br>Consignee: Aster Peak FZE, Dubai, UAE<br>"
        "Port of loading: Singapore. Port of discharge: Jebel Ali.<br>Vessel: MV Straits Harmony, "
        "on board 03 Jul 2026</p><p>Description of goods: CNC cutting equipment, eleven (11) crates, "
        "gross weight 14,300 kg.</p><p>Note: the cargo description box shows a correction (overwritten text).</p>")
    pdf(d / "customs_declaration_CD-2088.pdf", "CUSTOMS DECLARATION CD-2088",
        "<p>Exporter: Orchid Meridian Trading Pte. Ltd.<br>Declared value: USD 486,000<br>"
        "HS code: 8461.50 - machine tools for sawing or cutting-off metal<br>Destination: United Arab Emirates"
        "</p>")
    word(d / "supply_contract_aster_peak.docx", "Supply Contract", [
        ("Parties", ["Supplier: Orchid Meridian Trading Pte. Ltd. Buyer: Aster Peak FZE (director: Adrian Koh)."]),
        ("Terms", ["Goods: as per invoice. Payment terms: 90 days after delivery.",
                   "Governing law: Singapore. The contract has no delivery schedule, warranty or inspection clause."]),
    ])
    mail(d / "customer_explanation.eml", "Elena Tan <elena@orchidmeridian.example>",
         "RM Desk <rm.desk@bank.example>", "RE: Query on recent transactions", "Fri, 10 Jul 2026 09:12:00 +0800",
         "Dear RM team,\n\nThe USD 301,760 payment to Aster Peak FZE on 7 July is part of a regional copy-paper "
         "settlement. Aster Peak consolidates our paper purchases for the Gulf market.\n\nA credit note for the "
         "balance will follow next week. Please find the supply contract attached.\n\nRegards,\nElena Tan\n"
         "Director, Orchid Meridian Trading",
         [d / "supply_contract_aster_peak.docx"])
    (d / "supply_contract_aster_peak.docx").unlink()         # it only exists as the e-mail's attachment
    tx = [["Date", "Direction", "Counterparty", "Counterparty CIF", "Amount USD", "Reference"],
          ["2026-06-03", "IN", "Northstar Retail", "CIF-7712042", 38500, "INV-5521"],
          ["2026-06-18", "OUT", "Lotus Logistics", "", 42100, "FRT-0618"],
          ["2026-07-05", "IN", "Northstar Retail", "CIF-7712042", 182000, "T-871"],
          ["2026-07-06", "IN", "Bright Arc Pte", "CIF-6603189", 146000, "T-874"],
          ["2026-07-07", "OUT", "Aster Peak FZE", "", 301760, "T-882"],
          ["2026-07-09", "IN", "Northstar Retail", "CIF-7712042", 158000, "T-890"],
          ["2026-07-12", "OUT", "Payroll", "", 21400, "PAY-07"]]
    workbook(d / "account_statement_90d.xlsx", {"Transactions": tx,
             "Summary": [["Metric", "Value"], ["Period", "2026-04-01 to 2026-07-12"],
                         ["Inflow 01-08 Jul (USD)", 486000], ["Expected monthly activity (USD)", 45000]]})


# ---------------------------------------------------------------------- RM case
def rm_case(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    workbook(d / "crm_extract.xlsx", {
        "Clients": [["Client ID", "Name", "Segment", "Region", "AUM (SGD M)", "RM", "Risk profile", "Age"],
                    ["C-1001", "Eleanor Tan", "UHNW", "ASEAN", 64.0, "Gravu", "Balanced", 61],
                    ["C-1002", "Adrian Koh", "UHNW", "GCNA", 38.5, "KentC", "Growth", 55],
                    ["C-1003", "Mei Chen", "HNW", "ASEAN", 12.2, "Gravu", "Conservative", 47],
                    ["C-1004", "Emma Wong", "HNW", "ASEAN", 6.8, "Gravu", "Growth", 34]],
        "Relationships": [["From", "Relation", "To", "Source"],
                          ["Eleanor Tan", "spouse of", "Robert Tan (non-client)", "CRM declared"],
                          ["Emma Wong", "niece of", "Eleanor Tan", "CRM declared"],
                          ["Adrian Koh", "director of", "Koh Maritime Pte", "CRM declared"]]})
    word(d / "rm_meeting_note_eleanor_tan.docx", "RM Meeting Note - Eleanor Tan (C-1001)", [
        ("Meeting", ["Date: 12 Aug 2026. Attendees: Eleanor Tan, Gravu (RM).",
                     "Eleanor completed the sale of her 30% stake in Tan Precision Holdings; proceeds of about "
                     "SGD 28M arrived in late July.",
                     "About SGD 6M is earmarked for a property purchase and SGD 4M for a philanthropic gift.",
                     "She co-owns Orchid Holdings Ltd (BVI SPV) with Adrian Koh - not yet recorded in CRM.",
                     "She wants her niece Emma Wong involved in family wealth discussions from next year."]),
        ("Interests", ["- Private credit with quarterly income", "- Asia income funds",
                       "- No appetite for single-stock concentration"]),
        ("Follow-ups", ["- Introduce the private credit specialist", "- Confirm source-of-wealth documents for "
                        "the stake sale"]),
    ])
    pdf(d / "tan_family_trust_memorandum.pdf", "Tan Family Trust - Memorandum (extract)",
        "<p>Settlor: Eleanor Tan. Trustee: Meridian Trust Services (Singapore).<br>"
        "Beneficiaries: Emma Wong (niece), Lucas Wong (nephew).<br>Trust assets include 50% of Orchid Holdings "
        "Ltd (BVI); the remaining 50% is held by Adrian Koh.</p><p>Distribution clause: discretionary, with "
        "income distributions to beneficiaries from age 30.</p>")
    with (d / "t24_inflows.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerows([["value_date", "client_id", "client", "direction", "amount_sgd", "narrative"],
                     ["2026-07-24", "C-1001", "Eleanor Tan", "IN", 28000000, "Share sale proceeds TPH"],
                     ["2026-07-30", "C-1001", "Eleanor Tan", "OUT", 1500000, "Deposit - property"],
                     ["2026-08-02", "C-1002", "Adrian Koh", "IN", 7500000, "Dividend Koh Maritime"],
                     ["2026-08-05", "C-1003", "Mei Chen", "IN", 250000, "Salary and bonus"]])
    mail(d / "colleague_note_adrian_koh.eml", "KentC <kentc@bank.example>", "Gravu <gravu@bank.example>",
         "Adrian Koh - Orchid Holdings", "Mon, 17 Aug 2026 15:40:00 +0800",
         "Hi Gravu,\n\nFYI Adrian mentioned that he and Eleanor Tan are restructuring Orchid Holdings Ltd and may "
         "distribute part of the SPV's cash (around SGD 9M) later this year. He asked about bond ladders.\n\n"
         "Let's align before either of us pitches anything.\n\nKent")
    (d / "helios_news.html").write_text(
        "<html><body><h1>HELIOS news digest - 20 Aug 2026</h1>"
        "<p>Koh Maritime Pte named in a regional fuel-supply contract worth USD 40M (Straits Business Daily).</p>"
        "<p>Mei Chen appointed to the board of a state-linked utility; PEP screening may apply.</p>"
        "</body></html>", encoding="utf-8")


if __name__ == "__main__":
    ter_case(HERE / "ter-case")
    rm_case(HERE / "rm-case")
    for p in sorted([*(HERE / "ter-case").iterdir(), *(HERE / "rm-case").iterdir()]):
        print(p.relative_to(HERE))
