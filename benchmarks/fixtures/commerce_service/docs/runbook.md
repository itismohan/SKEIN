# Operations Runbook

For an order payment issue, inspect the API request, `OrderService.pay_order`,
and the payment authorization path. For cancellation issues, inspect
`OrderService.cancel_order` and the order repository update path.

Health checks are intentionally lightweight and do not depend on persistence.
