"""Long-task benchmark: an STR-style HTML report from a synthetic multi-format case file.

Each trial runs the kentc_agent runtime with a fixed workspace, prompt, tools and limits. The case holds KYC
profiles, RM notes, company registry extracts, trust deeds, account statements and media for 30-50 persons, well
beyond one context window. A planted network (key actor, money mules, a nominee director, two shell companies and
a trust) is masked behind abbreviated counterparty names, account numbers, shared contact details and an ID-only
trust beneficiary.
Decoys test precision: a name-alike, an adverse-media article that matches nobody, a legitimate family trust,
a high-volume business owner, a student with remittances and one explained cash deposit.

Grading is deterministic and per criterion (no all-or-nothing pass):
  A. overall picture   B. cross-identification of risk-linked parties   C. the HTML report in SG STR style.

    uv run --no-sync python examples/str_benchmark.py --self-check
    uv run --no-sync python examples/str_benchmark.py --output docs/str-benchmark-topics.json --repeats 1
"""
from __future__ import annotations

import argparse
import email.message
import hashlib
import json
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from compare_memory import Meter, peak_rss, totals

TOOLS = ("read", "bash", "write", "edit")
START, END = date(2026, 1, 1), date(2026, 6, 30)
TYPOLOGIES = ("structuring", "rapid_pass_through", "shell_company", "nominee_director", "layering_via_trust",
              "trade_based_money_laundering", "cuckoo_smurfing", "round_tripping", "pep_corruption",
              "terrorism_financing")
ROLES = ("key_actor", "money_mule", "nominee_director")
SECTIONS = ("summary", "subjects", "network", "transactions", "grounds", "recommendation")
FORBIDDEN = ("clearly", "obviously", "shocking", "criminal", "launderer", "fraudster", "guilty")
TIPPING_OFF = re.compile(r"\b(?:inform|notify|tell|alert|warn)\w*\s+(?:the\s+)?(?:customer|client|subject|account holder)s?\b",
                         re.I)
AMOUNT = re.compile(r"\bSGD \d{1,3}(?:,\d{3})*\.\d{2}\b")
SG_DATE = re.compile(r"\b\d{2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}\b")
ENTITY_ID = re.compile(r"\b(?:P\d{3}|C\d{2}|T\d{2})\b")
WEIGHTS = {"A_overall_picture": 0.25, "B_cross_identification": 0.45, "C_report": 0.30}

GIVEN = ["Wei Jie", "Hui Min", "Jun Hao", "Li Ting", "Kai Xiang", "Shu Fen", "Zhi Hao", "Xin Yi", "Jia Hui",
         "Yong Sheng", "Mei Ling", "Wen Jun"]
SURNAMES = ["Lim", "Tan", "Ng", "Lee", "Wong", "Goh", "Chua", "Koh", "Teo", "Ong", "Chan", "Yeo"]
ENGLISH = ["Daniel", "Rachel", "Bryan", "Joanne", "Kelvin", "Cheryl", "Gavin", "Michelle", "Ryan", "Vanessa"]
MALAY = ["Muhammad Faizal bin Rahman", "Nur Aisyah binte Ismail", "Ahmad Hafiz bin Osman", "Siti Nurhaliza binte Yusof",
         "Mohamed Irwan bin Salleh", "Farah Nadia binte Hassan"]
INDIAN = ["Arjun s/o Ramasamy", "Priya d/o Subramaniam", "Vikram s/o Gopal", "Kavitha d/o Krishnan",
          "Rajesh s/o Muthu", "Deepa d/o Selvam"]
STREETS = ["Tampines Street 21", "Bedok North Avenue 3", "Jurong West Street 52", "Ang Mo Kio Avenue 6",
           "Toa Payoh Lorong 4", "Clementi Avenue 2", "Yishun Ring Road", "Punggol Field", "Sengkang East Way",
           "Woodlands Drive 16", "Bukit Batok Street 31", "Pasir Ris Drive 1"]
JOBS = [("software engineer", 96_000), ("accountant", 78_000), ("nurse", 62_000), ("teacher", 70_000),
        ("logistics coordinator", 48_000), ("sales executive", 55_000), ("civil servant", 84_000),
        ("retail supervisor", 42_000), ("marketing manager", 110_000), ("lab technician", 52_000)]
BRANCHES = ["Tampines", "Jurong East", "Ang Mo Kio", "Bedok", "Woodlands", "Raffles Place"]


@dataclass
class Person:
    pid: str
    name: str
    nric: str
    dob: date
    nationality: str
    occupation: str
    employer: str
    income: int
    address: str
    mobile: str
    email: str
    account: str
    since: date
    risk: str = "Low"
    alt_mobile: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class Entity:
    eid: str
    name: str
    kind: str              # company | trust
    account: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Txn:
    day: date
    description: str
    counterparty: str
    counterparty_account: str
    amount: float          # positive credit, negative debit
    channel: str


@dataclass
class Truth:
    persons: int
    key_actor: str
    subjects: dict[str, str]
    entities: set[str]
    decoys: dict[str, str]
    typologies: set[str]
    placement_total: float
    period: tuple[date, date]
    files: list[str]


# --------------------------------------------------------------------------------------------- case generation
def _sgd(value: float) -> str:
    return f"SGD {value:,.2f}"


def _sg_date(value: date) -> str:
    return value.strftime("%d %b %Y")


class CaseBuilder:
    def __init__(self, persons: int, seed: int) -> None:
        if not 30 <= persons <= 50:
            raise ValueError("persons must be between 30 and 50")
        self.n, self.rng = persons, random.Random(seed)
        self.used: set[str] = set()
        self.ledgers: dict[str, list[Txn]] = {}

    def _unique(self, make: Any) -> str:
        while (value := make()) in self.used:
            pass
        self.used.add(value)
        return value

    def account(self) -> str:
        r = self.rng
        return self._unique(lambda: f"{r.randint(100, 999)}-{r.randint(100000, 999999)}-{r.randint(0, 9)}")

    def mobile(self) -> str:
        r = self.rng
        return self._unique(lambda: f"+65 {r.choice('89')}{r.randint(100, 999)} {r.randint(1000, 9999)}")

    def nric(self, foreign: bool = False) -> str:
        r = self.rng
        return self._unique(lambda: f"{'G' if foreign else 'S'}{r.randint(5_000_000, 9_999_999)}{r.choice('ABCDEFGHJZ')}")

    def address(self) -> str:
        r = self.rng
        return self._unique(lambda: f"Blk {r.randint(100, 899)} {r.choice(STREETS)}, #{r.randint(2, 18):02d}-"
                                    f"{r.randint(10, 450)}, Singapore {r.randint(310000, 829999)}")

    def name(self) -> str:
        r = self.rng
        def make() -> str:
            pick = r.random()
            if pick < 0.55:
                return f"{r.choice(ENGLISH)} {r.choice(SURNAMES)} {r.choice(GIVEN)}"
            if pick < 0.75:
                return f"{r.choice(SURNAMES)} {r.choice(GIVEN)}"
            return r.choice(MALAY if pick < 0.88 else INDIAN)
        return self._unique(make)

    def person(self, pid: str, **fixed: Any) -> Person:
        r = self.rng
        job, income = r.choice(JOBS)
        name = fixed.pop("name", None) or self.name()
        self.used.add(name)
        handle = re.sub(r"[^a-z]", "", name.lower().split()[0]) + str(r.randint(10, 99))
        values = dict(name=name, nric=self.nric(), dob=date(r.randint(1965, 2000), r.randint(1, 12), r.randint(1, 28)),
                      nationality="Singapore", occupation=job, employer=f"{r.choice(SURNAMES)} & Partners Pte. Ltd.",
                      income=income, address=self.address(), mobile=self.mobile(),
                      email=f"{handle}@{r.choice(['gmail.com', 'yahoo.com.sg', 'outlook.com'])}",
                      account=self.account(), since=date(r.randint(2008, 2023), r.randint(1, 12), 1))
        values.update(fixed)
        return Person(pid=pid, **values)

    def post(self, owner: str, txn: Txn) -> None:
        self.ledgers.setdefault(owner, []).append(txn)

    def transfer(self, day: date, payer: tuple[str, str, str], payee: tuple[str, str, str], amount: float,
                 description: str, channel: str = "FAST") -> None:
        """payer/payee: (ledger id or "", shown name, account)."""
        amount = round(amount, 2)
        if payer[0]:
            self.post(payer[0], Txn(day, description, payee[1], payee[2], -amount, channel))
        if payee[0]:
            self.post(payee[0], Txn(day, description, payer[1], payer[2], amount, channel))

    def routine(self, p: Person, monthly_salary: float | None = None) -> None:
        r = self.rng
        salary = monthly_salary if monthly_salary is not None else round(p.income / 12, -1)
        for month in range(1, 7):
            if salary:
                self.post(p.pid, Txn(date(2026, month, 25), "SALARY", p.employer.upper()[:24], "EMPLOYER-GIRO",
                                     salary, "GIRO"))
            self.post(p.pid, Txn(date(2026, month, 3), "HDB/RENTAL GIRO", "HDB", "HDB-COLLECTION",
                                 -round(r.uniform(450, 2400), 2), "GIRO"))
            self.post(p.pid, Txn(date(2026, month, 12), "SP SERVICES UTILITIES", "SP GROUP", "SPG-BILLING",
                                 -round(r.uniform(60, 260), 2), "GIRO"))
            for _ in range(r.randint(4, 8)):
                self.post(p.pid, Txn(date(2026, month, r.randint(1, 28)), "CARD PAYMENT", r.choice(
                    ["NTUC FAIRPRICE", "GRAB", "SHOPEE", "COLD STORAGE", "SINGTEL", "GUARDIAN"]), "CARD",
                    -round(r.uniform(15, 420), 2), "CARD"))

    def build(self, workspace: Path) -> Truth:
        r = self.rng
        ids = [f"P{i:03d}" for i in range(1, self.n + 1)]
        r.shuffle(roles := ids[:])
        key, m1, m2, m3, nominee, d_alike, d_business, d_trust, d_student, d_cash = roles[:10]
        cids = [f"C{i:02d}" for i in range(1, 9)]
        r.shuffle(cids)
        s1, s2, legit_co, *others = cids

        people: dict[str, Person] = {}
        people[key] = self.person(key, name="Marcus Tan Wei Ming", dob=date(1979, 4, 12), occupation="business consultant",
                                  employer="Self-employed", income=96_000, risk="Medium")
        k = people[key]
        people[d_alike] = self.person(d_alike, name="Marcus Tan Wei Liang", dob=date(1994, 9, 3),
                                      occupation="sales manager", income=88_000)
        shell1 = Entity(s1, "Brightpath Trading Pte. Ltd.", "company", self.account())
        shell2 = Entity(s2, "Northwind Advisory Pte. Ltd.", "company", self.account())
        trust = Entity("T01", "Harbour Light Trust", "trust", self.account())
        family_trust = Entity("T02", "Lim Family Trust", "trust", self.account())
        people[m1] = self.person(m1, occupation="full-time student (part-time admin assistant)",
                                 employer=shell1.name, income=9_600, dob=date(2004, 2, 17))
        people[m2] = self.person(m2, occupation="retiree", employer="Not employed", income=14_400,
                                 dob=date(1958, 11, 5), alt_mobile=k.mobile)
        people[m3] = self.person(m3, occupation="food delivery rider", employer="Self-employed", income=26_000,
                                 address=k.address)
        people[nominee] = self.person(nominee, occupation="corporate secretarial executive",
                                      employer="Apex Corporate Services Pte. Ltd.", income=58_000)
        people[d_business] = self.person(d_business, occupation="managing director", income=480_000, risk="Medium")
        people[d_trust] = self.person(d_trust, name="Lim Jia Hui", occupation="architect", income=120_000)
        people[d_student] = self.person(d_student, occupation="university student", employer="Not employed",
                                        income=0, nationality="Malaysia", nric=self.nric(foreign=True),
                                        dob=date(2005, 6, 21))
        people[d_cash] = self.person(d_cash)
        for pid in ids:
            people.setdefault(pid, self.person(pid))
        people[d_business].employer = "Self-employed (owner)"
        legit = Entity(legit_co, f"{r.choice(SURNAMES)} Precision Engineering Pte. Ltd.", "company", self.account())

        # Registry and trust facts: the links are visible only by address, ID number or account number.
        shell1.details = {"uen": f"2024{r.randint(10000, 99999)}K", "incorporated": "2024-08-19",
                          "registered_address": k.address, "activity": "General wholesale trade",
                          "paid_up_capital_sgd": 1_000, "directors": [people[nominee].name],
                          "shareholders": [{"name": people[nominee].name, "id": people[nominee].nric, "percent": 100}],
                          "secretary": "Apex Corporate Services Pte. Ltd."}
        shell2.details = {"uen": f"2025{r.randint(10000, 99999)}W", "incorporated": "2025-01-07",
                          "registered_address": "10 Anson Road, #22-05, Singapore 079903",
                          "activity": "Management consultancy", "paid_up_capital_sgd": 10_000,
                          "directors": [people[nominee].name],
                          "shareholders": [{"name": "Meridian Trustees Pte. Ltd. as trustee of the Harbour Light Trust",
                                            "id": "T01", "percent": 100}],
                          "secretary": "Apex Corporate Services Pte. Ltd."}
        legit.details = {"uen": f"2009{r.randint(10000, 99999)}E", "incorporated": "2009-03-02",
                         "registered_address": "25 Tuas Avenue 4, Singapore 639383",
                         "activity": "Precision machining of aerospace components", "paid_up_capital_sgd": 2_500_000,
                         "directors": [people[d_business].name],
                         "shareholders": [{"name": people[d_business].name, "id": people[d_business].nric, "percent": 80},
                                          {"name": "Tuas Holdings Pte. Ltd.", "id": "external", "percent": 20}],
                         "secretary": "Apex Corporate Services Pte. Ltd."}
        companies = [shell1, shell2, legit]
        for cid in others:
            owner = people[r.choice(roles[10:])]
            company = Entity(cid, f"{r.choice(SURNAMES)} {r.choice(['Kitchen', 'Logistics', 'Florist', 'Dental', 'Print'])} "
                                  "Pte. Ltd.", "company", self.account())
            directors = [owner.name] + ([people[nominee].name] if cid == others[0] else [])
            company.details = {"uen": f"20{r.randint(10, 22)}{r.randint(10000, 99999)}M", "incorporated": "2016-05-10",
                               "registered_address": self.address(), "activity": "Retail and services",
                               "paid_up_capital_sgd": r.choice([50_000, 100_000, 200_000]), "directors": directors,
                               "shareholders": [{"name": owner.name, "id": owner.nric, "percent": 100}],
                               "secretary": "Apex Corporate Services Pte. Ltd."}
            companies.append(company)
            self.routine_company(company)
        trust.details = {"type": "Discretionary trust", "settled": "2024-11-02", "settlor": "Lim Siew Hoon",
                         "trustee": "Meridian Trustees Pte. Ltd.", "protector": people[nominee].name,
                         "beneficiaries": [f"TAN WEI MING MARCUS (NRIC {k.nric})"],
                         "purpose": "General family purposes", "source_of_wealth": "Not documented in the deed"}
        family_trust.details = {"type": "Fixed-interest family trust", "settled": "2011-06-30",
                                "settlor": "Lim Boon Huat (deceased 2019)", "trustee": "Meridian Trustees Pte. Ltd.",
                                "beneficiaries": [f"LIM JIA HUI (NRIC {people[d_trust].nric})"],
                                "purpose": "Quarterly income to beneficiary",
                                "source_of_wealth": "Sale of Lim Boon Huat's logistics business in 2010 (sale agreement on file)"}

        for pid in ids:
            p = people[pid]
            if pid in (m1, m2):
                self.routine(p, monthly_salary=800.0 if pid == m1 else 0.0)
            elif pid == d_student:
                self.routine(p, monthly_salary=0.0)
            else:
                self.routine(p)
        for a, b in [(r.choice(ids), r.choice(ids)) for _ in range(self.n * 2)]:
            if a != b:
                pa, pb = people[a], people[b]
                self.transfer(date(2026, r.randint(1, 6), r.randint(1, 28)), (a, pa.name.upper()[:22], pa.account),
                              (b, pb.name.upper()[:22], pb.account), round(r.uniform(20, 900), 2), "PAYNOW TRANSFER")

        # The planted flow: placement by mules, pass-through to shells, layering through the trust, to the key actor.
        ring: list[date] = []
        placement = 0.0
        s1_party = (s1, "BRIGHTPATH TRDG", shell1.account)
        s2_party = (s2, "NORTHWIND ADV", shell2.account)
        t_party = ("T01", "MERIDIAN TTEES A/C HLT", trust.account)
        for mule, target in ((m1, s1_party), (m2, s1_party), (m3, s2_party)):
            p = people[mule]
            for _ in range(5):
                day = date(2026, 3, 2) + timedelta(days=r.randint(0, 80))
                deposit = round(r.uniform(18_200, 19_950), 2)
                placement += deposit
                self.post(mule, Txn(day, f"CASH DEPOSIT - BRANCH {r.choice(BRANCHES).upper()}", "", "", deposit, "CASH"))
                out_day = day + timedelta(days=r.choice([0, 1]))
                initials = "".join(part[0] for part in p.name.split()[:-1]) + " " + p.name.split()[-1].upper()
                self.transfer(out_day, (mule, initials, p.account), target, deposit - r.randint(80, 300),
                              "FAST TRANSFER - INV PAYMENT")
                ring += [day, out_day]
        s1_in = sum(t.amount for t in self.ledgers[s1] if t.amount > 0 and t.channel == "FAST")
        for week in range(6):
            day = date(2026, 3, 20) + timedelta(days=week * 11)
            self.transfer(day, s1_party, s2_party, round(s1_in * 0.15, 2), "CONSULTANCY FEE")
            ring.append(day)
        s2_in = sum(t.amount for t in self.ledgers[s2] if t.amount > 0)
        for i in range(4):
            day = date(2026, 4, 2) + timedelta(days=i * 18)
            self.transfer(day, s2_party, t_party, round(s2_in * 0.22, 2), "CAPITAL DISTRIBUTION TO TRUSTEE", "TT")
            ring.append(day)
        t_in = sum(t.amount for t in self.ledgers["T01"] if t.amount > 0)
        for i in range(3):
            day = date(2026, 4, 20) + timedelta(days=i * 17)
            self.transfer(day, t_party, (key, "M TAN", k.account), round(t_in * 0.30, 2), "BENEFICIARY DISTRIBUTION", "TT")
            ring.append(day)
        self.post(key, Txn(date(2026, 6, 8), "TT - PROPERTY DOWNPAYMENT", "PROPNEX CONVEYANCING", "TT-OUT",
                           -round(t_in * 0.6, 2), "TT"))
        self.post(s1, Txn(date(2026, 5, 30), "OFFICE EXPENSES", "REGUS", "CARD", -1_250.00, "CARD"))

        # Decoys with documented explanations.
        biz = people[d_business]
        for month in range(1, 7):
            for _ in range(3):
                self.transfer(date(2026, month, r.randint(1, 28)), ("", "AERO COMPONENTS ASIA", "TT-IN"),
                              (legit_co, "", ""), round(r.uniform(80_000, 240_000), 2), "INVOICE SETTLEMENT", "TT")
            self.transfer(date(2026, month, 28), (legit_co, legit.name.upper()[:24], legit.account), ("", "PAYROLL", "GIRO"),
                          round(r.uniform(150_000, 190_000), 2), "PAYROLL", "GIRO")
        for month in (3, 6):
            self.transfer(date(2026, month, 30), (legit_co, legit.name.upper()[:24], legit.account),
                          (d_business, "", biz.account), 120_000.00, "DIVIDEND", "GIRO")
        for month in (1, 4):
            self.transfer(date(2026, month, 5), ("T02", "MERIDIAN TTEES A/C LFT", family_trust.account),
                          (d_trust, "", people[d_trust].account), 18_500.00, "TRUST INCOME DISTRIBUTION", "TT")
        for month in range(1, 7):
            self.post(d_student, Txn(date(2026, month, 2), "INWARD TT - FAMILY SUPPORT", "LEE BOON KEAT (MAYBANK MY)",
                                     "TT-IN", round(r.uniform(2_500, 3_500), 2), "TT"))
        self.post(d_cash, Txn(date(2026, 4, 14), "CASH DEPOSIT - BRANCH BEDOK", "", "", 19_800.00, "CASH"))

        people[d_cash].notes.append(f"Customer deposited {_sgd(19_800)} in cash on {_sg_date(date(2026, 4, 14))} "
                                    "from the private sale of a 2015 Honda Vezel. Signed sale agreement and LTA "
                                    "transfer record sighted and filed.")
        people[d_student].notes.append("Monthly inward remittances are family support from the customer's father in "
                                       "Johor Bahru. Father's payslips and the university offer letter are on file.")
        people[d_trust].notes.append("Quarterly distributions from the Lim Family Trust. Trust deed and the 2010 business "
                                     "sale agreement sighted at onboarding.")
        people[m2].notes.append(f"Customer gave an alternate contact number {k.mobile} for a 'nephew who helps with "
                                "banking'. Customer could not explain the purpose of recent cash deposits and ended the call.")
        people[m1].notes.append("Customer said the part-time employer asked customer to 'receive client payments' "
                                "into the personal account and forward them.")
        people[nominee].notes.append("Customer is a director of several client companies of the corporate service "
                                     "provider. Customer receives a flat fee per directorship.")
        people[key].notes.append("Customer declared consultancy income and said a family trust may pay "
                                 "distributions. No trust documents were provided at the last review.")

        files = self.write(workspace, ids, people, companies, [trust, family_trust])
        return Truth(persons=self.n, key_actor=key,
                     subjects={key: "key_actor", m1: "money_mule", m2: "money_mule", m3: "money_mule",
                               nominee: "nominee_director"},
                     entities={s1, s2, "T01"},
                     decoys={d_alike: "name-alike of the key actor", d_business: "high-volume business owner",
                             d_trust: "legitimate family trust beneficiary", d_student: "family remittances",
                             d_cash: "explained cash deposit"},
                     typologies={"structuring", "rapid_pass_through", "shell_company", "nominee_director",
                                 "layering_via_trust"},
                     placement_total=round(placement, 2), period=(min(ring), max(ring)), files=files)

    def routine_company(self, company: Entity) -> None:
        r = self.rng
        for month in range(1, 7):
            for _ in range(r.randint(3, 6)):
                self.post(company.eid, Txn(date(2026, month, r.randint(1, 28)), "CUSTOMER RECEIPT",
                                           r.choice(["NETS SETTLEMENT", "GRABFOOD MERCHANT", "VISA SETTLEMENT"]),
                                           "SETTLEMENT", round(r.uniform(800, 9_000), 2), "GIRO"))
            self.post(company.eid, Txn(date(2026, month, 27), "SUPPLIER PAYMENT", "VARIOUS SUPPLIERS", "GIRO",
                                       -round(r.uniform(3_000, 18_000), 2), "GIRO"))

    # ------------------------------------------------------------------------------------------- documents
    def write(self, workspace: Path, ids: list[str], people: dict[str, Person], companies: list[Entity],
              trusts: list[Entity]) -> list[str]:
        import docx  # python-docx, a project dependency

        case = workspace / "case"
        for sub in ("profiles", "rm_notes", "registry", "trusts", "statements", "media"):
            (case / sub).mkdir(parents=True, exist_ok=True)
        (case / "README.txt").write_text(
            "Synthetic case file for a transaction monitoring review. All persons, companies, trusts, identifiers and\n"
            "accounts are fictitious.\n\nprofiles/    KYC profiles (md, docx, html, json)\nrm_notes/    relationship "
            "manager call notes (eml)\nregistry/    company registry extracts\ntrusts/      trust deed summaries\n"
            "statements/  <holder ID>_statement.csv, 01 Jan 2026 to 30 Jun 2026; each holder's account number is in\n"
            "             its profile, registry extract or trust deed\nmedia/       media screening hits\n")
        for index, pid in enumerate(ids):
            p = people[pid]
            rows = [("Customer ID", pid), ("Full name", p.name), ("NRIC/FIN", p.nric), ("Date of birth", p.dob.isoformat()),
                    ("Nationality", p.nationality), ("Occupation", p.occupation), ("Employer", p.employer),
                    ("Declared annual income", _sgd(p.income)), ("Residential address", p.address),
                    ("Mobile", p.mobile), ("Email", p.email), ("Account", f"SGD savings {p.account}"),
                    ("Relationship since", p.since.isoformat()), ("Customer risk rating", p.risk),
                    ("Expected activity", "Salary credits, bill payments and card spending")]
            narrative = (f"Onboarding CDD completed at branch. Source of funds declared as {p.occupation} income. "
                         "No PEP or sanctions screening hits at onboarding. Periodic review scheduled every three years. "
                         "Customer consented to the collection of personal data for account opening and ongoing "
                         "monitoring. ") * 2
            stem = f"{pid}_{re.sub(r'[^A-Za-z]+', '_', p.name).strip('_')}"
            kind = index % 4
            if kind == 0:
                body = "\n".join(f"| {k} | {v} |" for k, v in rows)
                (case / "profiles" / f"{stem}.md").write_text(
                    f"# KYC profile {pid}\n\n| Field | Value |\n|---|---|\n{body}\n\n## CDD notes\n\n{narrative}\n")
            elif kind == 1:
                doc = docx.Document()
                doc.add_heading(f"KYC profile {pid}", 1)
                table = doc.add_table(rows=0, cols=2)
                for k, v in rows:
                    cells = table.add_row().cells
                    cells[0].text, cells[1].text = k, v
                doc.add_heading("CDD notes", 2)
                doc.add_paragraph(narrative)
                doc.save(case / "profiles" / f"{stem}.docx")
            elif kind == 2:
                cells = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
                (case / "profiles" / f"{stem}.html").write_text(
                    f"<html><body><h1>KYC profile {pid}</h1><table>{cells}</table><h2>CDD notes</h2>"
                    f"<p>{narrative}</p></body></html>")
            else:
                (case / "profiles" / f"{stem}.json").write_text(json.dumps(
                    {**{k.lower().replace(" ", "_").replace("/", "_"): v for k, v in rows}, "cdd_notes": narrative},
                    indent=2))
            if p.notes or p.alt_mobile or index % 3 == 0:
                message = email.message.EmailMessage()
                message["From"] = "rm.desk@bank.example"
                message["To"] = "tm.review@bank.example"
                message["Subject"] = f"Call note {pid} {p.name}"
                message["Date"] = "Mon, 08 Jun 2026 10:15:00 +0800"
                text = p.notes or [f"Routine courtesy call. Customer confirmed contact details and employment as "
                                   f"{p.occupation}. No changes to the profile."]
                message.set_content("\n\n".join(text) + "\n\nRM Desk 4\n")
                (case / "rm_notes" / f"{pid}_call_note.eml").write_bytes(bytes(message))
        for company in companies:
            d = company.details
            (case / "registry" / f"{company.eid}_{re.sub(r'[^A-Za-z]+', '_', company.name).strip('_')}.json").write_text(
                json.dumps({"entity_id": company.eid, "name": company.name, **d,
                            "bank_account": f"SGD current {company.account}"}, indent=2))
        for trust in trusts:
            d = trust.details
            lines = [f"TRUST DEED SUMMARY - {trust.name} ({trust.eid})", "",
                     *(f"{key.replace('_', ' ').title()}: {', '.join(v) if isinstance(v, list) else v}"
                       for key, v in d.items()),
                     f"Trust bank account: SGD trust account {trust.account} held by the trustee", "",
                     "Prepared by the trustee for the bank's CDD file. The trustee confirms the identity of the "
                     "beneficiaries by NRIC only."]
            (case / "trusts" / f"{trust.eid}_{trust.name.replace(' ', '_')}.txt").write_text("\n".join(lines) + "\n")
        (case / "media" / "MEDIA-01_marcus_tan_charged.html").write_text(
            "<html><body><h1>Former property agent charged over cheating</h1><p>18 May 2026 - Marcus Tan, 58, a former "
            "property agent, was charged in court with cheating two buyers of about SGD 240,000. He is alleged to have "
            "collected option fees for units he did not market. The case has been adjourned.</p></body></html>")
        (case / "media" / "MEDIA-02_corporate_service_providers.html").write_text(
            "<html><body><h1>Regulator tightens rules on nominee directors</h1><p>02 Mar 2026 - New rules require "
            "corporate service providers to keep registers of nominee directors and their nominators. The changes "
            "follow cases in which shell companies with nominee directors received pass-through funds.</p></body></html>")
        # Plain CSV: the holder is only in the file name, the account number only in the profile/registry/deed.
        for owner, ledger in sorted(self.ledgers.items()):
            balance = round(self.rng.uniform(2_000, 30_000), 2) if owner.startswith("P") else 250_000.00
            lines = ["date,description,counterparty_name,counterparty_account,debit_sgd,credit_sgd,balance_sgd,channel"]
            for t in sorted(ledger, key=lambda t: t.day):
                balance = round(balance + t.amount, 2)
                debit, credit = (f"{-t.amount:.2f}", "") if t.amount < 0 else ("", f"{t.amount:.2f}")
                lines.append(f"{t.day.isoformat()},{t.description},{t.counterparty},{t.counterparty_account},"
                             f"{debit},{credit},{balance:.2f},{t.channel}")
            (case / "statements" / f"{owner}_statement.csv").write_text("\n".join(lines) + "\n")
        return sorted(str(p.relative_to(workspace)) for p in case.rglob("*") if p.is_file())


# --------------------------------------------------------------------------------------------- task and grading
def task_prompt(persons: int) -> str:
    return f"""You are a transaction monitoring analyst at a Singapore bank. This is a synthetic review exercise.
The folder case/ holds the complete case file for {persons} customers (P001 to P{persons:03d}): KYC profiles in
several formats, RM call notes (.eml), company registry extracts, trust deed summaries, account statements
(.csv, 01 Jan 2026 to 30 Jun 2026) and media hits. Start with case/README.txt. Use only the case file; do not
change anything under case/.

Goal: review every customer, find any network of related parties moving suspicious funds (links may be hidden
behind abbreviated counterparty names, account numbers, shared addresses or contact numbers, trust deeds and
company registry records), and write an internal STR-style report for the MLRO in Singapore financial crime
compliance house style.

Deliverables (create the folder report/):
1. report/findings.json, exactly these keys:
   "persons_reviewed": number of customer profiles reviewed (integer)
   "key_actor": customer ID of the person who ultimately controls or benefits from the suspicious funds
   "subjects": list of {{"id": customer ID, "role": one of {list(ROLES)}, "reason": one sentence,
               "evidence": list of case file paths}} - only customers with reasonable grounds to suspect
   "linked_entities": list of company/trust IDs (C.., T..) used in the suspicious flow
   "typologies": list chosen only from {list(TYPOLOGIES)}
   "placement_total_sgd": total of the cash deposits placed into the subjects' accounts as part of the scheme
   "period": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} first and last date of the transactions in the
             suspicious flow
2. report/index.html, one self-contained HTML file (inline CSS/SVG only; no external scripts, styles or images),
   with these section element ids: {", ".join(SECTIONS)}.
   - summary: the overall picture in a short executive narrative.
   - subjects: each subject's particulars and role; linked companies and trusts with their role.
   - network: an inline <svg> graph. One node per subject and linked entity, labelled with its ID (e.g. P007,
     C03, T01); edges for fund flows and control links.
   - transactions: the material transactions or linked groups, with dates and amounts.
   - grounds: the grounds for suspicion, each with its source file.
   - recommendation: next steps, including whether to consider filing an STR with STRO.

House style: formal, neutral and factual; third person; British English. Amounts as SGD 12,345.67; dates as
08 Jun 2026. No emotive or conclusory words (clearly, obviously, shocking, criminal, launderer, fraudster,
guilty). Keep facts apart from inferences ("This suggests ..."). Never match people or companies by name only:
confirm by ID number, date of birth, address, contact number or account number. Adverse media alone is an
allegation. Never suggest informing the customer about the review or an STR.

Each reply is limited to about 4,000 tokens: build the HTML in parts (for example write a skeleton, then
append or edit each section). When both files are written, reply with a short completion note."""


class _Html(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.ids: set[str] = set()
        # A section runs from the element carrying its id to the next section id in document order, so both
        # <section id="network">...</section> and <h2 id="network">...</h2><svg>...</svg> are recognised.
        self.current: str | None = None
        self.sections: dict[str, list[str]] = {name: [] for name in SECTIONS}
        self.text: list[str] = []
        self.svg_text: list[str] = []
        self.svg_edges = 0
        self.external: list[str] = []

    def _in_network_svg(self) -> bool:
        return self.current == "network" and "svg" in self.stack

    def _open(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
            if values["id"] in self.sections:
                self.current = values["id"]
        for key in ("src", "href"):
            target = values.get(key) or ""
            if tag in {"script", "link", "img", "iframe"} and re.match(r"(?:https?:)?//", target):
                self.external.append(target)
        if tag in {"line", "path", "polyline"} and self._in_network_svg():
            self.svg_edges += 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs)
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._open(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.stack:
            del self.stack[len(self.stack) - 1 - self.stack[::-1].index(tag):]

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self.current is not None:
            self.sections[self.current].append(data)
        if self._in_network_svg():
            self.svg_text.append(data)


def _f1(found: set[str], truth: set[str]) -> dict[str, float]:
    hit = len(found & truth)
    precision = hit / len(found) if found else 0.0
    recall = hit / len(truth) if truth else 0.0
    return {"precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if hit else 0.0}


def _date(value: Any) -> date | None:
    for parse in (date.fromisoformat, lambda v: datetime.strptime(v, "%d %b %Y").date()):
        try:
            return parse(str(value))
        except ValueError:
            pass
    return None


def _period(value: Any) -> tuple[date | None, date | None]:
    """{"start", "end"} as asked, or a string holding two ISO or "08 Jun 2026" dates."""
    if isinstance(value, dict):
        return _date(value.get("start")), _date(value.get("end"))
    found = [_date(m) for m in re.findall(r"\d{4}-\d{2}-\d{2}|" + SG_DATE.pattern[2:-2], str(value or ""))]
    return (found[0], found[1]) if len(found) >= 2 else (None, None)


def _id(value: Any) -> str:
    """An ID as asked, or the "id" of an object the agent wrote instead."""
    return str(value.get("id")) if isinstance(value, dict) else str(value)


def grade(workspace: Path, truth: Truth, hashes: dict[str, str]) -> dict[str, Any]:
    """Per-criterion scores in [0, 1]; axis scores are their means; the overall score is weighted."""
    report = workspace / "report"
    try:
        findings = json.loads((report / "findings.json").read_text())
        if not isinstance(findings, dict):
            findings = {}
    except (OSError, ValueError):
        findings = {}
    html_path = report / "index.html"
    html = html_path.read_text(errors="replace") if html_path.is_file() else ""
    page = _Html()
    if html:
        page.feed(html)
        page.close()
    text = " ".join(page.text)
    known = {Path(f).stem.split("_")[0] for f in truth.files}

    subjects = [s for s in findings.get("subjects") or [] if isinstance(s, dict)]
    flagged = {_id(s) for s in subjects}
    linked = findings.get("linked_entities") or []
    entities = {_id(e) for e in linked}
    typologies = {str(t) for t in findings.get("typologies") or []}
    total = findings.get("placement_total_sgd")
    start, end = _period(findings.get("period"))

    def close(value: Any, target: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return 0.0
        error = abs(value - target) / target
        return 1.0 if error <= 0.01 else 0.5 if error <= 0.10 else 0.0

    def day_score(found: date | None, target: date) -> float:
        if found is None:
            return 0.0
        gap = abs((found - target).days)
        return 1.0 if gap == 0 else 0.5 if gap <= 7 else 0.0

    a = {
        "persons_reviewed": float(findings.get("persons_reviewed") == truth.persons),
        "placement_total": close(total, truth.placement_total),
        "period_start": day_score(start, truth.period[0]),
        "period_end": day_score(end, truth.period[1]),
        "typologies_jaccard": len(typologies & truth.typologies) / len(typologies | truth.typologies)
                              if typologies | truth.typologies else 0.0,
        "summary_names_key_actor": float(truth.key_actor in " ".join(page.sections["summary"])),
    }
    subject_f1 = _f1(flagged, set(truth.subjects))
    entity_f1 = _f1(entities, truth.entities)
    roles = {str(s.get("id")): s.get("role") for s in subjects}
    cited = [p for s in subjects for p in (s.get("evidence") or []) if isinstance(p, str)]
    b = {
        "key_actor": float(_id(findings.get("key_actor")) == truth.key_actor),
        "subjects_f1": subject_f1["f1"],
        "linked_entities_f1": entity_f1["f1"],
        "roles_correct": sum(roles.get(pid) == role for pid, role in truth.subjects.items()) / len(truth.subjects),
        # Flagging nobody avoids every decoy but earns nothing here.
        "decoys_not_flagged": 1 - len(flagged & set(truth.decoys)) / len(truth.decoys) if flagged else 0.0,
        "evidence_paths_exist": sum((workspace / p).is_file() or (workspace / "case" / p).is_file() for p in cited)
                                / len(cited) if cited else 0.0,
    }
    network_ids = set(truth.subjects) | truth.entities
    svg = " ".join(page.svg_text)
    mentioned = set(ENTITY_ID.findall(text))
    banned = [w for w in FORBIDDEN if re.search(rf"\b{w}\b", text, re.I)]
    c = {
        "html_written": float(bool(html)),
        "self_contained": float(bool(html) and not page.external),
        "sections_present": sum(s in page.ids for s in SECTIONS) / len(SECTIONS),
        "graph_nodes_recall": len({i for i in network_ids if re.search(rf"\b{i}\b", svg)}) / len(network_ids),
        "graph_edges": min(1.0, page.svg_edges / (len(network_ids) - 1)),
        "neutral_wording": float(bool(html) and not banned),
        "no_tipping_off": float(bool(html) and not TIPPING_OFF.search(text)),
        "sgd_amount_format": min(1.0, len(AMOUNT.findall(text)) / 3),
        "sg_date_format": min(1.0, len(SG_DATE.findall(text)) / 3),
        "recommends_stro": float("STRO" in " ".join(page.sections["recommendation"])),
        "no_unknown_ids": float(bool(html) and mentioned <= known),
        # Reasoning above reads IDs leniently; following the stated findings.json contract is scored here.
        "findings_contract": sum((
            isinstance(findings.get("persons_reviewed"), int),
            isinstance(findings.get("key_actor"), str),
            bool(linked) and all(isinstance(e, str) for e in linked),
            bool(subjects) and all(s.get("role") in ROLES for s in subjects),
            bool(typologies) and typologies <= set(TYPOLOGIES),
            isinstance(findings.get("period"), dict) and all(_date(findings["period"].get(k)) is not None
                                                              and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(findings["period"].get(k)))
                                                              for k in ("start", "end")),
        )) / 6,
    }
    axes = {"A_overall_picture": a, "B_cross_identification": b, "C_report": c}
    weights = {"key_actor": 2.0}
    scores = {axis: sum(v * weights.get(k, 1.0) for k, v in items.items()) /
              sum(weights.get(k, 1.0) for k in items) for axis, items in axes.items()}
    unchanged = all((workspace / p).is_file() and hashlib.sha256((workspace / p).read_bytes()).hexdigest() == digest
                    for p, digest in hashes.items())
    overall = sum(WEIGHTS[axis] * score for axis, score in scores.items()) if unchanged else 0.0
    return {"overall": round(overall, 4), "axes": {k: round(v, 4) for k, v in scores.items()},
            "criteria": {axis: {k: round(v, 4) for k, v in items.items()} for axis, items in axes.items()},
            "case_unchanged": unchanged, "subjects": subject_f1, "entities": entity_f1,
            "flagged": sorted(flagged), "decoys_flagged": sorted(flagged & set(truth.decoys)),
            "banned_words": banned, "external_resources": page.external[:5], "unknown_ids": sorted(mentioned - known)}


# --------------------------------------------------------------------------------------------- self-check
def oracle(workspace: Path, truth: Truth) -> None:
    """Write a reference report straight from the ground truth."""
    report = workspace / "report"
    report.mkdir(exist_ok=True)
    statements = {pid: f"case/statements/{pid}_statement.csv" for pid in [*truth.subjects, *truth.entities]}
    findings = {
        "persons_reviewed": truth.persons, "key_actor": truth.key_actor,
        "subjects": [{"id": pid, "role": role, "reason": "Reference.", "evidence": [statements[pid]]}
                     for pid, role in truth.subjects.items()],
        "linked_entities": sorted(truth.entities), "typologies": sorted(truth.typologies),
        "placement_total_sgd": truth.placement_total,
        "period": {"start": truth.period[0].isoformat(), "end": truth.period[1].isoformat()},
    }
    (report / "findings.json").write_text(json.dumps(findings, indent=2))
    nodes = [*truth.subjects, *sorted(truth.entities)]
    svg = "".join(f'<text x="10" y="{20 * i + 20}">{n}</text>' for i, n in enumerate(nodes))
    svg += "".join(f'<line x1="0" y1="{i}" x2="5" y2="{i}"/>' for i in range(len(nodes) - 1))
    (report / "index.html").write_text(
        f"<html><body><section id='summary'><p>{truth.key_actor} appears to control funds of "
        f"{_sgd(truth.placement_total)} placed between {_sg_date(truth.period[0])} and {_sg_date(truth.period[1])}."
        f"</p></section><section id='subjects'><p>{', '.join(truth.subjects)}</p></section>"
        f"<section id='network'><svg>{svg}</svg></section><section id='transactions'><p>{_sgd(1000)} and "
        f"{_sgd(2000)} on "
        f"{_sg_date(truth.period[0])}.</p></section><section id='grounds'><p>This suggests structuring.</p></section>"
        f"<section id='recommendation'><p>Consider filing an STR with STRO.</p></section></body></html>")


def case_text(workspace: Path, files: list[str]) -> dict[str, str]:
    """Readable text per case file. A .docx contributes its paragraph and table text: its zip bytes carry
    creation timestamps, so byte hashes differ between identical builds."""
    import docx

    texts = {}
    for name in files:
        path = workspace / name
        if path.suffix == ".docx":
            document = docx.Document(path)
            texts[name] = "\n".join([*(p.text for p in document.paragraphs),
                                     *(c.text for t in document.tables for row in t.rows for c in row.cells)])
        else:
            texts[name] = path.read_text(errors="replace")
    return texts


def case_digest(texts: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(texts, sort_keys=True).encode()).hexdigest()


def self_check(persons: int, seed: int) -> None:
    with tempfile.TemporaryDirectory(prefix="str-benchmark-check-") as directory:
        workspace = Path(directory)
        truth = CaseBuilder(persons, seed).build(workspace)
        hashes = {f: hashlib.sha256((workspace / f).read_bytes()).hexdigest() for f in truth.files}
        chars = sum(map(len, case_text(workspace, truth.files).values()))
        empty = grade(workspace, truth, hashes)
        oracle(workspace, truth)
        perfect = grade(workspace, truth, hashes)
        findings = json.loads((workspace / "report/findings.json").read_text())
        findings["subjects"] += [{"id": pid, "role": "money_mule", "reason": "x", "evidence": []}
                                 for pid in truth.decoys]
        findings["key_actor"] = next(iter(truth.decoys))
        (workspace / "report/findings.json").write_text(json.dumps(findings))
        html = (workspace / "report/index.html").read_text()
        (workspace / "report/index.html").write_text(html.replace("appears to control", "is clearly a criminal who controls")
                                                     .replace("Consider filing", "Notify the customer and consider filing"))
        naive = grade(workspace, truth, hashes)
        print(json.dumps({"files": len(truth.files), "case_text_chars": chars, "approx_tokens_chars_div_4": chars // 4,
                          "key_actor": truth.key_actor, "subjects": truth.subjects, "entities": sorted(truth.entities),
                          "decoys": truth.decoys, "placement_total": truth.placement_total,
                          "period": [d.isoformat() for d in truth.period],
                          "empty": empty["overall"], "oracle": perfect["overall"], "oracle_axes": perfect["axes"],
                          "naive": naive["overall"], "naive_axes": naive["axes"],
                          "naive_flags": {k: naive[k] for k in ("decoys_flagged", "banned_words")}}, indent=2))


class UsageProxy:
    """Forwards the OpenAI-compatible API unchanged and records the server's prompt-cache use per completion
    (usage.prompt_tokens_details.cached_tokens and llama.cpp timings), which the agents' clients discard."""

    def __init__(self, upstream: str) -> None:
        self.upstream = upstream.rstrip("/")
        self.records: list[dict[str, Any]] = []
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"     # close-delimited bodies; the stream passes through unbuffered

            def log_message(self, *args: Any) -> None:
                pass

            def _forward(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else None
                headers = {k: v for k, v in self.headers.items() if k.lower() in ("content-type", "authorization")}
                path = self.path[len("/v1"):] if self.path.startswith("/v1") else self.path
                request = urllib.request.Request(owner.upstream + path, data=body, headers=headers, method=self.command)
                try:
                    response = opener.open(request, timeout=3600)
                except urllib.error.HTTPError as error:
                    response = error
                self.send_response(response.status if hasattr(response, "status") else response.code)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.end_headers()
                last: dict[str, Any] = {}
                for line in response:
                    self.wfile.write(line)
                    self.wfile.flush()
                    if line.startswith(b"data:") and b"[DONE]" not in line:
                        try:
                            chunk = json.loads(line[5:])
                        except ValueError:
                            continue
                        if chunk.get("usage") or chunk.get("timings"):
                            last = chunk
                if path.endswith("/chat/completions") and last:
                    usage, timings = last.get("usage") or {}, last.get("timings") or {}
                    owner.records.append({
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens",
                                                                                        timings.get("cache_n")),
                        "prompt_ms": timings.get("prompt_ms"), "predicted_ms": timings.get("predicted_ms")})

            do_GET = do_POST = _forward

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()

    def summary(self) -> dict[str, Any]:
        prompt = sum(r["prompt_tokens"] or 0 for r in self.records)
        cached = sum(r["cached_tokens"] or 0 for r in self.records)
        return {"requests": len(self.records), "prompt_tokens": prompt, "cached_tokens": cached,
                "cache_hit_ratio": round(cached / prompt, 4) if prompt else None,
                "prefill_s": round(sum(r["prompt_ms"] or 0 for r in self.records) / 1000, 1),
                "decode_s": round(sum(r["predicted_ms"] or 0 for r in self.records) / 1000, 1),
                "per_request": self.records}


# --------------------------------------------------------------------------------------------- live trials
def worker(trial: int, persons: int, seed: int, max_turns: int, artifacts: Path) -> dict[str, Any]:
    from kentc_agent.adapters import llm as llm_module
    from kentc_agent.adapters import tools as tools_module
    from kentc_agent.adapters.session import Session
    from kentc_agent.agent.loop import Agent
    from kentc_agent.config import Settings
    from kentc_agent.ports import Events

    class Observer(Events):
        def __init__(self) -> None:
            self.tools: list[dict[str, Any]] = []
            self.projections: list[dict[str, Any]] = []
            self.statuses: list[str] = []
            self.current: dict[str, Any] = {}

        def tool_start(self, agent: str, name: str, args: dict[str, Any]) -> None:
            self.current = {"name": name, "args": args}

        def tool_end(self, agent: str, name: str, result: str, error: bool) -> None:
            self.tools.append({**self.current, "name": name, "error": error, "chars": len(result)})

        def compaction(self, agent: str, before: int, after: int) -> None:
            self.projections.append({"kind": "summary", "before": before, "after": after})


        def status(self, agent: str, text: str) -> None:
            self.statuses.append(text)

    upstream = Settings().base_url
    proxy = UsageProxy(upstream)
    settings = Settings(temperature=0, reasoning_effort="none", sub_effort="none", max_output_tokens=4096,
                        max_turns=max_turns, request_timeout=600, trust_env=False, trace=True, base_url=proxy.url)
    meter = Meter(llm_module.LLMClient(settings))
    model = meter.info()
    events = Observer()
    result: dict[str, Any] = {"trial": trial, "persons": persons, "seed": seed,
                              "model": model.id, "context_window": model.context_window, "max_turns": max_turns}
    with tempfile.TemporaryDirectory(prefix="str-benchmark-") as temporary:
        workspace = Path(temporary)
        truth = CaseBuilder(persons, seed).build(workspace)
        hashes = {f: hashlib.sha256((workspace / f).read_bytes()).hexdigest() for f in truth.files}
        texts = case_text(workspace, truth.files)
        result.update(case_sha256=case_digest(texts), case_files=len(truth.files),
                      case_text_chars=sum(map(len, texts.values())))
        ctx = tools_module.ToolContext(workspace, settings, meter, events)
        agent = Agent(ctx, session=Session(workspace / "session.jsonl"),
                      tools=[tools_module.CORE_TOOLS[name] for name in TOOLS])
        meter.origin = time.monotonic()
        answer = ""
        try:
            answer = agent.run(task_prompt(persons))
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        result["answer_wall_s"] = time.monotonic() - meter.origin
        result["stopped"] = agent.stopped
        result["answer"] = answer[-2000:]
        result["grade"] = grade(workspace, truth, hashes)
        agent.close()
        result["answer_plus_close_s"] = time.monotonic() - meter.origin
        target = artifacts / f"trial-{trial}"
        if (workspace / "report").is_dir():
            shutil.copytree(workspace / "report", target, dirs_exist_ok=True)
    reads = [t["args"].get("path", "") for t in events.tools if t["name"] == "read" and isinstance(t.get("args"), dict)]
    shell = " ".join(str(t["args"].get("command", "")) for t in events.tools
                     if t["name"] == "bash" and isinstance(t.get("args"), dict))
    touched = {f for f in truth.files if any(f.endswith(r.lstrip("./")) for r in reads if r) or Path(f).name in shell}
    proxy.close()
    result.update(peak_rss_mib=peak_rss(), usage=totals(meter.calls), calls=len(meter.calls),
                  server_cache=proxy.summary(),
                  tool_counts=dict(Counter(t["name"] for t in events.tools)),
                  # Compact call log for loop diagnosis: name, arguments (truncated), result size.
                  tool_log=[[t["name"], json.dumps(t.get("args"), ensure_ascii=False)[:300], t["chars"]]
                            for t in events.tools],
                  identical_repeat_calls=sum(n - 1 for n in Counter(
                      (t["name"], json.dumps(t.get("args"), sort_keys=True)) for t in events.tools).values() if n > 1),
                  tool_errors=sum(t["error"] for t in events.tools),
                  file_coverage=round(len(touched) / len(truth.files), 4),
                  repeated_reads=sum(n - 1 for n in Counter(reads).values() if n > 1),
                  projections=events.projections, statuses=events.statuses[-20:],
                  truth={"key_actor": truth.key_actor, "subjects": truth.subjects, "entities": sorted(truth.entities),
                         "placement_total": truth.placement_total,
                         "period": [d.isoformat() for d in truth.period]})
    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    row: dict[str, Any] = {"trials": len(results),
                           "median_overall": statistics.median(r["grade"]["overall"] for r in results)}
    for axis in WEIGHTS:
        row[f"median_{axis}"] = statistics.median(r["grade"]["axes"][axis] for r in results)
    for key in ("answer_wall_s", "file_coverage", "repeated_reads", "peak_rss_mib"):
        row[f"median_{key}"] = statistics.median(r[key] for r in results)
    for kind in ("foreground", "summary"):
        for key in ("calls", "prompt_tokens", "completion_tokens"):
            row[f"median_{kind}_{key}"] = statistics.median(r["usage"][kind][key] for r in results)
    row["errors"] = [r.get("error") for r in results if r.get("error")]
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--persons", type=int, default=40)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-turns", type=int, default=80)
    parser.add_argument("--timeout", type=int, default=3 * 3600, help="seconds per trial; 0 = no limit")
    parser.add_argument("--self-check", action="store_true", help="grade empty, reference and naive reports; no model")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--trial", type=int, default=1, help=argparse.SUPPRESS)
    parser.add_argument("--artifacts", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.self_check:
        self_check(args.persons, args.seed)
        return
    if args.output is None:
        parser.error("--output is required")
    if args.worker:
        args.output.write_text(json.dumps(worker(args.trial, args.persons, args.seed, args.max_turns,
                                                 args.artifacts), ensure_ascii=False, indent=2))
        return
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    artifacts = args.output.with_suffix(".artifacts")
    artifacts.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
        "python": sys.version, "repeats": args.repeats,
        "protocol": {"persons": args.persons, "seed": args.seed, "max_turns": args.max_turns, "tools": list(TOOLS),
                     "settings": {"temperature": 0, "reasoning_effort": "none", "max_output_tokens": 4096},
                     "order": "sequential fresh processes; empty session; same case per seed",
                     "memory": "foreground compression with consolidated local topic files; no intrinsic retrieval tools",
                     "weights": WEIGHTS, "artifacts": str(artifacts)},
        "results": results,
    }
    with tempfile.TemporaryDirectory(prefix="str-benchmark-results-") as directory:
        for trial in range(1, args.repeats + 1):
            child = Path(directory) / "trial.json"
            command = [sys.executable, str(Path(__file__).resolve()), "--worker",
                       "--trial", str(trial), "--persons", str(args.persons), "--seed", str(args.seed),
                       "--max-turns", str(args.max_turns), "--output", str(child), "--artifacts", str(artifacts)]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=args.timeout or None)
            if completed.returncode:
                raise RuntimeError(f"trial {trial}: {completed.stderr[-4000:]}")
            result = json.loads(child.read_text())
            if results and (results[0]["model"], results[0]["context_window"], results[0]["case_sha256"]) != \
                    (result["model"], result["context_window"], result["case_sha256"]):
                raise RuntimeError("Deployment or case changed between trials; do not combine them")
            results.append(result)
            report["summary"] = summarize(results)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
            print(json.dumps({"trial": trial, "overall": result["grade"]["overall"],
                              "axes": result["grade"]["axes"], "wall_s": round(result["answer_wall_s"], 1),
                              "error": result.get("error")}), flush=True)
    print(json.dumps(report["summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
