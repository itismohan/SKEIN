class NotificationService:
    def notify_customer(self, customer_id, message):
        return self._send(customer_id, message)

    def _send(self, customer_id, message):
        return {"customer": customer_id, "message": message}
