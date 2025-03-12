from wine_spider.exceptions import CityNotFoundException

def find_continent(country):
    country_to_continent = {
        "China": "Asia",
        "Cannes": "Asia",
        "Singapore": "Asia",
        "Hong Kong": "Asia",
        "Napa": "US",
        "Oregon": "US",
        "Boston": "US",
        "Delaware": "US",
        "New York": "US",
        "Marlborough": "US",
        "Los Angeles": "US",
        "Beverly Hills": "US",
        "New Castle, DE": "US",
        "Zurich": "Europe",
        "Beaune": "Europe",
        "London": "Europe",
        "Geneva": "Europe",
        "Paris": "Europe",
        "Bordeaux": "Europe",
        "Abergavenny": "Europe",
        "Dijon (France)": "Europe"
    }

    continent = country_to_continent.get(country)

    if continent:
        return continent
    else:
        raise CityNotFoundException(country)

def region_to_country(region):
    region_to_country = {
        "Burgundy": "France",
        "Champagne": "France",
        "Rhone": "France",
        "South Australia": "Australia",
        "Loire": "France",
        "Saint Pettersburg": "Spain",
        "Other France": "France",
        "California": "United States",
    }

    country = region_to_country.get(region)

    if country:
        return country
    else:
        raise CityNotFoundException(region)