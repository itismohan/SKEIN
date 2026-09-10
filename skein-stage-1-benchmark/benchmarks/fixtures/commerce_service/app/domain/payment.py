class Payment:
    def __init__(self, payment_id, order_id, amount):
        self.payment_id = payment_id
        self.order_id = order_id
        self.amount = amount
        self.status = "AUTHORIZED"

    def mark_refunded(self):
        self.status = "REFUNDED"
