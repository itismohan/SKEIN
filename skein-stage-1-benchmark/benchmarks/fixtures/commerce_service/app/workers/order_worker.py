class OrderWorker:
    def __init__(self, order_service):
        self.order_service = order_service

    def process_order_created(self, event):
        return self._process(event)

    def _process(self, event):
        return self.order_service.create_order(event["id"], event["customer"], event["total"])

    def process_order_cancelled(self, event):
        return self.order_service.cancel_order(event["id"])
