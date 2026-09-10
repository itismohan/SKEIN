class PaymentController:
    def __init__(self, payment_service):
        self.payment_service = payment_service

    def post_authorization(self, order_id, amount):
        return self.payment_service.authorize_payment(order_id, amount)

    def post_refund(self, payment_id):
        return self.payment_service.refund_payment(payment_id)
