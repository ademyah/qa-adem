import os
import pytest
import requests

BASE = os.getenv("BASE_URL", "http://localhost:3002")


class Api:
    """Thin helper around the Maison Lumen API."""

    def __init__(self):
        self.s = requests.Session()

    def req(self, method, path, **kw):
        return self.s.request(method, BASE + path, timeout=10, **kw)

    def new_cart(self):
        r = self.req("POST", "/carts")
        assert r.status_code == 201
        return r.json()["id"]

    def add(self, cart, product_id, quantity):
        return self.req("POST", f"/carts/{cart}/items", json={"productId": product_id, "quantity": quantity})

    def cart_with(self, product_id, quantity):
        """New cart holding `quantity` of `product_id` (asserts the setup worked)."""
        cart = self.new_cart()
        r = self.add(cart, product_id, quantity)
        assert r.status_code == 201, f"setup failed: {r.status_code} {r.text}"
        return cart

    def promo(self, cart, code):
        return self.req("POST", f"/carts/{cart}/promo", json={"code": code})

    def get_cart(self, cart):
        return self.req("GET", f"/carts/{cart}").json()

    def checkout(self, cart):
        return self.req("POST", f"/carts/{cart}/checkout")

    def stock(self, product_id):
        return self.req("GET", f"/products/{product_id}").json()["stock"]


@pytest.fixture(autouse=True)
def _reset():
    """Every test starts from the initial data (SPEC: POST /reset)."""
    r = requests.post(BASE + "/reset", timeout=10)
    assert r.status_code == 200, "server not reachable: start it with `node server.js`"


@pytest.fixture
def api():
    return Api()
