class OrderController:
    def __init__(self, order_service, query_service):
        self.order_service = order_service
        self.query_service = query_service

    def post_order(self, order_id, customer_id, total):
        return self.order_service.create_order(order_id, customer_id, total)

    def post_payment(self, order_id):
        return self.order_service.pay_order(order_id)

    def delete_order(self, order_id):
        return self.order_service.cancel_order(order_id)

    def get_order(self, order_id):
        return self.query_service.get_order(order_id)
