---
max_turns: 8
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

    def refund(self):
        assert self.state == "paid"
        self.refunded = self.price
        self.state = "refunded"
```

Add partial refunds to orders.py: refund(amount) may be called several times on a paid order, and the order counts as refunded once the refunds reach the price. An order must never end up both shipped and fully refunded.
