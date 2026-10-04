# QuotePilot — business and product blueprint

Decision record: 2 October 2026. Working name; check trademarks and domain availability before branding. All money is SGD unless stated otherwise.

## 1. Decision and boundaries

Build a proposal-preparation product for owner-led web-development agencies with 2–10 people. Start with a paid, manually reviewed service; automate only the workflow that paying customers repeatedly use. The job: turn discovery notes and an approved service catalogue into a client-ready scope, price table, exclusions, clarification questions, and three follow-up email drafts.

Sell time saved and clearer scope, **not guaranteed sales or AI magic**. Proposed positioning: “Discovery notes in. A reviewable proposal and follow-up pack out. Your rates, your scope, your final approval.”

The interactive companion is `quotepilot-design.html`. It contains a working local structured proposal composer and an economic calculator, plus screen designs. It is a design artifact, not a deployed SaaS: no accounts, AI calls, payments, persistence, or email delivery. Inputs stay in the browser; exports are local text files. Do not submit confidential material to a public prototype.

### Known versus assumed

- Known from you: YouTube account, Stripe account, GitHub.io presence, approximately S$200,000 available capital.
- Observed repository: extensive AI explanations and interactive HTML demonstrations. This supplies a possible portfolio, not evidence of customers or audience demand.
- Unknown: audience size and buyer fit, Stripe activation and settlement status, available weekly hours, business registration, customer network, existing income and personal runway.
- Planning assumptions: you can commit 15–20 hours/week, demonstrate software yourself, sell in English, and personally deliver the first five pilots. Do not hire a team if these assumptions fail; extend the schedule and test manually.
- No verified market demand, sales pipeline, conversion rate, retention, or profitability. Every target below is a decision threshold or scenario, not a forecast.

### Why this, rather than alternatives?

| Option | Fit with stated assets | Main risk | Decision |
|---|---|---|---|
| YouTube ads | Account exists | Audience and eligibility unknown; indirect monetisation | Use YouTube for distribution, not initial income |
| Generic AI course or prompt shop | Fast to publish | Weak differentiation; many free substitutes | Give away a checklist; do not make this the core offer |
| Trading bot / paid investment signals | Capital available | Capital loss, regulatory and trust risks | Exclude |
| Proposal workflow with paid setup | Technical demonstrations + Stripe | ChatGPT/templates may be sufficient; willingness to pay unknown | Test with real paid workflows first |

This is a conservative product hypothesis, not a claim of being the objectively best market. Concentrate on one segment for 30 days; do not chase multiple niches before interpreting the evidence.

## 2. Buyer, problem, and competitive test

**Buyer:** agency owner responsible for quoting S$3,000–30,000 website projects; initially English-speaking Singapore agencies. Qualification: at least four proposals/month, repeated scope items, no dedicated sales-operations person, willing to share a redacted prior proposal. Expansion to other countries follows evidence, not day-one localisation.

**Trigger:** discovery call completed, proposal needed, owner is assembling scope and rates across notes and old documents.

**Current alternatives:** a prior Word/Google Docs proposal, ChatGPT with copied notes, proposal software, a freelancer, or not changing the process. Do not claim incumbents lack features. Compare the customer's actual method, including their existing tools.

**Possible differentiation:** customer-approved service catalogue; every scope item traceable to a note or explicit manual addition; no invented prices, dates, guarantees or legal terms; explicit exclusions; one complete handoff pack. Templates and an LLM alone are easy to copy. Customer configuration and repeat use are the initial advantage; no defensible moat exists yet.

### Interview and evaluation protocol

Recruit 15 qualified owners, not friends providing encouragement. Ask to walk through their last proposal, preparation time, revisions, tool spend, common scope disputes, and the next proposal due date. Ask: “What would make you keep your current method?” Do not begin with a feature pitch.

For at least five redacted examples, time the customer's current workflow versus QuotePilot. Measure preparation time until they judge the pack client-ready, substantive corrections, and missing/invented commitments. Success target: median preparation time reduction ≥50%, **zero unsupported prices or commitments in the final exported pack**, and at least three out of five independently asking to use it again. Count sales only when paid; distinguish free trial feedback from revenue.

## 3. Offer ladder and direct payment

### Offer A — paid pilot, available before SaaS

S$490 once, five genuine initial slots due to delivery capacity. Includes a 45-minute onboarding, one approved service catalogue, two proposal/follow-up packs delivered within two business days of complete inputs, and one revision per pack. Customer approves all commercial and legal terms; you prepare drafts, never negotiate or send them on their behalf. Pilot covers one agency and no custom integration. Request payment only after showing a sample and agreeing deliverables.

Refund proposal: full refund before work begins; if the agreed first draft is not delivered within two business days of complete input, offer a full refund. After work starts, handle quality disputes against written scope and mandatory consumer/business law with counsel. This proposed policy must be published and accepted before charging; do not use a “no refunds ever” clause. Final terms require legal review.

**Manual order path:** qualified call → sample and written scope → one-time Stripe Payment Link → verify successful payment in Stripe Dashboard → assign order ID and send onboarding within one business day → customer securely submits redacted input → prepare, review, deliver → obtain approval and feedback → offer next purchase or subscription when available. Maintain a ledger of paid, unfulfilled, delivered, refunded and disputed orders. A redirect or screenshot is not proof of payment. Use instant card payments for pilots; do not treat pending payment methods as paid.

### Offer B — subscription, only after repeat-use gate

S$99/month per agency, one owner account, 20 proposal packs per billing month. A pack is one proposal and its three follow-up drafts; two regeneration attempts per pack included, unlimited manual editing. S$20 variable-cost budget/account/month is an assumption to verify. No automatic email, CRM integration, client e-signature, legal drafting, or unlimited AI. Hard quota: offer next-period use or a new plan, not surprise overage billing. No annual plan until retention is observed.

First paid pilots get a clear optional invitation; the pilot does **not** auto-enrol into a subscription. No dual charging for the same deliverable. Existing pilot catalogue can be migrated after consent. Publish cancellation, export and deletion instructions.

### Offer C — optional catalogue setup

S$790 one-time setup for subscription customers, maximum two hours of operator work, one approved catalogue and one onboarding session; no integrations. This is not recurring revenue. Validate it separately; do not rely on it in SaaS break-even calculations.

## 4. Unit economics and capital protection

Baseline assumptions: domestic card fee 3.4% + S$0.50 per successful charge, based on Stripe Singapore listed pricing; actual country, international card, conversion, Billing, taxes, refund and dispute costs can differ. Model a further 1% of subscription revenue for billing/tool charges as an **assumption**, not a quoted Stripe fee. S$8 AI/infrastructure + S$12 support = S$20 variable delivery per account/month. S$2,000 monthly fixed cash overhead plus S$5,000 founder draw; draw is an economic runway assumption, not accounting salary advice. Prices shown before any applicable tax; do not add GST unless entitled/required.

```
Monthly contribution/account = P × (1 − 0.034 − 0.01) − 0.50 − V
At P=99, V=20: S$74.144 (~74.9% contribution margin)
Operating result = accounts × contribution − fixed overhead − founder draw
Break-even accounts = ceil((fixed overhead + draw) / contribution) = 95
```

| Paid accounts | Gross MRR | Contribution | After S$7,000 fixed+draw |
|---:|---:|---:|---:|
| 25 | 2,475 | 1,853.60 | −5,146.40 |
| 75 | 7,425 | 5,560.80 | −1,439.20 |
| 150 | 14,850 | 11,121.60 | 4,121.60 |

These are steady-state arithmetic scenarios, not expected outcomes. Exclude acquisition spend, income tax, GST, chargebacks, working-capital timing and unexpected operating costs; subtract them before calling anything take-home profit. A S$200 cash CAC pays back in approximately 2.7 months at baseline contribution, before churn; founder sales labour also belongs in economic CAC. Do not buy traffic on a theoretical lifetime value. Measure collected contribution by cohort. If monthly churn is 5%, 100 accounts lose about five accounts/month and require five acquisitions just to stay flat; 5% is an illustration, not observed churn.

Pilot economics: S$490 − S$17.16 card fee − S$30 tools − 4 hours × S$60 internal labour = **S$202.84 contribution before acquisition, fixed overhead and tax**. Five pilots yield S$2,450 gross revenue, S$1,014.20 modeled contribution and 20 delivery hours. Pilot income alone is not a business salary. If each pilot takes eight hours, contribution becomes −S$37.16: change scope or stop.

### Capital gates — maximum authorisations, not a spending plan

| Allocation | Cap | Release condition |
|---|---:|---|
| Ring-fenced reserve | 170,000 | Do not expose to product risk; personal runway separate |
| Gate 1: interviews, sample, legal/accounting triage, manual delivery | 5,000 | Initial validation only; aim to spend less |
| Gate 2: production build and security review | 10,000 | Five paid pilots, ≥3 repeat buyers/users, quality/time targets met |
| Gate 3: distribution experiments and operating buffer | 15,000 | ≥10 monthly subscribers, ≥8 of first 10 renew once, acceptable delivery costs |
| Total | 200,000 | Further investment requires a new decision |

Gate 1 suggested ceilings: S$1,500 legal/accounting/privacy review, S$500 domain/hosting/tools, S$1,000 creative/delivery assistance, S$500 targeted experiments, S$1,500 contingency. Gate 2: S$6,000 implementation, S$2,000 security/quality review, S$2,000 contingency. Gate 3: S$3,000 capped acquisition experiments, S$7,000 operating buffer, S$5,000 contingency. Contractor quotes may exceed caps; do not quietly remove security or deliverability to fit the budget. Founder draw must fit actual personal finances; the reserve is not an investment recommendation.

**Stop/pivot:** after 30 qualified sales conversations, fewer than three paid pilots → stop coding and revisit buyer/job/offer. After five pilots, fewer than three repeat uses or no material time saving → do not build SaaS. After first ten subscribers, fewer than eight renew once → interview cancellations before spending on growth. These small samples guide decisions; they do not establish market-wide retention.

## 5. Acquisition system: YouTube → qualified enquiry → paid pilot

Do not wait for YouTube ad monetisation or assume your current viewers are buyers. Direct, personalised outreach supplies early conversations; video provides proof.

**Landing copy:** “Stop rebuilding your web proposals from scratch.” Subheading: “Turn discovery notes and your approved rates into scope, exclusions and follow-up drafts. Review every commitment before it leaves your agency.” Initial CTA: “Request a sample / apply for the S$490 pilot.” Secondary CTA: “See a fictional proposal walkthrough.” Show actual sample output, boundaries, turnaround, pricing, privacy summary and refund terms. No invented reviews, logos, customer counts or unsupported conversion claims.

**First six videos**, one 6–10-minute walkthrough/week plus two excerpts from each:
1. From messy discovery notes to a scoped website proposal.
2. Five exclusions to review before quoting a website.
3. ChatGPT plus a template versus an approved-rate workflow: timed comparison.
4. A follow-up email that asks for a decision without inventing urgency.
5. How scope changes affect a quote: show the line items.
6. Redacted customer case, only with written publication consent; otherwise fictional example clearly labelled.

Open with the concrete document problem, show before/after, review the limitations, then one CTA. Use a unique UTM per video; one link to a commercially permitted landing host. Publish in the language buyers actually use; English is the initial assumption, not evidence of current audience fit. No mass scraping, purchased lists or unsolicited WhatsApp/SMS blasts. Respect opt-outs and applicable marketing/DNC rules.

**First outreach message:** “Hi [name], I’m testing a proposal-preparation workflow for small web agencies. It uses your own service rates and keeps scope assumptions visible. If preparing quotes is a recurring bottleneck, could I show a fictional example and learn how you handle it today? No client data needed.” Use real names manually, not fake personalisation.

**Weekly operating targets:** 25 genuinely relevant contacts, five conversations, two sample walkthroughs, one paid pilot as a target—not a funnel forecast. Ask referrals only after successful delivery. Do not offer undisclosed affiliate payments.

**Measurement:** source/UTM, qualified enquiry, booked call, attended call, sample reviewed, paid order, first pack approved, repeat use, renewal, cancellation and refund. Report numerator, denominator and cohort dates. Never send proposal text, client names or sensitive amounts to analytics. Operational success is paid activation and renewal, not views.

**Ads gate:** no ads until five paid pilots. Experiment cap S$500 initially. Pause a channel after S$300 spend without a qualified call; do not label it universally ineffective from that small test. Growth gate: observed cash CAC ≤S$200, cohort contribution payback ≤3 months, and support/time limits met. Record founder acquisition hours separately.

## 6. Product design and complete first-release scope

### Screens and states

1. **Public landing:** sample, offer, FAQ, privacy, terms, real support contact. Pilot CTA opens a real enquiry route only after deployment; no pretend checkout.
2. **Account / billing:** verified email sign-in; agency name, plan, renewal date, used/remaining packs, cancel at period end, Stripe customer portal, download/delete data. An empty paid account has an onboarding CTA.
3. **Catalogue:** service name, unit, approved SGD rate, included deliverables, exclusions and approved payment terms. Rate edits apply only to new proposal versions; prior exports remain immutable.
4. **New proposal:** client/project labels, pasted notes (max 20,000 characters initially), selected catalogue items and quantities, desired timeline explicitly entered by user. Warn against personal/sensitive data. No recordings/uploads in first release.
5. **Review:** source panel beside generated scope; per item: source quote/reference or “manually added”; editable price, assumptions, exclusions, unresolved questions. Customer-supplied facts and AI-suggested wording visibly distinct. Block final export until prices and commitments are confirmed. Missing information stays a question, never a fabricated fact.
6. **Delivery pack:** branded printable proposal, plain-text copy, three email drafts; no automatic sending. Preview totals and exact version before export. Export filename includes project and version without unsafe path characters.
7. **History:** drafts/reviewed/exported status, creation/update times and versions. Duplicate to a new draft; no silent modification of previously exported version. Cancelled customers can export during grace period.

### Journey and errors

New → collecting input → queued → generating → review required → approved → exported. AI error → retryable failure, not a false complete state. Payment pending → pending access, with clear status and support. Empty catalogue → setup required. Quota reached → manual edit/export of old packs still available. Session expired → re-authentication without uploading secrets to URL. Delete → confirmation, removal from active storage, disclosed backup expiry. Export is a versioned action, not acceptance by the client.

AI proposes wording and scope candidates only. Server validates output against a schema; catalogue IDs and money values must match approved records. Client notes are untrusted data, never model instructions. No model ability to send email, access arbitrary URLs, execute tools, or change pricing. Customer enters final quantities, rates, timeline and terms. Version-controlled prompt evaluation on redacted/fictional inputs must catch unsupported commitments and instructions embedded in notes.

### Acceptance criteria for the production release

- A paid user can onboard, configure catalogue, submit notes, review source-linked scope, edit, approve and export a complete pack; the model cannot silently change catalogue prices.
- A non-paying or wrong-tenant account cannot read, generate or export another agency's documents. Object-ID guessing and browser-side entitlement changes fail.
- A duplicated Stripe event cannot grant twice; an unpaid Checkout return cannot grant access; a paid order without a browser return still receives access.
- Invalid AI output, timeout and quota exhaustion display recoverable states and do not burn a pack credit without a successful result. Concurrent generation cannot overspend credits.
- Old export remains unchanged after catalogue edits; approval is invalidated when commitments change.
- Cancellation stops future renewals; failed renewal prompts update-payment action and grants only the disclosed grace policy; refund/dispute changes reconcile access.
- Screen-reader labels, keyboard operation, mobile layout, explicit errors and usable contrast; printable output does not depend on animations.
- Restore a backup into a clean environment; verify deletion policy, operator access log and per-tenant isolation before live customer input.

**Not in first release:** CRM sync, e-signature, multi-currency, team roles, public client document links, automatic emails, lead scraping, auto-negotiation, audio transcription, financial/legal advice. These are deliberate product boundaries, not incomplete implementations.

## 7. Implementation architecture and security

**Commercial host:** custom domain on paid Cloudflare Pages/Workers or another host permitting commercial use. Keep GitHub for source; GitHub.io remains an educational portfolio, not checkout or the commercial SaaS. DNS/domain availability and host plan terms need verification. Initial infrastructure budget is S$150/month inside variable/fixed assumptions; obtain actual quotes.

**Stack decision:** TypeScript app and API on one origin, managed PostgreSQL and verified-email auth, private object storage for immutable exports if needed, one model provider behind a server-side adapter, Stripe-hosted Checkout and customer portal. Prefer one service and one database; no vector database, multi-agent orchestration or Kubernetes. Choose database/model region and contracts only after privacy review. No new permanent dependencies for the local design artifact.

**Data model:** Agency(id, ownerId, retentionPolicy); CatalogueItem(agencyId, version, name, unit, rateMinor, currency, inclusions, exclusions); Proposal(agencyId, version, input, sourceRefs, lineItems, assumptions, questions, status, approvedAt); GenerationJob(agencyId, proposalId, idempotencyKey, status, creditReservation, result); Subscription(agencyId, stripeCustomerId, stripeSubscriptionId, status, paidThrough); Order(agencyId, checkoutSessionId UNIQUE, paidStatus, fulfillmentStatus); BillingEvent(stripeEventId UNIQUE, processedAt); UsageLedger(agencyId, billingPeriod, jobId UNIQUE, reserved/consumed/released); Audit(agencyId, actor, action, objectId, timestamp). Store money as integer minor units, not floating point.

**Endpoints:** POST /checkout (authenticated, server-selected allowlisted price, bind agency); POST /stripe/webhook (raw-body signature verification); GET /billing (server entitlement); POST /billing/portal (owned customer only); CRUD /catalogue; POST /proposals; POST /proposals/:id/generate (idempotent, transactional quota reservation); GET /jobs/:id; PATCH /proposals/:id (expected version); POST /proposals/:id/approve; GET /proposals/:id/export; GET /account/export; DELETE /account. Every data query is agency-scoped server-side; enforce database row-level controls as defence in depth. Rate-limit login and generation; CSRF protection for cookie-authenticated writes. No secrets in frontend or repository.

### Subscription/payment state contract

- Start pilots with Dashboard-verified one-time payments and manual ledger. Automated subscriptions require production webhooks before selling.
- Verify Stripe signature using raw body; record event IDs; durably enqueue/process idempotently. Bind actual Stripe customer/subscription to agency using server-created metadata, not user-provided arbitrary IDs.
- Retrieve current Stripe objects before entitlement transitions so out-of-order events cannot revive cancelled access. Allowlisted product/price IDs and verified paid status decide fulfillment.
- Checkout completion can link account/order, but subscription paid-through follows verified paid invoices (invoice.paid) and current subscription. A success page only polls server state.
- Handle checkout.session.completed, asynchronous success/failure if enabled, invoice.paid, invoice.payment_failed, customer.subscription.updated/deleted, refund and dispute events. Use a transactional order/usage ledger; webhook retries cannot duplicate access or credits.
- Failed renewal: notify, three-day disclosed grace, then generation read-only; exports retained for 30 days. Cancel at period end: access until paidThrough, no automatic annual commitment. Refund/dispute: reconcile remaining entitlement and investigate, never silently keep charging.
- Scheduled reconciliation compares local paid-through with Stripe and alerts on mismatch; do not log payment card data. Send a real receipt and fulfillment email with support contact.

### Privacy and operational controls

Redact client identifiers during pilots. Publish collection purpose, legal basis/consent approach, retention and subprocessors; identify a DPO/contact. Confirm customer authority to submit data; use contracts for overseas transfers and processing, assess PDPA applicability with counsel. Provider must contractually support suitable data handling; do not promise “never trained on your data” without verifying its actual terms/settings.

Proposed default: source notes deleted 30 days after final export; proposals retained until customer deletion or 90 days after cancellation; active copies deleted within seven days of verified deletion; backups expire within 30 days; accounting records retained as required separately without proposal content. These are policies to implement and disclose, not properties of the prototype. Operator access requires explicit support purpose and audit; prohibit sensitive production payloads in logs. Minimal analytics; no customer content in event payloads. Incident procedure: contain, revoke secrets, establish impact, consult counsel on notification, communicate facts, restore and reconcile.

Register/verify the appropriate Singapore business entity and Stripe identity/bank account before selling. Track taxable turnover and monitor IRAS compulsory GST rules: more than S$1 million under retrospective calendar-year or prospective next-12-month tests; thresholds and deadlines depend on facts. Obtain accounting advice on exported services, overseas customers, income tax and deductibility; capital is not taxable turnover. Start domestic B2B sales to reduce, not eliminate, cross-border complexity. Legal/privacy/marketing checks are launch prerequisites, not a claim this design is compliant.

## 8. Ninety-day execution with owners and gates

Owner is you unless a contractor is explicitly hired. Weekly review: cash spent, qualified conversations, payments/refunds, delivery hours, pack approvals, repeat use and renewal cohorts.

| When | Deliverable | Responsible | Exit condition |
|---|---|---|---|
| Days 1–7 | 15 interviews scheduled, 5 completed; fictional sample; commercial domain/host selected; business/payment/legal review begun | Founder | Three buyers show recurring problem and an actual upcoming proposal |
| Days 8–14 | Remaining interviews; sample walkthroughs; publish permitted commercial landing, exact pilot scope/terms and secure intake; create real one-time Payment Link | Founder + counsel/accountant | Real payment verified and first delivery booked; no checkout until terms ready |
| Days 15–30 | Deliver five paid pilots and publish four weekly walkthroughs; log before/after time and corrections | Founder | Five paid, ≥3 repeat uses, median ≥50% time saving, no unsupported commitments in final packs |
| Days 31–45, only if gate passes | Implement catalogue, auth, source-linked review, deterministic pricing and export; select processor contracts | Founder/contractor | Full workflow on fictional data; cross-tenant isolation and output review verified |
| Days 46–60 | Stripe test-mode lifecycle, quota concurrency, failed generation, export/deletion/restore, mobile/accessibility and security review | Founder + reviewer | Acceptance criteria pass; deploy then one authorised real low-value payment/refund reconciliation |
| Days 61–90 | Invite first 10 subscribers; weekly onboarding and usage interviews; observe first monthly renewals; capped channel experiments only after gates | Founder | ≥8/10 renew once, measured unit costs, contribution payback target; otherwise hold growth |

Day 90 is a review, not a promise of S$10,000 MRR. Build schedule assumes founder execution or a contractor within budget; no deadline justifies bypassing payment correctness, privacy or tenant isolation. If validation takes longer, shift the build, not the gates.

### First seven concrete actions

1. Identify 30 suitable agencies and send five individually relevant interview invitations/day.
2. Use the companion composer to prepare a fictional scope sample and timed demonstration.
3. Run five interviews; record current workflow and quote frequency without collecting unnecessary client data.
4. Review the S$490 scope with one willing buyer; obtain explicit acceptance before asking for payment.
5. Complete business/Stripe/terms/privacy checks and commercially permitted hosting; create the actual Payment Link yourself in your account.
6. Deliver the first pack manually and measure client-ready time and correction burden.
7. Decide on day 30 from paid/repeat evidence; keep the remaining capital untouched.

## 9. Risks, controls, and decision log

| Risk | Leading signal | Control / decision |
|---|---|---|
| No willingness to pay | Interested calls but no orders | Charge for bounded pilot; stop on sales gate |
| ChatGPT/template sufficient | No time saving or repeat use | Benchmark actual alternative; no platform build without advantage |
| Low workflow frequency | Less than four proposals/month | Qualify or prefer per-project service; do not force subscription |
| AI invents commitment | Unsupported rate/date/scope | Approved catalogue, source refs, explicit human approval; block export |
| Service overwhelms founder | >4 hours per pilot or growing support | Bound scope, log time, change pricing before hiring |
| Acquisition expensive | Cash CAC >S$200 or payback >3 months | Stop ads; inspect channel and retention |
| Privacy/data leak | Wrong-tenant access or provider terms unsuitable | Isolation review, redaction, processor contracts; no live data until resolved |
| Payment disputes | Misunderstood scope or duplicate fulfillment | Written deliverables, verified payment, order ledger and clear refund policy |
| Founder cannot sustain cadence | Missed onboarding/delivery | Reduce pilot slots and extend timeline; no fabricated automation |

Decision: service-first validation; subscription only after repeat use. No production integration is asserted by this document. Required account actions and legal decisions remain with the owner; no account credentials or live Payment Link are present in this repository.

## 10. Primary sources and freshness

Sources consulted 2 October 2026; provider pricing and rules can change. Recheck before live launch.

- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits): prohibits Pages as hosting for an online business, e-commerce site or commercial SaaS; do not build checkout there.
- [Stripe Singapore pricing](https://stripe.com/en-sg/pricing): listed domestic card pricing; the model's additional 1% charge reserve is a planning assumption, not a Stripe quote.
- [Stripe Checkout fulfillment](https://docs.stripe.com/checkout/fulfillment?payment-ui=stripe-hosted): manual fulfillment at low volume, verified payment status, required automated webhooks for subscriptions, idempotency and asynchronous payment events.
- [IRAS: Do I need to register for GST?](https://www.iras.gov.sg/taxes/goods-services-tax-(gst)/gst-registration-deregistration/do-i-need-to-register-for-gst): compulsory registration thresholds and timing; not legal/accounting advice.
- [PDPC data protection impact assessment guide](https://www.pdpc.gov.sg/-/media/files/pdpc/pdf-files/other-guides/dpia/guide-to-data-protection-impact-assessments-14-sep-2021.pdf): assess data processing risks and safeguards; obtain current legal review.

## 11. Design verification

Served the HTML locally and exercised it in Chromium at desktop width and 390px mobile width. Observed: edited client/fee appear literally in the proposal preview; approval enables export; changing the timeline clears approval and disables export; baseline calculator gives S$7,425 MRR, S$74.14 contribution/account, −S$1,439.20 after costs/draw, 95-account break-even and 2.7-month cash CAC payback. Delivery cost S$120 yields “Not viable” / “No payback”; negative account count displays validation and clears results. Desktop composer and mobile hero/calculator visually inspected; mobile document had no horizontal overflow. Browser error log was empty.

Export click reached “download requested,” but the automation environment did not expose a saved file, so saved-file contents are **not verified**. No live payment, AI, account, email or production security flow was exercised; those are production acceptance criteria, not features asserted by this design.
