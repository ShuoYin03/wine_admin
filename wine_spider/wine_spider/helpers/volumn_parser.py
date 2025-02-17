from wine_spider.exceptions import UnknownWineVolumnUnitException

def parse_volumn(title):
    if "BT" in title:
        return 75
    elif "MAG" in title:
        return 150
    elif "1 JM30" in title:
        return 300
    else:
        raise UnknownWineVolumnUnitException(title)