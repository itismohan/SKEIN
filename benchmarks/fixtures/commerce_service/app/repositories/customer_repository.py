class CustomerRepository:
    def __init__(self):
        self.customers = {}

    def save(self, customer):
        self.customers[customer["id"]] = customer
        return customer

    def get(self, customer_id):
        return self.customers.get(customer_id)
