# Maison Lumen: cart and promo-code API, specification v1

*Maison Lumen* is a fictional online shop. This document is the reference for how the API must behave. If the running server and this document disagree, the server is wrong (unless you think the document is unclear: then say so in your note).

## 1. Conventions

- JSON in, JSON out. Money is always an **integer number of cents** (`1995` means 19.95 EUR). Prices include VAT; there is no VAT breakdown.
- Errors have the shape `{ "error": "message" }`.
- Status codes:

| Code | Meaning |
|---|---|
| 200 / 201 | success / resource created |
| 400 | the request itself is invalid (missing field, wrong type, value out of range) |
| 404 | unknown resource (cart, product, order, promo code) |
| 409 | the request is valid but conflicts with the current state (not enough stock, illegal status change, cart already checked out, second discount code) |
| 422 | the request is valid but a business rule refuses it (quantity limit, minimum subtotal, expired code, empty cart) |

## 2. Endpoints

| Method and path | Purpose |
|---|---|
| `GET /products`, `GET /products/:id` | catalogue: `id, name, priceCents, stock` |
| `POST /carts` | create an empty cart (201) |
| `GET /carts/:id` | the cart with its totals |
| `POST /carts/:id/items` | body `{ productId, quantity }`: add a product |
| `PATCH /carts/:id/items/:productId` | body `{ quantity }`: set the quantity of a line |
| `DELETE /carts/:id/items/:productId` | remove a line |
| `POST /carts/:id/promo` | body `{ code }`: apply a promo code |
| `POST /carts/:id/checkout` | turn the cart into an order (201) |
| `GET /orders/:id` | the order |
| `POST /orders/:id/pay`, `/ship`, `/cancel` | change the order status |
| `POST /reset` | test helper: restores the initial data |

Every cart endpoint returns the cart: `id, status (open | checked_out), promoCodes, items[] (productId, name, unitPriceCents, quantity, lineTotalCents), subtotalCents, discountCents, shippingCents, totalCents`.

## 3. Quantities and stock

1. On `POST .../items`, `quantity` must be an integer of at least 1. On `PATCH`, it must be an integer of at least 0, and `0` removes the line. Otherwise: 400.
2. A cart holds **at most 10 units of the same product** (the quantity of the line, not of one request). Above that: 422.
3. A line can never hold more units than the current stock. Exactly the stock is allowed. Above: 409. Stock is checked when a product is added or changed, and checked again at checkout.
4. Adding a product that is already in the cart increases its line (200). Adding a new product creates a line (201).
5. A cart that is `checked_out` cannot be modified any more: 409.

## 4. Totals

Totals are recalculated from the cart every time it is read, in this order:

1. `subtotalCents` = sum of the lines (`unitPriceCents * quantity`).
2. `discountCents` = the discount given by the promo code (section 5), computed on the subtotal. A percentage is **rounded half up to the nearest cent**. The discount never exceeds the subtotal.
3. `shippingCents` = **490**, unless the subtotal **after discount** is **5000 or more**, or the code `FREESHIP` is on the cart, or the cart is empty: then 0.
4. `totalCents` = subtotal - discount + shipping.

## 5. Promo codes

| Code | Effect | Condition |
|---|---|---|
| `WELCOME10` | 10 % off the subtotal | none |
| `FIVEOFF` | 500 cents off the subtotal | subtotal (before discount) of **3000 or more** |
| `SUMMER25` | 25 % off the subtotal | valid until 31 August 2026 (UTC) included |
| `FREESHIP` | shipping is free | none |

- `WELCOME10`, `FIVEOFF` and `SUMMER25` are *discount codes*. A cart can hold **at most one discount code**, plus optionally `FREESHIP`. Applying a second discount code is refused (409) and the cart does not change.
- Applying a code that is already on the cart changes nothing (200).
- Applying `FIVEOFF` while the subtotal is below 3000 is refused (422). An expired code is refused (422). An unknown code gives 404.
- A code gives a discount only while its conditions are met: the totals always describe the cart as it is now.

## 6. Checkout and orders

- `POST /carts/:id/checkout` requires an open, non-empty cart (empty: 422). If any line exceeds the current stock: 409 and nothing changes.
- On success: 201, an order with status `pending_payment` and a copy of the items and totals; the stock is decreased; the cart becomes `checked_out`.
- **The stock can never become negative**, including when two customers check out at the same time.
- Order statuses and the only allowed changes:

```
pending_payment --pay--> paid --ship--> shipped
pending_payment --cancel--> cancelled
paid --cancel--> cancelled
```

  `shipped` and `cancelled` are final. Any other change: 409. Cancelling an order gives the stock back.
