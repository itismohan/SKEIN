class Order:
    def __init__(self, order_id, customer_id, total):
        self.order_id = order_id
        self.customer_id = customer_id
        self.total = total
        self.status = "PENDING"

    def mark_paid(self):
        self.status = "PAID"

    def mark_cancelled(self):
        self.status = "CANCELLED"
