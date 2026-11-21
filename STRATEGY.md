# Test strategy: Maison Lumen cart and promo API

**Need and assumptions.** Before launch the team wants to know what works, what does not, and what to fix first. I treated `SPEC.md` as the reference and read `server.js` only to choose where to probe, never to define expected results. Assumptions (the organiser's answers and mine, each tested): promo codes are case-insensitive; spaces around a code are ignored (my choice); a code already on a cart stays there but must give a 0 discount once its condition fails (no remove route exists); 422 (limit) wins over 409 (stock) when both apply; an order cancellation does not reopen the cart; validation order between 400 and 404 is unspecified, so I do not test it.

**Risks, ranked, and why.**
1. Concurrent checkout: money and stock, and the spec states the rule explicitly.
2. Quantity validation: a negative quantity gives a negative total.
3. Promo codes: stacking and state after cart changes (revenue leaks).
4. Order status machine: goods shipped without payment.
5. Stock and limit boundaries (exactly the stock, 10 per line, line vs request).
6. Totals: rounding half up, shipping threshold after discount.
7. Input robustness: types, unknown ids, malformed JSON, error shape.

**Result.** 49 test cases (37 pass, 12 expected failures) covering six areas; 10 confirmed defects in `BUGS.md`, ranked 1 to 10 by customer impact and ease of abuse. Every bug has a test that checks the specification and stays red (strict xfail with the bug number).

**Not tested.** The valid case of SUMMER25 (real clock, confirmed by the organiser); authentication and authorisation (none exists); performance and load; security beyond input validation; concurrency on other routes (add item, apply promo, pay/cancel races); what checkout does with a cart holding an invalid quantity (BUG-02); idempotency of repeated checkout requests in parallel on the same cart.

**AI usage and checks.** I used an AI assistant (Claude) to review the specification and the provided server, to propose a ranked list of risks, and to draft the pytest files. I did not accept its output as is: I ran the whole suite against the server several times, reproduced every bug by hand with the exact requests listed in `BUGS.md`, and caught one false positive (the first concurrency test failed because of BUG-07 during setup, not because of the race; I rewrote it and confirmed `stock = -10`). I can explain every test and every report.

**With one more day.** Parallel tests for add-item/promo/pay/cancel races; seeded generated tests on totals (random carts, compare with an independent calculation); a rule-to-test matrix; a Postman collection; CI that starts the server and runs `pytest`; a check of what orders contain after BUG-02 inputs.
