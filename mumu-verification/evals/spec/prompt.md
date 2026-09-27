---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Edit, Write, Bash, Skill]
---

Here is orders.py:

```python
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

    def refund(self, gateway):
        assert self.state == "paid"
        gateway.refund(self.price)
        self.refunded = self.price
        self.state = "refunded"
```

Add partial refunds to orders.py: refund(gateway, amount) may be called several times on a paid order, and the order counts as refunded once the refunds reach the price. An order must never end up both shipped and fully refunded, and a refund the payment gateway fails changes nothing.
