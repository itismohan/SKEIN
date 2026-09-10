class OrderQueryService:
    def __init__(self, order_repository):
        self.order_repository = order_repository

    def get_order(self, order_id):
        return self.order_repository.get(order_id)

    def get_order_status(self, order_id):
        order = self.get_order(order_id)
        return order.status if order else None
