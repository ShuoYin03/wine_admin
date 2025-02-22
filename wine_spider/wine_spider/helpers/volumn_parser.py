from wine_spider.exceptions import UnknownWineVolumnFormatException

def parse_unit(title):
    if title.count('(') > 1:
        title = title[title.rfind('('):title.rfind(')') + 1]
    unit_string = title.split("(")[1].split(')')[0]
    unit, unit_format = float(unit_string.split(' ')[0]), unit_string.split(' ')[1]
    return unit, unit_format

def parse_volumn(unit, bottle_size, title):
    unit_multipliers = {
        'L': 100,
        'cl': 1,
        'pint': 56.83,
        'Pint': 56.83,
        'Half-Pint': 28.42,
        'quart': 113.65,
        'Quart': 113.65,
        'Gallon': 454.61,
        'gallon': 454.61,
        'Litre': 100,
        'litre': 100,
        'ml': 0.1,
        'Bottle': 75,
        'Bottles': 75,
        'bottle': 75,
        'bottles': 75,
        'Ounces': 2.84,
        'MAG': 150,
        'BT': 75,
    }

    if bottle_size:
        bottle_info = bottle_size.split(' ')
        if len(bottle_info) == 1:
            size_value = float(''.join(filter(str.isdigit, bottle_size))) if ''.join(filter(str.isdigit, bottle_size)) != '' else 1
            size_unit = ''.join(filter(str.isalpha, bottle_size))
        elif len(bottle_info) == 2:
            size_value = float(bottle_info[0])
            size_unit = bottle_info[1]
        elif len(bottle_info) == 3:
            size_value = float(bottle_info[0]) 
            size_unit = bottle_info[-1]
            unit_percentage = fraction_to_float(bottle_info[1])
            size_value = size_value * unit_percentage
        else:
            raise UnknownWineVolumnFormatException(f"Unknown unit: {bottle_size}")
    
        if size_unit not in unit_multipliers:
            raise UnknownWineVolumnFormatException(f"Unknown unit: {bottle_size}")

        return unit * size_value * unit_multipliers[size_unit]

    if title.count('(') > 1:
        title = title[title.rfind('('):title.rfind(')') + 1]

    title = title.split("(")[1].split(')')[0]
    if 'Fluid Oz.' in title:
        title = title.replace('Fluid Oz.', 'Ounces')

    if ',' in title:
        title = title.split(',')
        for i in range(len(title)):
            title[i] = title[i].strip()

    if isinstance(title, list):
        volumn = 0
        for t in title:
            volumn += parse_title(t, unit_multipliers)
        return volumn
    else:
        return parse_title(title, unit_multipliers)

def parse_title(title, unit_multipliers):
    bottles = ['Bottles', 'Bottle', 'bottle', 'bottles']
    bottle_info = title.split(' ')
    if len(bottle_info) == 1:
        size_value = float(''.join(filter(str.isdigit, title))) if ''.join(filter(str.isdigit, title)) != '' else 1
        size_unit = ''.join(filter(str.isalpha, title))
    elif len(bottle_info) == 2:
        size_value = float(bottle_info[0])
        size_unit = bottle_info[1]
    elif len(bottle_info) == 3:
        size_value = int(bottle_info[0]) 
        size_unit = bottle_info[-1]
    elif len(bottle_info) == 4:
        if bottle_info[1] in bottles:
            size_value = int(bottle_info[0]) * fraction_to_float(bottle_info[2])
            size_unit = bottle_info[-1]
        else:
            size_value1 = int(bottle_info[0]) 
            size_unit1 = unit_multipliers[bottle_info[1]]
            size_value2 = fraction_to_float(bottle_info[2])
            size_unit2 = unit_multipliers[bottle_info[3]]
            return size_value1 * size_unit1 + size_value2 * size_unit2

    if size_unit not in unit_multipliers:
        raise UnknownWineVolumnFormatException(f"Unknown unit inside: {bottle_info}")

    return size_value * unit_multipliers[size_unit]

def fraction_to_float(fraction_str):
    if '/' in fraction_str:
        numerator, denominator = fraction_str.split('/')
        return float(numerator) / float(denominator)
    return float(fraction_str)