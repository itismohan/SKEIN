class OrderRepository:
    def __init__(self):
        self.orders = {}

    def save(self, order):
        self.orders[order.order_id] = order
        return order

    def get(self, order_id):
        return self.orders.get(order_id)

    def update_status(self, order_id, status):
        order = self.get(order_id)
        if order:
            order.status = status
        return order
