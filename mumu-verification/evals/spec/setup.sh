#!/bin/sh
cat > orders.py <<'PY'
class Order:
    def __init__(self, price):
        self.price = price
        self.state = "placed"
        self.refunded = 0

    def pay(self):
        assert self.state == "placed"
        self.state = "paid"

    def ship(self):
        assert self.state == "paid"
        self.state = "shipped"

    def refund(self):
        assert self.state == "paid"
        self.refunded = self.price
        self.state = "refunded"
PY
