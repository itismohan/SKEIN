# Order Platform Architecture

The API layer delegates order commands to `OrderService`. Query traffic uses
`OrderQueryService`. `OrderService` persists orders through `OrderRepository`
and delegates payment authorization to `PaymentService`.

Workers consume order events and reuse the service layer rather than writing
to repositories directly. Payment and customer repositories are independent
persistence boundaries.
