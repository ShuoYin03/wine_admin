from wine_spider.exceptions import ChristiesFilterNotFoundException

valid_filters = [
  "Producer", "Artist / Maker", "Artist, Maker, Author", "Winery",
  "Region/Sub-Region", "Origin / Ethnicity", "Origin", "Region", "Region/Type",
  "Country", "Country/State",
  "Type", "Color", "Colour",
  "Size", "Bottle Size", "Format",
]

invalid_filters = [
  'Theme', 'Themes', 'Saved', 'Favourite', 'Material', 'Special Collections', 
  'Specialist Pick', 'Specialist Picks', 'Case Type', 'Client', 'Client Filter', 
  'Design', 'Duty Status', 'Function / Movement', 'Grape Varietal', 'Item Category', 
  'Large Format', 'Material / Technique', 'Object', 'Style / Period','Stylistic Period',
  'Subject Matter / Theme', 'Varietal', 'Variety', 
  "Vintage", "Date", "Price", "Estimate", "Estimates", "Low Estimate"
]

def is_filter_exists(filter):
    if filter in valid_filters:
        return True
    elif filter not in invalid_filters:
        raise ChristiesFilterNotFoundException(filter)
    return False

filter_map = {
  "Producer": "lot_producer",
  "Artist / Maker": "lot_producer",
  "Artist, Maker, Author": "lot_producer",
  "Winery": "lot_producer",
  
  "Region/Sub-Region": "region",
  "Origin / Ethnicity": "region",
  "Origin": "region",
  "Region": "region",
  "Region/Type": "region",

  "Country": "country",
  "Country/State": "country",

  "Type": "wine_colour",
  "Color": "wine_colour",
  "Colour": "wine_colour",

  "Size": "unit_format", 
  "Bottle Size": "unit_format", 
  "Format": "unit_format"
}

def map_filter_to_field(filter):
    if filter in filter_map:
        return filter_map[filter]
    elif filter not in invalid_filters:
        raise ChristiesFilterNotFoundException(filter)
    return