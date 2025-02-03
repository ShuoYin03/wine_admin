import unicodedata
import re

def normalize_string(input_string):
    input_string = input_string.lower()
    input_string = input_string.strip()
    input_string = unicodedata.normalize('NFKD', input_string)
    input_string = re.sub(r'[^\w\s-]', '', input_string)
    return input_string