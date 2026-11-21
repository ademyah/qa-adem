"""SPEC 5 - promo codes."""
import pytest
CANDLE, MUG, TOWEL, WOOL = 1, 2, 7, 5


def test_code_is_case_insensitive(api):
    cart = api.cart_with(MUG, 2)
    r = api.promo(cart, "welcome10")
    assert r.status_code == 200 and r.json()["promoCodes"] == ["WELCOME10"]


def test_surrounding_spaces_are_ignored_ASSUMPTION(api):
    # Assumption (organiser: "decide and state it"): " WELCOME10 " is accepted.
    cart = api.cart_with(MUG, 2)
    assert api.promo(cart, "  WELCOME10 ").status_code == 200


def test_unknown_code_is_404(api):
    assert api.promo(api.cart_with(MUG, 1), "NOPE").status_code == 404


def test_empty_or_missing_code_is_400(api):
    cart = api.cart_with(MUG, 1)
    assert api.promo(cart, "").status_code == 400
    assert api.req("POST", f"/carts/{cart}/promo", json={}).status_code == 400
    assert api.req("POST", f"/carts/{cart}/promo", json={"code": 123}).status_code == 400


@pytest.mark.xfail(reason="BUG-10", strict=True)
def test_expired_code_is_422(api):
    # SUMMER25 expired on 2026-08-31; real clock is later (organiser confirmed).
    cart = api.cart_with(MUG, 2)
    r = api.promo(cart, "SUMMER25")
    assert r.status_code == 422, r.text


def test_same_code_twice_changes_nothing(api):
    cart = api.cart_with(MUG, 2)
    api.promo(cart, "WELCOME10")
    r = api.promo(cart, "WELCOME10")
    assert r.status_code == 200 and r.json()["promoCodes"] == ["WELCOME10"]


@pytest.mark.xfail(reason="BUG-03", strict=True)
def test_second_discount_code_is_refused_409_and_cart_unchanged(api):
    cart = api.cart_with(WOOL, 1)  # 8900
    api.promo(cart, "WELCOME10")
    before = api.get_cart(cart)
    r = api.promo(cart, "FIVEOFF")
    assert r.status_code == 409, r.text
    assert api.get_cart(cart) == before


def test_freeship_can_be_combined_with_one_discount_code(api):
    cart = api.cart_with(MUG, 2)  # 2500
    api.promo(cart, "WELCOME10")
    r = api.promo(cart, "FREESHIP")
    assert r.status_code == 200
    c = r.json()
    assert c["discountCents"] == 250 and c["shippingCents"] == 0 and c["totalCents"] == 2250


def test_fiveoff_refused_below_3000_with_422(api):
    cart = api.cart_with(MUG, 2)  # 2500
    assert api.promo(cart, "FIVEOFF").status_code == 422


def test_fiveoff_ok_at_exactly_3000_boundary(api):
    cart = api.new_cart()
    api.add(cart, MUG, 2)      # 2500
    api.add(cart, TOWEL, 1)    # + 799 = 3299 >= 3000
    r = api.promo(cart, "FIVEOFF")
    assert r.status_code == 200 and r.json()["discountCents"] == 500


@pytest.mark.xfail(reason="BUG-05", strict=True)
def test_fiveoff_gives_no_discount_once_subtotal_drops_below_3000(api):
    # SPEC 5: "A code gives a discount only while its conditions are met."
    cart = api.new_cart()
    api.add(cart, MUG, 2)
    api.add(cart, TOWEL, 1)  # 3299
    assert api.promo(cart, "FIVEOFF").status_code == 200
    api.req("DELETE", f"/carts/{cart}/items/{TOWEL}")  # subtotal 2500
    c = api.get_cart(cart)
    assert c["discountCents"] == 0, c
