# Bug reports: Maison Lumen cart and promo API

All reports were reproduced on a fresh server (`POST /reset` first). Each has an automated test marked `xfail(reason="BUG-xx", strict=True)`: it stays red until the bug is fixed, then the strict mark forces its removal.

| ID | Title | Severity | Priority |
|---|---|---|---|
| BUG-01 | Parallel checkouts oversell: stock becomes negative | Critical | 1 |
| BUG-02 | Quantity 0, negative or decimal accepted when adding to a cart | Critical | 2 |
| BUG-03 | Several discount codes can be stacked | Critical | 3 |
| BUG-04 | Unpaid order can be shipped | Critical | 4 |
| BUG-05 | FIVEOFF keeps its discount after the subtotal drops below 3000 | Major | 5 |
| BUG-06 | 10-unit line limit checked per request, not per line | Major | 6 |
| BUG-07 | Adding exactly the available stock is refused | Major | 7 |
| BUG-08 | Free shipping decided on the subtotal before discount | Major | 8 |
| BUG-09 | Percentage discount rounded down instead of half up | Minor | 9 |
| BUG-10 | Expired promo code returns 404 instead of 422 | Minor | 10 |

Priority logic: first what loses stock or money without any effort from an attacker (01 to 04), then rule violations with a bounded cost (05 to 08), then cosmetic cents and status codes (09, 10).

---

## BUG-01: Parallel checkouts oversell, stock becomes negative

- **Severity / Priority:** Critical / 1. Customers pay for goods that do not exist; trivially triggered by two simultaneous customers.
- **Specification reference:** SPEC 6, "The stock can never become negative, including when two customers check out at the same time."
- **Steps to reproduce:**
  1. `POST /reset`
  2. Create 5 carts (`POST /carts` x5, ids c1..c5) and add 3 Wool Throws (product 5, stock 5) to each: `POST /carts/cN/items {"productId":5,"quantity":3}`
  3. Send `POST /carts/c1/checkout` ... `POST /carts/c5/checkout` at the same time.
  4. `GET /products/5`
- **Expected result:** one checkout returns 201, the four others 409; stock is 2.
- **Actual result:** all five return 201; `{"id":5,...,"stock":-10}`.
- **Notes:** reproduced every run. Likely cause: `checkout` checks the stock, then waits 25 ms (payment pre-authorisation), then decrements, so every request passes the check before any decrement. Test: `test_concurrency.py::test_parallel_checkouts_never_oversell`; a serial control test passes, which isolates the race.

## BUG-02: Quantity 0, negative or decimal accepted on `POST /carts/:id/items`

- **Severity / Priority:** Critical / 2. A negative quantity produces a negative subtotal and a negative total.
- **Specification reference:** SPEC 3.1, quantity must be an integer of at least 1, otherwise 400.
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`
  2. `POST /carts/c1/items {"productId":1,"quantity":-1}`
- **Expected result:** 400.
- **Actual result:** 201, `"quantity":-1,"lineTotalCents":-1995,"subtotalCents":-1995,"totalCents":-1505`. With `0` the response is 201 with an empty-value line; with `1.5` the response is 201 with `lineTotalCents` 2992.5 (not an integer number of cents, breaking SPEC 1).
- **Notes:** always. Cause: the server only checks `typeof quantity === "number"`. I did not test what a checkout of such a cart does to stock or orders (not in my time budget): it should be checked once this is fixed or by the developers. Strings and null are correctly refused (tests pass).

## BUG-03: Several discount codes can be stacked

- **Severity / Priority:** Critical / 3. Direct loss of revenue, and the customer can combine every code.
- **Specification reference:** SPEC 5, at most one discount code per cart; a second one is refused with 409 and the cart does not change.
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`
  2. `POST /carts/c1/items {"productId":5,"quantity":1}` (8900)
  3. `POST /carts/c1/promo {"code":"WELCOME10"}` then `POST /carts/c1/promo {"code":"FIVEOFF"}`
- **Expected result:** second call 409, `promoCodes` still `["WELCOME10"]`.
- **Actual result:** 200, `"promoCodes":["WELCOME10","FIVEOFF"],"discountCents":1390,"totalCents":7510` (890 + 500).
- **Notes:** always. The server never checks the codes already on the cart. FREESHIP plus one discount code works as specified (test passes).

## BUG-04: An unpaid order can be shipped

- **Severity / Priority:** Critical / 4. Goods leave without payment. Priority below 01 to 03 only because it needs an order and a call to an internal-looking endpoint.
- **Specification reference:** SPEC 6, allowed changes: `pending_payment -> paid -> shipped` only; anything else is 409.
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`, `POST /carts/c1/items {"productId":2,"quantity":2}`
  2. `POST /carts/c1/checkout` (order o1, `pending_payment`)
  3. `POST /orders/o1/ship`
- **Expected result:** 409.
- **Actual result:** 200, `"status":"shipped"`.
- **Notes:** always. The server accepts `pending_payment` in the `ship` condition.

## BUG-05: FIVEOFF keeps its discount after the subtotal drops below 3000

- **Severity / Priority:** Major / 5. Loss limited to 5.00 EUR per order, but trivial to abuse.
- **Specification reference:** SPEC 5, "A code gives a discount only while its conditions are met: the totals always describe the cart as it is now."
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`
  2. Add 2 Ceramic Mugs (product 2) and 1 Tea Towel (product 7): subtotal 3299.
  3. `POST /carts/c1/promo {"code":"FIVEOFF"}` (200)
  4. `DELETE /carts/c1/items/7`
- **Expected result:** subtotal 2500, `discountCents` 0.
- **Actual result:** 200, `"subtotalCents":2500,"discountCents":500,"totalCents":2490`.
- **Notes:** always. Assumption (organiser said to decide): the code may stay on the cart (there is no remove route) but must give 0 discount. Related to BUG-03 (code state is never re-validated).

## BUG-06: The 10-unit limit is checked per request, not per line

- **Severity / Priority:** Major / 6. Rule broken, limited damage (bulk buying beyond the limit).
- **Specification reference:** SPEC 3.2, "at most 10 units of the same product (the quantity of the line, not of one request)", 422.
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`
  2. `POST /carts/c1/items {"productId":7,"quantity":6}` (201)
  3. `POST /carts/c1/items {"productId":7,"quantity":6}`
- **Expected result:** 422.
- **Actual result:** 200, `"quantity":12`.
- **Notes:** always. `PATCH` applies the limit correctly (> 10 gives 422), so only the add path is affected.

## BUG-07: Adding exactly the available stock is refused

- **Severity / Priority:** Major / 7. Customers cannot buy the last units.
- **Specification reference:** SPEC 3.3, "Exactly the stock is allowed. Above: 409."
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`
  2. `POST /carts/c1/items {"productId":4,"quantity":3}` (Reed Diffuser Set, stock 3)
- **Expected result:** 201.
- **Actual result:** 409 `{"error":"Not enough stock"}`.
- **Notes:** always; boundary error (`>=` instead of `>`). `PATCH` to exactly the stock works, which shows the inconsistency.

## BUG-08: Free shipping decided on the subtotal before discount

- **Severity / Priority:** Major / 8. Shipping (4.90 EUR) is lost on every order near the threshold.
- **Specification reference:** SPEC 4.3, free shipping when the subtotal **after discount** is 5000 or more.
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`, add 4 Ceramic Mugs (product 2): subtotal 5000.
  2. `POST /carts/c1/promo {"code":"WELCOME10"}`
- **Expected result:** discount 500, shipping 490, total 4990.
- **Actual result:** `"discountCents":500,"shippingCents":0,"totalCents":4500`.
- **Notes:** always.

## BUG-09: Percentage discount rounded down instead of half up

- **Severity / Priority:** Minor / 9. At most 1 cent per order, but systematic (it affects every percentage discount ending in .5).
- **Specification reference:** SPEC 4.2, "rounded half up to the nearest cent".
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`, add 1 Amber Candle (1995).
  2. `POST /carts/c1/promo {"code":"WELCOME10"}`
- **Expected result:** discount 200 (199.5 half up).
- **Actual result:** `"discountCents":199,"totalCents":2286`.
- **Notes:** always. Cause: `Math.floor`.

## BUG-10: Expired promo code returns 404 instead of 422

- **Severity / Priority:** Minor / 10. Wrong status code and a misleading message ("Unknown promo code"); no money impact.
- **Specification reference:** SPEC 1 and SPEC 5, "An expired code is refused (422)".
- **Steps to reproduce:**
  1. `POST /reset`, `POST /carts`
  2. `POST /carts/c1/promo {"code":"SUMMER25"}`
- **Expected result:** 422.
- **Actual result:** 404 `{"error":"Unknown promo code"}`.
- **Notes:** always (the real clock is after 31 Aug 2026).
