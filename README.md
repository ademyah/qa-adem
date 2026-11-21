# QA case study: Maison Lumen cart and promo API

Python 3.9+ with pytest and requests. Node.js 18+ for the provided server (not modified).

## Run

```bash
# terminal 1: the system under test
node server.js

# terminal 2: the tests (one command)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pytest
```

Another port: `PORT=4000 node server.js` and `BASE_URL=http://localhost:4000 pytest`.
Each test calls `POST /reset` first, so tests are independent and can run in any order.

## How to read the results

Expected result of a normal run: **37 passed, 12 xfailed**.

- `passed`: the server follows the specification for that rule.
- `xfailed`: a confirmed defect. The test checks the **specification**, not the faulty behaviour, and is marked `xfail(reason="BUG-xx", strict=True)`. `BUG-xx` points to `BUGS.md`. The test stays red in substance; `strict=True` turns it into a failure (XPASS) as soon as the bug is fixed, as a reminder to remove the mark.
- To see the raw failures: `pytest --runxfail`.

| File | Area (SPEC section) |
|---|---|
| `tests/test_quantities_stock.py` | quantities and stock (3) |
| `tests/test_totals.py` | totals, rounding, shipping (4) |
| `tests/test_promo_codes.py` | promo codes (5) |
| `tests/test_checkout_orders.py` | checkout and order statuses (6) |
| `tests/test_validation.py` | input validation, error shape (1) |
| `tests/test_concurrency.py` | simultaneous checkouts (6) |

Deliverables: `STRATEGY.md` (one page), `BUGS.md` (10 reports, sorted table).

## Not covered

See `STRATEGY.md`: valid SUMMER25 (the server uses the real clock), security and authentication, performance, concurrency on routes other than checkout, a checkout of a cart containing invalid quantities (BUG-02), CI, Postman collection, generated tests.
