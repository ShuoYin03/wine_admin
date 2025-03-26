class RatesNotFoundException(Exception):
    def __init__(self, rates_from, rates_to, message="Fx rates not found"):
        self.rates_from = rates_from
        self.rates_to = rates_to
        self.message = f"{message}: {rates_from} to {rates_to}"
        super().__init__(self.message)