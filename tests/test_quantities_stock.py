"""SPEC 3 - quantities and stock."""
import pytest

CANDLE, MUG, DIFFUSER, VASE, TOWEL, LANTERN = 1, 2, 4, 6, 7, 8


def test_add_new_line_returns_201_and_existing_line_200(api):
    cart = api.new_cart()
    assert api.add(cart, CANDLE, 1).status_code == 201
    r = api.add(cart, CANDLE, 2)
    assert r.status_code == 200
    assert r.json()["items"][0]["quantity"] == 3


@pytest.mark.xfail(reason="BUG-07", strict=True)
def test_can_add_exactly_the_stock(api):
    # SPEC 3.3: "Exactly the stock is allowed". Diffuser has stock 3.
    cart = api.new_cart()
    r = api.add(cart, DIFFUSER, 3)
    assert r.status_code == 201, r.text


def test_cannot_add_more_than_stock(api):
    cart = api.new_cart()
    assert api.add(cart, VASE, 3).status_code == 409  # stock 2


def test_out_of_stock_product_is_refused(api):
    cart = api.new_cart()
    assert api.add(cart, LANTERN, 1).status_code == 409  # stock 0


@pytest.mark.xfail(reason="BUG-06", strict=True)
def test_line_limit_applies_to_the_line_not_to_one_request(api):
    # SPEC 3.2: at most 10 units of the same product per cart -> 422.
    cart = api.cart_with(TOWEL, 6)
    r = api.add(cart, TOWEL, 6)  # line would be 12
    assert r.status_code == 422, r.text


def test_limit_error_wins_over_stock_error(api):
    # Organiser's answer: 422 (limit) takes priority over 409 (stock). Wool throw stock 5.
    cart = api.new_cart()
    assert api.add(cart, 5, 11).status_code == 422


@pytest.mark.parametrize("qty", ["2", None])
def test_add_rejects_non_numeric_quantity_with_400(api, qty):
    cart = api.new_cart()
    assert api.add(cart, CANDLE, qty).status_code == 400


@pytest.mark.xfail(reason="BUG-02", strict=True)
@pytest.mark.parametrize("qty", [0, -1, 1.5])
def test_add_rejects_zero_negative_or_decimal_quantity_with_400(api, qty):
    # SPEC 3.1: quantity must be an integer >= 1, otherwise 400.
    cart = api.new_cart()
    r = api.add(cart, CANDLE, qty)
    assert r.status_code == 400, f"quantity={qty!r}: {r.status_code} {r.text}"


def test_patch_zero_removes_the_line(api):
    cart = api.cart_with(CANDLE, 2)
    r = api.req("PATCH", f"/carts/{cart}/items/{CANDLE}", json={"quantity": 0})
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_patch_above_stock_is_409_and_at_stock_is_200(api):
    cart = api.cart_with(DIFFUSER, 1)
    assert api.req("PATCH", f"/carts/{cart}/items/{DIFFUSER}", json={"quantity": 4}).status_code == 409
    assert api.req("PATCH", f"/carts/{cart}/items/{DIFFUSER}", json={"quantity": 3}).status_code == 200
