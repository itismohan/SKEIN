from app.domain.orders import Order

class OrderService:
    def __init__(self, order_repository, payment_service):
        self.order_repository = order_repository
        self.payment_service = payment_service

    def create_order(self, order_id, customer_id, total):
        order = self._build_order(order_id, customer_id, total)
        self.order_repository.save(order)
        return order

    def _build_order(self, order_id, customer_id, total):
        return Order(order_id, customer_id, total)

    def pay_order(self, order_id):
        order = self.order_repository.get(order_id)
        payment = self.payment_service.authorize_payment(order_id, order.total)
        order.mark_paid()
        self.order_repository.save(order)
        return payment

    def cancel_order(self, order_id):
        order = self.order_repository.get(order_id)
        order.mark_cancelled()
        return self.order_repository.save(order)
