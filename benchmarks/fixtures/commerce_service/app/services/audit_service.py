class AuditService:
    def record_order_created(self, order_id):
        return self._write_event("ORDER_CREATED", order_id)

    def record_payment(self, payment_id):
        return self._write_event("PAYMENT_AUTHORIZED", payment_id)

    def _write_event(self, event_type, entity_id):
        return {"type": event_type, "id": entity_id}
