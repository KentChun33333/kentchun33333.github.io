# Knowledge Distill Skill — Worked Example

## Scenario: Legacy Checkout Service Migration
A engineering team needs to migrate a legacy e-commerce checkout service to a new microservices platform. The files are messy, undocumented, and contain outdated specs. The analyst executes the **Knowledge Distill Skill** to establish a clean, source-grounded understanding.

---

## 1. Loop 1: Discover

The analyst catalogs the inputs and assigns IDs.

### Output: `data-cooked/source-index.md`
```markdown
# Source Index

| Source ID | Raw Path | Type | Size | Parse Difficulty | Notes |
|---|---|---:|---:|---|---|
| source-001 | data-raw/checkout_v2_spec.pdf | PDF | 1.8 MB | medium | Core spec with API definitions and business rules |
| source-002 | data-raw/state_machine.png | PNG | 450 KB | high | Flowchart of transaction states (requires visual OCR) |
| source-003 | data-raw/payment_errors.csv | CSV | 12 KB | low | Mapping of gateway error codes to user-facing messages |
| source-004 | data-raw/schema.sql | SQL | 4 KB | low | Legacy PostgreSQL schema for order and payment tables |
```

### Output: `analysis/discovery.md`
```markdown
# Discovery Report

- **Folder Summary**: Contains the checkout spec PDF, a state machine diagram, a database schema, and an error code CSV mapping.
- **Key Focus Areas**: The Stripe/PayPal gateway integration (source-001) and order states (source-002).
- **Noisy / OutofScope Files**: A deprecated v1 checkout spec found in a subfolder was excluded as a duplicate/obsolete.
- **Parsing Strategy**: 
  - `source-001` (PDF): Standard Python extraction.
  - `source-002` (PNG): Vision-based extraction of transitions and events.
  - `source-003` (CSV): Python CSV-to-Markdown table converter.
  - `source-004` (SQL): Structural SQL schema summary generator.
```

---

## 2. Loop 2: Define Cook Spec

### Output: `analysis/parse-plan.md`
```markdown
# Parse Plan

- **source-001**:
  - raw_path: `data-raw/checkout_v2_spec.pdf`
  - parser_strategy: pdf-text-extract (using PyPDF)
  - output_md_path: `data-cooked/source-001.md`
  - known_risks: Layout contains two-column text; might extract out of sequence.

- **source-002**:
  - raw_path: `data-raw/state_machine.png`
  - parser_strategy: vision-description-ocr (using multimodal LLM)
  - output_md_path: `data-cooked/source-002.md`
  - known_risks: Resolution is low; text on state transition arrows might be blurry.
```

---

## 3. Loop 3: Cook

Below is an example of a cooked source document.

### Output: `data-cooked/source-001.md`
```markdown
# Cooked Source: source-001

- Raw file: `data-raw/checkout_v2_spec.pdf`
- Type: PDF
- Parser: pdf-text-extract (v1.2)
- Parsed at: 2026-05-22
- Confidence: high
- Notes: Double-column layout successfully reconstructed.

---

## Section 1: Checkout Initialization
The checkout session is initiated by sending a POST request to `/v2/checkout/session` with the `cart_id` and `user_id`. 
The system returns a `session_token` valid for 15 minutes.

## Section 2: Payment Gateways
We support Stripe for Credit/Debit Cards and PayPal. 
An idempotency key (header `X-Idempotency-Key`) is REQUIRED for Stripe charge calls to prevent double charging.
```

---

## 4. Loop 4: Analyze

The analyst synthesizes findings across the cooked documents.

### Output: `analysis/flow.md`
```markdown
# Flow Analysis — Checkout Lifecycle

## 1. Executive Summary
The checkout flow converts a user's cart into a completed order by validating inventory, reserving items, calling external payment gateways (Stripe/PayPal), and creating a final database record.

## 2. Sequence of Stages
| Step # | Stage Name | Actor(s) | Inputs | Outputs | Source IDs |
|---|---|---|---|---|---|
| 001 | Initialization | Client App | Cart ID, User ID | Session Token | source-001 |
| 002 | Inventory Reservation | Inventory Service | Cart Items | Holds Created | source-001, source-004 |
| 003 | Payment Processing | Payment Gateway | Token, Payment Method | Transaction ID | source-001, source-002 |
| 004 | Completion | Order Service | Transaction ID | Order Confirmation | source-001, source-004 |

## 3. Decision Logic & Gates
- **Payment Success Gate**:
  - **Gateway Status = SUCCESS**: Advance to order completion.
  - **Gateway Status = FAILED (Soft Decline)**: Show user error message (source-003) and prompt to retry payment.
  - **Gateway Status = FAILED (Hard Decline)**: Cancel inventory reservations and void checkout session token.

## 4. Exceptions & Failure Modes
- **Idempotency Conflict**: If Stripe is called with an already used `X-Idempotency-Key`, Stripe returns HTTP 409. The system recovers by fetching the existing payment details instead of creating a new charge. (Source: source-001)
```

### Output: `analysis/dependency.md`
```markdown
# Dependency Analysis — Checkout Service

## 1. System & Entity Relationships
- **External Dependencies**:
  - **Stripe API**: Process credit cards. Downstream dependency on Stripe webhook listeners for asynchronous failures. (Source: source-001)
  - **PayPal API**: Process PayPal balances. (Source: source-001)
- **Internal Dependencies**:
  - **Inventory Service**: Lock inventory items (holds expire in 15 minutes). (Source: source-001, source-004)

## 2. Critical Path Analysis
- **Critical Path**: Initialize Session → Lock Inventory → Process Payment Gateway → Commit Order to DB.
- **Single Point of Failure (SPOF)**: The Inventory Service. If it goes down, checkouts cannot proceed even if payment gateways are fully online. (Source: source-001)
```

---

## 5. Loop 5: Knowledge Summary

The final, clean reference guides for the developers are heavily compressed and deduplicated to maximize information density.

### Output: `knowledge/big-picture.md`
```markdown
# Big Picture Reference: Checkout Platform

## 1. Purpose & Context
The Checkout Platform manages user checkout sessions, coordinates inventory locks to prevent overselling, processes payment tokens through 3rd-party gateways, and transitions carts into finalized orders.

## 2. Core Operational Lifecycle
The system operates on a stateful 15-minute lease:
1. Client initializes the session, placing a 15-minute lock on inventory.
2. User submits payment details, invoking Stripe or PayPal.
3. System verifies payment response and transitions order state to `PAID` or `FAILED`.
4. Order details are persisted and downstream logistics are notified.

## 3. System Boundaries & Constraints
- **Session Duration**: Strictly 15 minutes. Payments received after 15 minutes must be auto-refunded because inventory holds expire.
- **Idempotency**: All payment transactions must use the client-generated idempotency key (header `X-Idempotency-Key`).
```

### Output: `knowledge/workflow-reference.md`
```markdown
# Workflow Reference Guide: Checkout Lifecycle

For core platform constraints and session duration limits, see [knowledge/big-picture.md](big-picture.md).

## 1. Stacking Flow Diagram

```text
[Input Data Contract]                 [Core Module]                    [Output Data Contract]
=====================                 =============                    ======================
Cart ID, User ID           -->   Checkout Initialization   -->   Session Token (15m lease)
                                                                 (Source: source-001)

Cart Items, Session Token  -->    Inventory Reservation    -->   Inventory Holds Created
                                                                 (Source: source-001, source-004)

Payment Method, Token      -->     Payment Processing      -->   Gateway Transaction ID & Status
                                                                 (Source: source-001, source-002)

Transaction ID             -->     Checkout Completion     -->   Order Confirmation & Persistence
                                                                 (Source: source-001, source-004)
```

## 2. Key Error Handling Policies
1. **Soft declines** (e.g., Code `ERR_CARD_DECLINED`): The user remains on the payment screen. Inventory hold timer does NOT reset. (Source: source-003)
2. **Hard declines** (e.g., Code `ERR_FRAUD_BLOCKED`): Immediate transition to `CANCELLED`. Inventory released. (Source: source-003)
```
