# Order requests and fulfillment MVP

This release adds **manual cash-on-delivery order requests** for *real, approved marketplace products only*. It does not collect money or calculate final delivery fees. Demo items cannot be ordered.

## Flow

1. Customer signs in, selects **Buy now** on an approved, stocked seller product or visits checkout from the real marketplace bag.
2. Checkout validates contact name, phone, address and explicit agreement. Product price and stock are checked by the server, not read from posted prices.
3. The request creates a product-price snapshot and an order line for each seller product. Available inventory is **reserved**, not immediately deducted.
4. The seller sees only their store's order lines under **Seller center → Store orders**, and moves pending → processing → shipped → delivered. Before shipping, the seller may cancel; the customer may cancel only a pending line.
5. Cancelling releases the reservation. Marking delivered deducts physical quantity and reservation and writes an append-only stock movement. Repeating a completed status action cannot deduct twice.

## Safety

- The user's browser does not set unit prices or seller IDs.
- Source cart lines are removed only after successful transactional order creation.
- Checkout token prevents repeated service-level submissions from duplicating orders; PostgreSQL row locks + conditional stock updates protect concurrent requests.
- Seller and buyer access is scoped to the authenticated account. POST actions enforce CSRF.
- On order placement, stock remains reserved until line is cancelled or marked delivered; there is **no automatic expiry yet**.
- Seller delivery confirmations are manual assertions. No carrier integration, payment reconciliation or refunds.
- **All price totals exclude delivery fees/taxes**; do not treat the displayed product subtotal as the final payable amount.
- SQLite is fine for local development, but concurrent order/stock paths need PostgreSQL transaction tests before production.

## Local verification

```powershell
git switch feat/order-checkout-fulfillment-mvp
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q
npm.cmd run build:css
```

Before `python manage.py migrate`, back up the local SQLite database. This feature introduces an additive `orders.0001_initial` migration, no data reset or fake migrations.

Manually verify both direct Buy now and multi-seller cart checkout, address validation, saved order history, cancellation, seller authorization, out-of-stock behavior, and delivery stock movement.

## Still required before production

- Online payments (verified provider webhook, asynchronous capture and refund reconciliation).
- Shipping rates, delivery zones, VAT/tax calculation, carrier tracking.
- Customer and seller communication/notification system.
- Cancellation and return/refund policy, seller settlement and dispute workflows.
- Reservation expiry/recovery and operational monitoring.
- Production storage (S3/R2), email/SMS provider, PostgreSQL concurrency tests, deployment/security review.
