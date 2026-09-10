class PaymentRepository:
    def __init__(self):
        self.payments = {}

    def save(self, payment):
        self.payments[payment.payment_id] = payment
        return payment

    def get(self, payment_id):
        return self.payments.get(payment_id)
