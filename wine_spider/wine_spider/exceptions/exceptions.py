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

class UnknownWineVolumeFormatException(Exception):
    def __init__(self, volume_unit, message="Unknown wine volume unit"):
        self.volume_unit = volume_unit
        self.message = f"{message}: {volume_unit}"
        super().__init__(self.message)

class AmbiguousRegionAndCountryMatchException(Exception):
    def __init__(self, title, message="Ambiguous region and country match"):
        self.message = f"{message}: {title}"
        super().__init__(self.message)

class NoMatchedRegionAndCountryException(Exception):
    def __init__(self, title, matched_name, matched_producer, matched_region, matched_country, matched_score, message="No matched region or country"):
        self.title = title
        self.message = f"{message}: {title}, Best match: {matched_name}, {matched_producer}, {matched_region}, {matched_country}, {matched_score}"
        super().__init__(self.message)

class WrongMatchedRegionAndCountryException(Exception):
    def __init__(self, title, matched_name, matched_producer, matched_region, matched_country, matched_score, message="Wrong matched region or country"):
        self.title = title
        self.message = f"{message}: {title}, Best match: {matched_name}, {matched_producer}, {matched_region}, {matched_country}, {matched_score}"
        super().__init__(self.message)

class NoPreDefinedVolumeIdentifierException(Exception):
    def __init__(self, title, message="No matched volume identifier"):
        self.title = title
        self.message = f"{message}: {title}"
        super().__init__(self.message)

class NoVolumnInfoException(Exception):
    def __init__(self, title, message="No volume info found"):
        self.title = title
        self.message = f"{message}: {title}"
        super().__init__(self.message)

# Christies specific exceptions
class ChristiesFilterNotFoundException(Exception):
    def __init__(self, filter_name, message="Christies filter not found"):
        self.filter_name = filter_name
        self.message = f"{message}: {filter_name}"
        super().__init__(self.message)