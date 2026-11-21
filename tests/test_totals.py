"""SPEC 4 - totals, rounding, shipping."""
import pytest
CANDLE, MUG, TOWEL = 1, 2, 7


def test_subtotal_and_shipping_below_threshold(api):
    cart = api.cart_with(CANDLE, 2)  # 2 x 1995 = 3990
    c = api.get_cart(cart)
    assert (c["subtotalCents"], c["discountCents"], c["shippingCents"], c["totalCents"]) == (3990, 0, 490, 4480)


def test_empty_cart_has_free_shipping(api):
    c = api.get_cart(api.new_cart())
    assert (c["subtotalCents"], c["shippingCents"], c["totalCents"]) == (0, 0, 0)


def test_free_shipping_at_exactly_5000(api):
    c = api.get_cart(api.cart_with(MUG, 4))  # 4 x 1250 = 5000
    assert c["shippingCents"] == 0 and c["totalCents"] == 5000


@pytest.mark.xfail(reason="BUG-09", strict=True)
def test_percentage_discount_rounds_half_up(api):
    # 1995 * 10% = 199.5 -> half up = 200 (SPEC 4.2)
    cart = api.cart_with(CANDLE, 1)
    api.promo(cart, "WELCOME10")
    assert api.get_cart(cart)["discountCents"] == 200


@pytest.mark.xfail(reason="BUG-08", strict=True)
def test_shipping_threshold_uses_subtotal_after_discount(api):
    # 5000 - 10% = 4500 < 5000 -> shipping must be charged (SPEC 4.3)
    cart = api.cart_with(MUG, 4)
    api.promo(cart, "WELCOME10")
    c = api.get_cart(cart)
    assert c["discountCents"] == 500
    assert c["shippingCents"] == 490
    assert c["totalCents"] == 5000 - 500 + 490


def test_line_totals_add_up_to_subtotal(api):
    cart = api.cart_with(CANDLE, 3)
    api.add(cart, MUG, 2)
    c = api.get_cart(cart)
    assert sum(l["lineTotalCents"] for l in c["items"]) == c["subtotalCents"] == 3 * 1995 + 2 * 1250
