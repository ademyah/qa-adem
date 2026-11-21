"""SPEC 6: stock can never become negative, even with simultaneous checkouts."""
from concurrent.futures import ThreadPoolExecutor

import pytest

WOOL = 5  # stock 5


@pytest.mark.concurrency
@pytest.mark.xfail(reason="BUG-01", strict=True)
def test_parallel_checkouts_never_oversell(api):
    # 5 carts each hold 3 wool throws (3 < stock 5, so setup does not hit BUG-05).
    # Only ONE checkout can be honoured (3 + 3 > 5): the others must be 409 and stock must stay >= 0.
    carts = [api.cart_with(WOOL, 3) for _ in range(5)]
    with ThreadPoolExecutor(max_workers=5) as pool:
        codes = list(pool.map(lambda c: api.checkout(c).status_code, carts))
    stock = api.stock(WOOL)
    assert stock >= 0, f"stock became {stock}; statuses={codes}"
    assert codes.count(201) == 1 and codes.count(409) == 4, codes


def test_sequential_checkouts_respect_stock(api):
    # Control test (no parallelism): the stock check itself works when requests are serial.
    a, b = api.cart_with(WOOL, 3), api.cart_with(WOOL, 3)
    assert api.checkout(a).status_code == 201
    assert api.checkout(b).status_code == 409
    assert api.stock(WOOL) == 2
