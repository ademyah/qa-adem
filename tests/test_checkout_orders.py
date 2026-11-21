"""SPEC 6 - checkout and order statuses."""
import pytest
MUG, VASE = 2, 6


def _order(api, product=MUG, qty=2):
    cart = api.cart_with(product, qty)
    r = api.checkout(cart)
    assert r.status_code == 201, r.text
    return cart, r.json()


def test_checkout_creates_pending_order_and_decreases_stock(api):
    cart, order = _order(api)
    assert order["status"] == "pending_payment"
    assert order["totalCents"] == 2500 + 490
    assert api.stock(MUG) == 38
    assert api.get_cart(cart)["status"] == "checked_out"


def test_empty_cart_checkout_is_422(api):
    assert api.checkout(api.new_cart()).status_code == 422


def test_checked_out_cart_cannot_be_modified_or_checked_out_again(api):
    cart, _ = _order(api)
    assert api.add(cart, MUG, 1).status_code == 409
    assert api.checkout(cart).status_code == 409
    assert api.promo(cart, "WELCOME10").status_code == 409


def test_pay_then_ship_happy_path(api):
    _, o = _order(api)
    assert api.req("POST", f"/orders/{o['id']}/pay").json()["status"] == "paid"
    assert api.req("POST", f"/orders/{o['id']}/ship").json()["status"] == "shipped"


@pytest.mark.xfail(reason="BUG-04", strict=True)
def test_cannot_ship_an_unpaid_order(api):
    # SPEC 6: only pending_payment -> paid -> shipped.
    _, o = _order(api)
    r = api.req("POST", f"/orders/{o['id']}/ship")
    assert r.status_code == 409, r.text


def test_final_statuses_cannot_change(api):
    _, o = _order(api)
    api.req("POST", f"/orders/{o['id']}/cancel")
    for action in ("pay", "ship", "cancel"):
        assert api.req("POST", f"/orders/{o['id']}/{action}").status_code == 409


def test_cancel_gives_stock_back(api):
    _, o = _order(api, MUG, 3)
    assert api.stock(MUG) == 37
    assert api.req("POST", f"/orders/{o['id']}/cancel").status_code == 200
    assert api.stock(MUG) == 40


def test_unknown_order_is_404(api):
    assert api.req("GET", "/orders/o999").status_code == 404
