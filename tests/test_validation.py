"""Input validation and robustness (SPEC 1)."""
import pytest

CANDLE = 1


def test_unknown_cart_is_404(api):
    assert api.req("GET", "/carts/c999").status_code == 404


def test_unknown_product_is_404(api):
    assert api.add(api.new_cart(), 999, 1).status_code == 404
    assert api.req("GET", "/products/999").status_code == 404


@pytest.mark.parametrize("pid", ["1", None, 1.5])
def test_product_id_must_be_an_integer_400(api, pid):
    r = api.req("POST", f"/carts/{api.new_cart()}/items", json={"productId": pid, "quantity": 1})
    assert r.status_code == 400


def test_malformed_json_is_400(api):
    r = api.req("POST", f"/carts/{api.new_cart()}/items", data="{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400


def test_error_bodies_have_the_error_shape(api):
    r = api.req("GET", "/carts/c999")
    assert set(r.json()) == {"error"}


def test_remove_line_not_in_cart_is_404(api):
    assert api.req("DELETE", f"/carts/{api.new_cart()}/items/{CANDLE}").status_code == 404


def test_catalogue_matches_provided_products(api):
    products = api.req("GET", "/products").json()
    assert len(products) == 8 and all({"id", "name", "priceCents", "stock"} <= set(p) for p in products)
