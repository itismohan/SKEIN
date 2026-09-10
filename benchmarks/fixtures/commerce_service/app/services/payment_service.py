class PaymentService:
    def __init__(self, payment_repository):
        self.payment_repository = payment_repository

    def authorize_payment(self, order_id, amount):
        payment = self._build_payment(order_id, amount)
        return self.payment_repository.save(payment)

    def _build_payment(self, order_id, amount):
        return type("Payment", (), {"payment_id": f"pay-{order_id}", "order_id": order_id, "amount": amount})()

    def refund_payment(self, payment_id):
        payment = self.payment_repository.get(payment_id)
        return payment
