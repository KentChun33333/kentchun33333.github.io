---
name: stripe-cashier
description: Set up or verify a direct-sale cashier flow (收銀台) with Stripe Payment Links. Use for a fixed-price service or digital product, buyer checkout, payment confirmation, manual fulfillment, or a cash-in-bank deadline.
---

# Stripe Cashier（收銀台）

Use an existing Stripe Payment Link if it matches the offer. A link collects payment; it does not find buyers. Do not build a storefront, add webhooks, or change OpenMemo to complete a direct order.

## 1. Pin down the order

- Capture the item or fixed scope, deliverable, turnaround, total price and currency, and when cash must reach the bank. Reuse facts already provided. For custom work, agree on scope and refund terms before charging; only request redacted samples.
- If the lead came from a marketplace, use its payment flow when its rules require it. Don't move the buyer off-platform. Confirm any required employer approval before offering paid work.
- For the Singapore bill scenario: quote **S$35 once** for one bounded Excel, CSV, or Python fix. At Stripe Singapore's published standard domestic-card rate (3.4% + S$0.50), the estimated proceeds are **S$33.31 before any other charges**. Recheck [local pricing](https://stripe.com/en-sg/pricing) and the seller's pricing if the net amount matters.

## 2. Verify the link or prepare one

1. Open only the seller-supplied public Stripe link (`https://buy.stripe.com/…`) in an isolated buyer view. Do not enter personal or payment details or submit checkout. Record the product, amount, currency, quantity, billing interval if any, and any test-mode banner. Report what you could not verify. A matching preview is not evidence of live payment capability.
2. If the link is missing, inactive, test-only, or mismatched, prepare the exact settings for the account owner in [Stripe Dashboard → Payment Links](https://dashboard.stripe.com/payment-links): product name and description, one-time fixed price in the agreed currency, quantity one with quantity adjustment off, and a confirmation message with the agreed delivery or intake instructions. Use a separate matching link rather than silently changing a link that buyers may already have. Never request API keys, account passwords, or card details.
3. Preview again before sharing. For proof of a complete checkout, use Stripe's sandbox only, with its test link and test payment details, and report the result as test-only. Get explicit approval before creating or changing a live link, sending it to a buyer, or making any other live transaction or refund. Do not charge a live card to verify a link.

## 3. Check payout against the deadline

- Check the account's bank payout status and expected deposit date in [Stripe Payouts](https://dashboard.stripe.com/payouts), or ask the owner for the date if the Dashboard isn't accessible. For a new order with no payout estimate, use the account's settlement timing and payout schedule as an estimate, not a guarantee. Stripe says a [first payout typically takes 7–14 days](https://docs.stripe.com/payouts).
- Successful payment, available Stripe balance, and money in the bank are separate states. If arrival cannot be confirmed by the deadline, say so. For an eligible direct Singapore sale, offer direct PayNow before sharing checkout if seller and buyer agree; verify funds in the receiving bank. Avoid a duplicate payment if Stripe has already been used or is processing.

## 4. Confirm payment and deliver

1. Once scope is agreed, send the approved link with the price and delivery timing. Assign an order ID and record only the information needed to fulfill the order. Keep the ledger out of the repository.
2. Before fulfillment, match the order, amount and currency to a **successful live payment** in [Stripe Dashboard → Payments](https://dashboard.stripe.com/payments), or a bank credit for direct PayNow. A screenshot, return URL, email alone, pending payment, or sandbox event is not payment proof. See [Stripe's post-payment guide](https://docs.stripe.com/payment-links/post-payment).
3. Deliver via the agreed private channel and record delivery separately from bank payout. Mark failures, refunds, and disputes without counting them as collected revenue.

## Return to the seller

Report **offer**, **checkout evidence** (verified, mismatch, or unverified), **expected net and bank-arrival status**, and **next action**. Never report an order paid, delivered, or deposited without evidence for that state.

For this repository, OpenMemo's [`/boutique`](../../webapp/frontend/src/App.jsx) is sign-in protected and the [`payments.py` route](../../webapp/backend/routers/payments.py) generates a new Checkout Session per attempt. Neither is the seller's reusable Payment Link; don't use a session URL as the public cashier link.
