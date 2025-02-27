class CityNotFoundException(Exception):
    def __init__(self, city_name, message="City not found in continent json"):
        self.city_name = city_name
        self.message = f"{message}: {city_name}"
        super().__init__(self.message)

class InvalidDateInputException(Exception):
    def __init__(self, date_input, message="Date input not supported"):
        self.date_input = date_input
        self.message = f"{message}: {date_input}"
        super().__init__(self.message)

class UnknownWineVolumnFormatException(Exception):
    def __init__(self, volumn_unit, message="Unknown wine volumn unit"):
        self.volumn_unit = volumn_unit
        self.message = f"{message}: {volumn_unit}"
        super().__init__(self.message)

class AmbiguousRegionAndCountryMatchException(Exception):
    def __init__(self, title, message="Ambiguous region and country match"):
        self.message = f"{message}: {title}"
        super().__init__(self.message)

class NoMatchedRegionAndCountryException(Exception):
    def __init__(self, title, message="No matched region or country"):
        self.title = title
        self.message = f"{message}: , {title}"
        super().__init__(self.message)